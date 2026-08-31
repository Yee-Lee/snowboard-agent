"""Resource Manager main implementation.

Defined per Ch 5 (docs/implement/ch05_resource_manager.md).
Handles multi-phase DAG startup, real->null core fallback, startup rollback,
WorkerCatalog sealing, static capability map derivation, recovery ticket/barrier,
and reverse-order shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, cast

from sbd.core.config.models import AppConfig
from sbd.core.event_bus import EventBus
from .catalog import WorkerCatalog
from .errors import (
    RecoveryContractViolation,
    RecoveryFatalError,
    ResourceGraphError,
    ResourceNotReadyError,
    StartupError,
    UndeclaredDependencyError,
)
from .models import (
    CapabilityKind,
    ManagedRecord,
    RecoveryTicket,
    ResourceKey,
    ResourceSpec,
    ShutdownReport,
    StopFailure,
)
from .phases import StartPhase
from .registry import Registry
from .resolver import ResourceResolver

logger = logging.getLogger(__name__)




class ResourceManager:
    def __init__(
        self,
        config: AppConfig,
        bus: EventBus,
        worker_catalog: WorkerCatalog | None = None,
    ) -> None:
        self._config = config
        self._bus = bus
        self._catalog = worker_catalog or WorkerCatalog()
        self._state_manager: Any = None

        self._specs: list[ResourceSpec] = []
        self._registry: Registry | None = None
        self._records: dict[str, ManagedRecord] = {}
        self._started_order: list[str] = []

        self._capability_builder: dict[str, bool] = {}
        self._capability_map: Mapping[str, bool] | None = None

        self._recovery_ready = asyncio.Event()
        self._recovery_ready.set()  # Initial state: ready (no recovery in progress)
        self._recovery_generation = 0
        self._active_recovery_task: asyncio.Task[None] | None = None
        self._active_recovery_ticket: RecoveryTicket | None = None
        self._fatal_recovery = asyncio.Event()
        self._fatal_recovery_error: RecoveryFatalError | None = None
        self._shutting_down = False
        self._startup_complete = False
        self._disabled_sources: set[str] = set()

    @property
    def catalog(self) -> WorkerCatalog:
        return self._catalog

    def set_state_manager(self, sm: Any) -> None:
        self._state_manager = sm

    def register(self, spec: ResourceSpec) -> None:
        if self._registry is not None:
            raise ResourceGraphError("Cannot register new specs after preflight validation")
        self._specs.append(spec)

    async def start(self) -> None:
        """Execute multi-phase DAG startup."""
        # 1. Preflight validation
        try:
            self._registry = Registry(self._specs)
        except Exception as exc:
            raise ResourceGraphError(f"Preflight validation failed: {exc}") from exc

        self._capability_builder = {kind: False for kind in (
            "audio", "display", "camera", "gpio", "listen", "read", "look", "speak", "tool")}
        self._records = {
            spec.key: ManagedRecord(spec=spec) for spec in self._registry.iter_specs()
        }

        try:
            # Producers are a separate final barrier.  Catalog/coherence must
            # be final before any source can publish a wake signal.
            phases = sorted(
                (phase for phase in StartPhase if phase != StartPhase.INPUT_PRODUCER),
                key=lambda phase: phase.value,
            )
            for phase in phases:
                phase_specs = [s for s in self._specs if s.phase == phase]
                if not phase_specs:
                    continue

                # Topo sort within phase (tie-breaker by registration order)
                sorted_phase_specs = self._topo_sort_phase(phase_specs)

                for spec in sorted_phase_specs:
                    await self._start_one(spec)

            self._capability_map = MappingProxyType(dict(self._capability_builder))
            await self._startup_coherence_gate()
            self._catalog.seal(self._required_catalog_kinds())

            input_specs = [
                spec for spec in self._specs
                if spec.phase == StartPhase.INPUT_PRODUCER
                and spec.key not in self._disabled_sources
            ]
            for spec in self._topo_sort_phase(input_specs):
                await self._start_one(spec)
                await self._late_fill_and_arm(spec)
            self._startup_complete = True

        except Exception as root_cause:
            logger.error("Startup failure in RM, initiating rollback: %s", root_cause)
            rollback_failures = await self._rollback()
            raise StartupError(
                f"Startup failed: {root_cause}", rollback_failures=rollback_failures
            ) from root_cause

    def _topo_sort_phase(self, phase_specs: list[ResourceSpec]) -> list[ResourceSpec]:
        """Kahn's algorithm with registration index as tie-breaker."""
        spec_map = {s.key: s for s in phase_specs}
        phase_keys = set(spec_map.keys())

        in_degree = {k: 0 for k in phase_keys}
        adj: dict[str, list[str]] = {k: [] for k in phase_keys}

        for s in phase_specs:
            for dep in s.dependencies:
                if dep in phase_keys:
                    adj[dep].append(s.key)
                    in_degree[s.key] += 1

        ready = [s for s in phase_specs if in_degree[s.key] == 0]
        sorted_result: list[ResourceSpec] = []

        while ready:
            ready.sort(key=lambda s: self._specs.index(s))
            curr = ready.pop(0)
            sorted_result.append(curr)

            for child_key in adj[curr.key]:
                in_degree[child_key] -= 1
                if in_degree[child_key] == 0:
                    ready.append(spec_map[child_key])

        return sorted_result

    async def _start_one(self, spec: ResourceSpec) -> None:
        record = self._records[spec.key]

        # Build scoped resolver
        resolver = ResourceResolver(spec.key, spec.dependencies, self._records)

        try:
            # Instantiate via factory
            instance = spec.factory(resolver)
            record.instance = instance

            # Call start()
            if hasattr(instance, "start") and callable(instance.start):
                await asyncio.wait_for(instance.start(), self._startup_timeout(spec.key))

            record.started = True
            record.own_start_ok = True
            record.recovery_hook = spec.recovery_hook
            self._started_order.append(spec.key)

            # Capability tracking
            if spec.capability_kind is not None:
                deps_ok = all(
                    self._capability_builder.get(dep, False)
                    for dep in spec.capability_dependencies
                )
                core_contributors_ok = all(
                    dep_record.started
                    and not dep_record.using_null
                    and not self._is_null_instance(dep_record.instance)
                    for dependency in spec.dependencies
                    if (dep_record := self._records[dependency]).spec.phase == StartPhase.CORE
                )
                self._capability_builder[spec.capability_kind] = (
                    record.own_start_ok
                    and deps_ok
                    and core_contributors_ok
                    and not self._is_null_instance(record.instance)
                )

            if spec.phase == StartPhase.WORKER:
                worker_kind = self._worker_kind(spec)
                if worker_kind is not None:
                    self._catalog.register(worker_kind, instance)

        except Exception as exc:
            logger.warning("Failed to start resource %s: %s", spec.key, exc)

            # Core HAL Fallback
            if spec.phase == StartPhase.CORE:
                if spec.null_factory is not None:
                    # HAL-specific null implementations are supplied by composition.
                    if record.instance is not None and hasattr(record.instance, "stop"):
                        try:
                            await asyncio.wait_for(record.instance.stop(), self._stop_timeout(spec.key))
                        except Exception:
                            logger.warning("Could not stop failed real resource %s", spec.key, exc_info=True)
                    null_inst = spec.null_factory(resolver)
                    await asyncio.wait_for(null_inst.start(), self._startup_timeout(spec.key))

                    record.instance = null_inst
                    record.using_null = True
                    record.started = True
                    record.own_start_ok = True
                    self._started_order.append(spec.key)

                    if spec.capability_kind is not None:
                        self._capability_builder[spec.capability_kind] = False
                    return
                elif spec.key == "core.gpio":
                    # GPIO failure: capability=False without Null object
                    if spec.capability_kind is not None:
                        self._capability_builder[spec.capability_kind] = False
                    return

            # Worker phase failure policy based on config required flag
            if spec.phase == StartPhase.BACKEND:
                # Backends are unavailable until a dependent worker applies
                # its own required/optional policy.
                return
            if spec.phase == StartPhase.OBSERVER:
                logger.warning("Optional observer/adaptor %s failed start, skipping", spec.key)
                return
            if spec.phase == StartPhase.WORKER:
                if spec.required:
                    raise StartupError(f"Required worker {spec.key} failed start: {exc}") from exc
                else:
                    if spec.capability_kind is not None:
                        self._capability_builder[spec.capability_kind] = False
                    return

            # Input producer or Reasoner failure
            if spec.required:
                raise StartupError(f"Required resource {spec.key} failed start: {exc}") from exc
            else:
                logger.warning("Optional resource %s failed start, skipping", spec.key)

    @staticmethod
    def _worker_kind(spec: ResourceSpec) -> str | None:
        key = str(spec.key)
        prefixes = (
            "worker.perception.",
            "worker.action.",
            "worker.cognition.",
        )
        for prefix in prefixes:
            if key.startswith(prefix):
                kind = key.removeprefix(prefix)
                return "reasoner" if kind == "reasoner" else kind
        return spec.capability_kind

    @staticmethod
    def _is_null_instance(instance: object | None) -> bool:
        return instance is not None and ".null." in type(instance).__module__

    async def _late_fill_and_arm(self, spec: ResourceSpec) -> None:
        record = self._records[spec.key]
        if not record.started or record.instance is None:
            return
        instance = record.instance
        if self._state_manager is not None:
            control = getattr(instance, "control", instance)
            if spec.key == "input.external_message":
                self._state_manager.set_external_message_control(control)
            elif spec.key == "input.voice_wake":
                self._state_manager.set_wake_listener(control)
        arm = getattr(instance, "arm", None)
        if callable(arm):
            await asyncio.wait_for(arm(), self._startup_timeout(spec.key))

    def capability_of(self, kind: str) -> bool:
        if self._capability_map is None:
            raise RuntimeError("Capability map is not ready (startup not completed)")
        try:
            return self._capability_map[kind]
        except KeyError:
            raise KeyError(f"Unknown capability kind: '{kind}'") from None

    def reasoner_capability_of(self, kind: str) -> bool:
        """Restricted capability query for Reasoner — perception and action kinds only."""
        allowed = {"listen", "read", "look", "speak", "tool"}
        if kind not in allowed:
            raise KeyError(f"Reasoner is not allowed to query capability kind: '{kind}'")
        return self.capability_of(kind)

    async def _startup_coherence_gate(self) -> None:
        """Ensure every enabled producer has its fixed first-turn worker."""
        missing_defaults = [
            kind for kind in self._config.perception.default_perceptions
            if kind not in self._catalog.candidate_kinds
        ]
        if missing_defaults:
            raise StartupError(
                "Default perceptions have no READY worker: "
                + ", ".join(missing_defaults)
            )

        sources = (
            ("input.button", self._config.input_sources.button.policy, "listen"),
            ("input.voice_wake", self._config.input_sources.voice_wake.policy, "listen"),
            ("input.external_message", self._config.input_sources.external_message.policy, "read"),
        )
        for key, policy, worker_kind in sources:
            if not policy.enabled:
                self._disabled_sources.add(key)
                continue
            if worker_kind in self._catalog.candidate_kinds:
                continue
            if policy.required:
                raise StartupError(f"Required source {key} has no {worker_kind} worker")
            self._disabled_sources.add(key)
            logger.warning("Disabled optional source %s because %s is unavailable", key, worker_kind)

        if (
            self._state_manager is not None
            and "input.voice_wake" in self._disabled_sources
            and any(spec.key == "input.voice_wake" for spec in self._specs)
        ):
            self._state_manager.set_wake_listener(None)

    def _required_catalog_kinds(self) -> set[str]:
        required = {"reasoner", "rest", *self._config.perception.default_perceptions}
        sources = (
            ("input.button", self._config.input_sources.button.policy, "listen"),
            ("input.voice_wake", self._config.input_sources.voice_wake.policy, "listen"),
            (
                "input.external_message",
                self._config.input_sources.external_message.policy,
                "read",
            ),
        )
        required.update(
            worker_kind
            for key, policy, worker_kind in sources
            if policy.enabled and key not in self._disabled_sources
        )
        return required

    def _startup_timeout(self, key: str) -> float:
        return self._config.resource.startup_timeout_seconds.by_kind.get(key, self._config.resource.startup_timeout_seconds.default)

    def _stop_timeout(self, key: str) -> float:
        return self._config.resource.stop_timeout_seconds.by_kind.get(key, self._config.resource.stop_timeout_seconds.default)

    async def _rollback(self) -> tuple[StopFailure, ...]:
        """Stop started resources in reverse order."""
        failures: list[StopFailure] = []
        for key in reversed(list(self._started_order)):
            record = self._records[key]
            if record.started and record.instance is not None:
                try:
                    if hasattr(record.instance, "stop") and callable(record.instance.stop):
                        await asyncio.wait_for(record.instance.stop(), self._stop_timeout(key))
                except Exception as exc:
                    logger.warning("Error stopping %s during rollback: %s", key, exc)
                    failures.append(StopFailure(key=key, error=exc))
                record.started = False
        self._started_order.clear()
        return tuple(failures)

    async def stop_all(self) -> ShutdownReport:
        """Stop all started resources in reverse started order."""
        failures: list[StopFailure] = []
        for key in reversed(list(self._started_order)):
            record = self._records.get(key)
            if record is not None and record.started and record.instance is not None:
                try:
                    if hasattr(record.instance, "stop") and callable(record.instance.stop):
                        await asyncio.wait_for(record.instance.stop(), self._stop_timeout(key))
                except Exception as exc:
                    logger.warning("Error stopping %s during shutdown: %s", key, exc)
                    failures.append(StopFailure(key=key, error=exc))
                record.started = False
        self._started_order.clear()
        return ShutdownReport(failures=tuple(failures))

    def begin_recovery(self, keys: tuple[str, ...]) -> RecoveryTicket:
        """Begin background recovery for destroyed backends."""
        if not keys:
            return RecoveryTicket(self._recovery_generation, ())

        if not self._startup_complete:
            raise RecoveryContractViolation("Recovery cannot begin before startup completes")

        for k in keys:
            if k not in self._records:
                raise RecoveryContractViolation(f"Unknown recovery key: {k}")
            record = self._records[k]
            if not record.started or not record.spec.recoverable or record.recovery_hook is None:
                raise RecoveryContractViolation(f"Resource is not recoverable and READY: {k}")

        if not self._recovery_ready.is_set():
            raise RecoveryContractViolation("Concurrent recovery batches are not allowed")
        if self._shutting_down:
            raise RecoveryContractViolation("Recovery cannot begin during shutdown")

        self._recovery_ready.clear()
        self._recovery_generation += 1
        key_set = set(keys)
        ticket = RecoveryTicket(
            generation=self._recovery_generation,
            keys=tuple(key for key in self._started_order if key in key_set),
        )

        self._active_recovery_ticket = ticket
        self._active_recovery_task = asyncio.create_task(self._run_recovery(ticket))
        return ticket

    async def _run_recovery(self, ticket: RecoveryTicket) -> None:
        try:
            async with asyncio.timeout(self._config.resource.recovery_timeout_seconds):
                for key in ticket.keys:
                    record = self._records[key]
                    hook = record.recovery_hook
                    if hasattr(hook, "rebuild"):
                        result = await hook.rebuild(self._bus, self._config)
                    else:
                        result = await hook()
                    if result is not None:
                        stop = getattr(result, "stop", None)
                        if callable(stop):
                            await stop()
                        raise RecoveryContractViolation(
                            "Recovery hook returned a replacement instance; "
                            "the owner must switch only its backend reference and return None"
                        )
        except Exception as exc:
            self._recovery_ready.clear()
            fatal = RecoveryFatalError(f"Recovery failed: {exc}")
            self._fatal_recovery_error = fatal
            self._fatal_recovery.set()
            raise fatal from exc
        else:
            self._recovery_ready.set()

    async def wait_recovery(self, ticket: RecoveryTicket) -> None:
        """Await completion of a recovery ticket."""
        if not ticket.keys and ticket.generation == self._recovery_generation:
            return
        if ticket != self._active_recovery_ticket:
            raise RecoveryContractViolation(
                f"Stale or mismatched recovery ticket: {ticket.generation}"
            )

        if self._active_recovery_task is not None:
            try:
                await self._active_recovery_task
            except RecoveryFatalError:
                raise
            except Exception as exc:
                raise RecoveryFatalError(f"Recovery failed: {exc}") from exc

    def recovery_ready(self) -> bool:
        return self._recovery_ready.is_set()

    async def wait_fatal(self) -> None:
        """Raise the first latched background recovery failure."""
        await self._fatal_recovery.wait()
        assert self._fatal_recovery_error is not None
        if self._active_recovery_task is not None and self._active_recovery_task.done():
            self._active_recovery_task.exception()
        raise self._fatal_recovery_error

    async def prepare_shutdown(self) -> None:
        self._shutting_down = True
        task = self._active_recovery_task
        if task is None or task.done():
            return
        task.cancel()
        try:
            async with asyncio.timeout(
                self._config.resource.recovery_shutdown_cleanup_timeout_seconds
            ):
                await task
        except asyncio.CancelledError:
            return
        except TimeoutError as exc:
            raise RecoveryFatalError("Recovery shutdown cleanup timed out") from exc
        except Exception as exc:
            raise RecoveryFatalError("Recovery shutdown cleanup failed") from exc
