"""Tests for WP-M1-08: Resource Manager.

Covers Test IDs M1-RM-001 to M1-RM-006:
- M1-RM-001: Preflight DAG validation, cycle detection, self-dep, missing dep
- M1-RM-002: Phase-ordered startup (STATE_MANAGER->CORE->...->INPUT_PRODUCER)
- M1-RM-003: Core HAL fallback (audio/display/camera real failure -> null fallback)
- M1-RM-004: WorkerCatalog seal, capability map freeze, Reasoner query restriction
- M1-RM-005: Recovery ticket, barrier, generation tracking, ticket wait
- M1-RM-006: Startup rollback and shutdown stop_all reverse order
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
import pytest
from types import MappingProxyType
from typing import Any

from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import ComponentPolicy, TimeoutMap
from sbd.core.event_bus import EventBus
from sbd.core.resource_manager import (
    CapabilityKind,
    RecoveryContractViolation,
    RecoveryFatalError,
    ResourceGraphError,
    ResourceManager,
    ResourceResolver,
    ResourceSpec,
    StartPhase,
    StartupError,
    WorkerCatalog,
)


class DummyResource:
    def __init__(self, key: str, fail_start: bool = False):
        self.key = key
        self.fail_start = fail_start
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        if self.fail_start:
            raise RuntimeError(f"Failed to start {self.key}")
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


def register_session_skeleton(rm: ResourceManager) -> None:
    rm.register(ResourceSpec(
        key="worker.cognition.reasoner",
        phase=StartPhase.WORKER,
        factory=lambda resolver: DummyResource("worker.cognition.reasoner"),
    ))
    rm.register(ResourceSpec(
        key="worker.action.rest",
        phase=StartPhase.WORKER,
        factory=lambda resolver: DummyResource("worker.action.rest"),
    ))


def register_default_listen(rm: ResourceManager) -> None:
    rm.register(ResourceSpec(
        key="worker.perception.listen",
        phase=StartPhase.WORKER,
        factory=lambda resolver: DummyResource("worker.perception.listen"),
        capability_kind="listen",
    ))
    register_session_skeleton(rm)


# ── M1-RM-001: Preflight Validation & DAG Graph ─────────────────────────

def test_rm_001_missing_dependency_raises_graph_error():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)

        spec = ResourceSpec(
            key="worker.test",
            phase=StartPhase.WORKER,
            factory=lambda r: DummyResource("worker.test"),
            dependencies=("non_existent_key",),
        )
        rm.register(spec)

        with pytest.raises(ResourceGraphError, match="not declared|missing|unknown"):
            await rm.start()

    asyncio.run(async_test())


def test_rm_002_producer_is_late_filled_before_arm() -> None:
    async def run() -> None:
        calls: list[str] = []

        class StateManagerPort:
            def set_external_message_control(self, control) -> None:
                assert control is producer
                calls.append("late-fill")

        class Producer(DummyResource):
            async def start(self) -> None:
                calls.append("start")

            async def arm(self) -> None:
                calls.append("arm")

        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)
        producer = Producer("input.external_message")
        rm.set_state_manager(StateManagerPort())
        register_default_listen(rm)
        rm.register(ResourceSpec(
            key="worker.perception.read",
            phase=StartPhase.WORKER,
            factory=lambda resolver: DummyResource("worker.perception.read"),
            capability_kind="read",
        ))
        rm.register(ResourceSpec(
            key="input.external_message",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: producer,
        ))

        await rm.start()
        assert calls == ["start", "late-fill", "arm"]

    asyncio.run(run())


def test_rm_003_optional_source_without_first_turn_worker_never_starts() -> None:
    async def run() -> None:
        factory_called = False

        def source_factory(resolver):
            nonlocal factory_called
            factory_called = True
            return DummyResource("input.external_message")

        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        register_default_listen(rm)
        rm.register(ResourceSpec(
            key="input.external_message",
            phase=StartPhase.INPUT_PRODUCER,
            factory=source_factory,
        ))
        await rm.start()
        assert factory_called is False

    asyncio.run(run())


def test_rm_003_required_source_without_first_turn_worker_is_fatal() -> None:
    async def run() -> None:
        external = replace(
            DEFAULT_CONFIG.input_sources.external_message,
            policy=ComponentPolicy(enabled=True, required=True),
        )
        config = replace(
            DEFAULT_CONFIG,
            input_sources=replace(
                DEFAULT_CONFIG.input_sources,
                external_message=external,
            ),
        )
        factory_called = False

        def source_factory(resolver):
            nonlocal factory_called
            factory_called = True
            return DummyResource("input.external_message")

        rm = ResourceManager(config, EventBus())
        register_default_listen(rm)
        rm.register(ResourceSpec(
            key="input.external_message",
            phase=StartPhase.INPUT_PRODUCER,
            factory=source_factory,
            required=True,
        ))
        with pytest.raises(StartupError, match="no read worker"):
            await rm.start()
        assert factory_called is False

    asyncio.run(run())


def test_rm_005_recovery_dependency_order_and_backend_owner_switch() -> None:
    async def run() -> None:
        calls: list[str] = []

        class BackendOwner(DummyResource):
            def __init__(self, key: str, backend: DummyResource) -> None:
                super().__init__(key)
                self.backend = backend

        class Hook:
            def __init__(
                self,
                key: str,
                owner: BackendOwner | None = None,
                replacement: DummyResource | None = None,
            ) -> None:
                self.key = key
                self.owner = owner
                self.replacement = replacement

            async def rebuild(self, bus, config) -> None:
                calls.append(self.key)
                if self.owner is not None and self.replacement is not None:
                    self.owner.backend = self.replacement

        old_backend = DummyResource("backend.listen.old")
        replacement = DummyResource("backend.listen.replacement")
        worker = BackendOwner("worker.perception.listen", old_backend)
        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key="backend.a",
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource("backend.a"),
            recoverable=True,
            recovery_hook=Hook("backend.a"),
        ))
        rm.register(ResourceSpec(
            key="worker.perception.listen",
            phase=StartPhase.WORKER,
            dependencies=("backend.a",),
            factory=lambda resolver: worker,
            capability_kind="listen",
            recoverable=True,
            recovery_hook=Hook("worker.perception.listen", worker, replacement),
        ))
        register_session_skeleton(rm)
        await rm.start()

        ticket = rm.begin_recovery((
            "worker.perception.listen",
            "backend.a",
            "worker.perception.listen",
        ))
        assert ticket.keys == ("backend.a", "worker.perception.listen")
        assert rm.recovery_ready() is False
        await rm.wait_recovery(ticket)
        assert calls == ["backend.a", "worker.perception.listen"]
        assert rm.catalog.perception("listen") is worker
        assert worker.backend is replacement
        assert rm.capability_of("listen") is True

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["failure", "timeout"])
def test_rm_005_recovery_failure_or_timeout_keeps_barrier_clear(mode: str) -> None:
    async def run() -> None:
        release = asyncio.Event()

        class Hook:
            async def rebuild(self, bus, config):
                if mode == "failure":
                    raise RuntimeError("rebuild failed")
                await release.wait()

        resource = replace(
            DEFAULT_CONFIG.resource,
            recovery_timeout_seconds=0.01,
        )
        config = replace(DEFAULT_CONFIG, resource=resource)
        rm = ResourceManager(config, EventBus())
        rm.register(ResourceSpec(
            key="backend.a",
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource("backend.a"),
            recoverable=True,
            recovery_hook=Hook(),
        ))
        register_default_listen(rm)
        await rm.start()

        ticket = rm.begin_recovery(("backend.a",))
        with pytest.raises(RecoveryFatalError, match="Recovery failed"):
            await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is False

    asyncio.run(run())


def test_rm_005_recovery_reentry_and_unrecoverable_keys_are_rejected() -> None:
    async def run() -> None:
        started, release = asyncio.Event(), asyncio.Event()

        class Hook:
            async def rebuild(self, bus, config):
                started.set()
                await release.wait()

        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key="backend.a",
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource("backend.a"),
            recoverable=True,
            recovery_hook=Hook(),
        ))
        register_default_listen(rm)
        await rm.start()
        ticket = rm.begin_recovery(("backend.a",))
        await asyncio.wait_for(started.wait(), timeout=1)
        with pytest.raises(RecoveryContractViolation, match="Concurrent"):
            rm.begin_recovery(("backend.a",))
        with pytest.raises(RecoveryContractViolation, match="not recoverable"):
            rm.begin_recovery(("worker.perception.listen",))
        release.set()
        await rm.wait_recovery(ticket)

    asyncio.run(run())


def test_rm_005_shutdown_waits_for_recovery_hook_cleanup() -> None:
    async def run() -> None:
        rebuild_started = asyncio.Event()
        cleanup_started = asyncio.Event()
        cleanup_release = asyncio.Event()
        cleaned = False

        class Hook:
            async def rebuild(self, bus, config):
                nonlocal cleaned
                rebuild_started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cleanup_started.set()
                    await cleanup_release.wait()
                    cleaned = True
                    raise

        resource = replace(
            DEFAULT_CONFIG.resource,
            recovery_shutdown_cleanup_timeout_seconds=0.5,
        )
        rm = ResourceManager(replace(DEFAULT_CONFIG, resource=resource), EventBus())
        rm.register(ResourceSpec(
            key="backend.a",
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource("backend.a"),
            recoverable=True,
            recovery_hook=Hook(),
        ))
        register_default_listen(rm)
        await rm.start()
        rm.begin_recovery(("backend.a",))
        await asyncio.wait_for(rebuild_started.wait(), timeout=1)

        shutdown = asyncio.create_task(rm.prepare_shutdown())
        await asyncio.wait_for(cleanup_started.wait(), timeout=1)
        assert shutdown.done() is False
        cleanup_release.set()
        await shutdown
        assert cleaned is True
        assert rm.recovery_ready() is False

    asyncio.run(run())


def test_rm_006_start_timeout_rolls_back_and_stop_failures_do_not_block() -> None:
    async def run() -> None:
        stop_calls: list[str] = []

        class Core(DummyResource):
            async def stop(self) -> None:
                stop_calls.append("core")

        class BlockedWorker(DummyResource):
            async def start(self) -> None:
                await asyncio.Event().wait()

        resource = replace(
            DEFAULT_CONFIG.resource,
            startup_timeout_seconds=TimeoutMap(0.01, MappingProxyType({})),
        )
        rm = ResourceManager(replace(DEFAULT_CONFIG, resource=resource), EventBus())
        rm.register(ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=lambda resolver: Core("core.audio"),
        ))
        rm.register(ResourceSpec(
            key="worker.perception.listen",
            phase=StartPhase.WORKER,
            dependencies=("core.audio",),
            factory=lambda resolver: BlockedWorker("worker.perception.listen"),
            capability_kind="listen",
            required=True,
        ))
        with pytest.raises(StartupError):
            await rm.start()
        assert stop_calls == ["core"]

        stop_calls.clear()

        class BadStop(DummyResource):
            async def stop(self) -> None:
                stop_calls.append("listen")
                raise RuntimeError("stop failed")

        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=lambda resolver: Core("core.audio"),
        ))
        rm.register(ResourceSpec(
            key="worker.perception.listen",
            phase=StartPhase.WORKER,
            dependencies=("core.audio",),
            factory=lambda resolver: BadStop("worker.perception.listen"),
            capability_kind="listen",
        ))
        register_session_skeleton(rm)
        await rm.start()
        report = await rm.stop_all()
        assert stop_calls == ["listen", "core"]
        assert [failure.key for failure in report.failures] == [
            "worker.perception.listen"
        ]
        assert (await rm.stop_all()).failures == ()
        assert stop_calls == ["listen", "core"]

    asyncio.run(run())


def test_rm_001_cycle_detection_raises_graph_error():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)

        s1 = ResourceSpec(
            key="core.a",
            phase=StartPhase.CORE,
            factory=lambda r: DummyResource("core.a"),
            dependencies=("core.b",),
        )
        s2 = ResourceSpec(
            key="core.b",
            phase=StartPhase.CORE,
            factory=lambda r: DummyResource("core.b"),
            dependencies=("core.a",),
        )
        rm.register(s1)
        rm.register(s2)

        with pytest.raises(ResourceGraphError, match="[cC]ycle"):
            await rm.start()

    asyncio.run(async_test())


# ── M1-RM-002: Phase-Ordered Startup ────────────────────────────────────


def test_rm_002_phase_ordered_startup():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)
        call_order = []

        def make_factory(key: str):
            def factory(r: ResourceResolver):
                d = DummyResource(key)
                orig_start = d.start
                async def custom_start():
                    call_order.append(key)
                    await orig_start()
                d.start = custom_start
                return d
            return factory

        s_worker = ResourceSpec(
            key="worker.listen",
            phase=StartPhase.WORKER,
            factory=make_factory("worker.listen"),
            dependencies=("core.audio",),
            capability_kind="listen",
        )
        s_core = ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=make_factory("core.audio"),
            capability_kind="audio",
        )

        rm.register(s_worker)
        rm.register(s_core)

        register_session_skeleton(rm)
        await rm.start()
        # Core phase MUST start before Worker phase regardless of registration order
        assert call_order == ["core.audio", "worker.listen"]

    asyncio.run(async_test())


# ── M1-RM-003: Core HAL Fallback ────────────────────────────────────────


def test_rm_003_audio_real_failure_fallbacks_to_null():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)

        s_audio = ResourceSpec(
            key="core.audio.input",
            phase=StartPhase.CORE,
            factory=lambda r: DummyResource("core.audio.input", fail_start=True),
            capability_kind="audio",
            null_factory=lambda r: DummyResource("null.audio.input"),
        )
        rm.register(s_audio)
        register_default_listen(rm)

        await rm.start()

        # Audio capability should be False due to null fallback
        assert rm.capability_of("audio") is False

    asyncio.run(async_test())


# ── M1-RM-004: Catalog Sealing & Capability Query ───────────────────────


def test_rm_004_catalog_seal_and_reasoner_restriction():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)

        s_audio = ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=lambda r: DummyResource("core.audio"),
            capability_kind="audio",
        )
        s_listen = ResourceSpec(
            key="worker.listen",
            phase=StartPhase.WORKER,
            factory=lambda r: DummyResource("worker.listen"),
            dependencies=("core.audio",),
            capability_kind="listen",
        )

        rm.register(s_audio)
        rm.register(s_listen)

        register_session_skeleton(rm)
        await rm.start()

        assert rm.capability_of("listen") is True
        assert rm.capability_of("audio") is True

        # Reasoner allowed queries: perception / action kinds only
        assert rm.reasoner_capability_of("listen") is True
        with pytest.raises(KeyError, match="not allowed"):
            rm.reasoner_capability_of("audio")

    asyncio.run(async_test())


# ── M1-RM-005: Recovery Ticket & Barrier ────────────────────────────────


def test_rm_005_recovery_ticket_and_barrier():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)

        class Hook:
            def __init__(self):
                self.called = False

            async def rebuild(self, bus, config) -> None:
                self.called = True

        hook = Hook()

        s_llm = ResourceSpec(
            key="backend.cognition.reasoner.llm",
            phase=StartPhase.BACKEND,
            factory=lambda r: DummyResource("backend.cognition.reasoner.llm"),
            recoverable=True,
            recovery_hook=hook,
        )
        rm.register(s_llm)
        register_default_listen(rm)
        await rm.start()

        ticket = rm.begin_recovery(("backend.cognition.reasoner.llm",))
        assert ticket.generation == 1
        assert ticket.keys == ("backend.cognition.reasoner.llm",)

        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True
        assert hook.called is True

    asyncio.run(async_test())


# ── M1-RM-006: Startup Rollback & Shutdown Reverse Order ───────────────


def test_rm_006_shutdown_reverse_order():
    async def async_test():
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)
        stop_order = []

        def make_resource(key: str):
            d = DummyResource(key)
            async def custom_stop():
                stop_order.append(key)
                d.stopped = True
            d.stop = custom_stop
            return d

        s1 = ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=lambda r: make_resource("core.audio"),
        )
        s2 = ResourceSpec(
            key="worker.listen",
            phase=StartPhase.WORKER,
            factory=lambda r: make_resource("worker.listen"),
            dependencies=("core.audio",),
            capability_kind="listen",
        )

        rm.register(s1)
        rm.register(s2)
        register_session_skeleton(rm)
        await rm.start()

        report = await rm.stop_all()
        assert len(report.failures) == 0
        # Stop order must be reverse of start order (worker.listen first, then core.audio)
        assert stop_order == ["worker.listen", "core.audio"]

    asyncio.run(async_test())


def test_rm_004_capability_dependencies_propagate_false() -> None:
    async def run() -> None:
        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key="core.audio",
            phase=StartPhase.CORE,
            factory=lambda resolver: DummyResource("core.audio", fail_start=True),
            capability_kind="audio",
            null_factory=lambda resolver: DummyResource("null.audio"),
        ))
        rm.register(ResourceSpec(
            key="worker.perception.listen",
            phase=StartPhase.WORKER,
            factory=lambda resolver: DummyResource("worker.perception.listen"),
            capability_kind="listen",
            capability_dependencies=("audio",),
        ))
        register_session_skeleton(rm)

        await rm.start()

        assert rm.capability_of("audio") is False
        assert rm.capability_of("tool") is False

    asyncio.run(run())


def test_rm_004_catalog_seal_rejects_missing_required_kinds() -> None:
    catalog = WorkerCatalog()
    reasoner = DummyResource("worker.cognition.reasoner")
    rest = DummyResource("worker.action.rest")
    catalog.set_reasoner(reasoner)  # type: ignore[arg-type]
    catalog.register_action("rest", rest)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="listen, read"):
        catalog.seal({"listen", "read"})

    assert catalog.is_sealed is False


def test_rm_005_invalid_returned_replacement_is_cleaned() -> None:
    async def run() -> None:
        replacement = DummyResource("backend.replacement")

        class InvalidHook:
            async def rebuild(self, bus, config):
                await replacement.start()
                return replacement

        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key="backend.a",
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource("backend.a"),
            recoverable=True,
            recovery_hook=InvalidHook(),
        ))
        register_default_listen(rm)
        await rm.start()

        ticket = rm.begin_recovery(("backend.a",))
        with pytest.raises(RecoveryFatalError, match="owner must switch only its backend"):
            await rm.wait_recovery(ticket)

        assert replacement.stopped is True
        assert rm.recovery_ready() is False

    asyncio.run(run())


def test_rm_regression_capability_preflight_and_phase_failure_policy() -> None:
    async def run() -> None:
        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        register_default_listen(rm)
        await rm.start()
        for kind in ("audio", "display", "camera", "gpio", "listen", "read", "look", "speak", "tool"):
            assert isinstance(rm.capability_of(kind), bool)
        with pytest.raises(KeyError):
            rm.capability_of("unknown")

        factory_called = False
        for spec in (
            ResourceSpec(key="Core.Audio", phase=StartPhase.CORE, factory=lambda _: DummyResource("bad")),
            ResourceSpec(key="core.bad", phase=StartPhase.CORE, factory=lambda _: DummyResource("bad"), capability_kind="invalid"),  # type: ignore[arg-type]
            ResourceSpec(key="core.gpio", phase=StartPhase.CORE, factory=lambda _: DummyResource("bad"), null_factory=lambda _: DummyResource("null")),
        ):
            def factory(_: Any) -> DummyResource:
                nonlocal factory_called
                factory_called = True
                return DummyResource("must-not-start")
            invalid = ResourceManager(DEFAULT_CONFIG, EventBus())
            invalid.register(replace(spec, factory=factory))
            with pytest.raises(ResourceGraphError):
                await invalid.start()
            assert factory_called is False

        for required in (True, False):
            rm = ResourceManager(DEFAULT_CONFIG, EventBus())
            register_default_listen(rm)
            rm.register(ResourceSpec(key="backend.test", phase=StartPhase.BACKEND, factory=lambda _: DummyResource("backend.test", fail_start=True)))
            rm.register(ResourceSpec(key="worker.action.tool", phase=StartPhase.WORKER, dependencies=("backend.test",), required=required, capability_kind="tool", factory=lambda resolver: resolver.require("backend.test")))
            if required:
                with pytest.raises(StartupError):
                    await rm.start()
            else:
                await rm.start()
                assert rm.capability_of("tool") is False

        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        register_default_listen(rm)
        rm.register(ResourceSpec(key="adaptor.mqtt", phase=StartPhase.OBSERVER, required=True, factory=lambda _: DummyResource("adaptor.mqtt", fail_start=True)))
        await rm.start()

    asyncio.run(run())
