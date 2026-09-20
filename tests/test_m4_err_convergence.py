"""M4-ERR WP2 completed-fault and recovery-key convergence tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy,
    ConvergenceFatalError,
    DefaultSessionConverger,
)
from sbd.core.worker_runtime import WorkerRuntime
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.event_bus import EventBus
from sbd.core.resource_manager import RecoveryFatalError, ResourceManager, ResourceSpec, StartPhase
from tests.test_resource_manager import DummyResource, register_default_listen


KEY = "backend.perception.listen.asr"


def _fault(disposition: BackendDisposition, keys: tuple[str, ...] = ()) -> ComponentSystemFault:
    return ComponentSystemFault.create(
        where="perception.listen",
        code="ASR_PROTOCOL_FAILED",
        backend=disposition,
        recovery_keys=keys,
    )


async def _failed_task(fault: ComponentSystemFault) -> None:
    raise fault


class _Worker:
    def __init__(self, report: ForceAbortReport) -> None:
        self.report = report
        self.abort_calls = 0
        self.force_calls = 0

    async def abort(self) -> None:
        self.abort_calls += 1

    async def force_abort(self) -> ForceAbortReport:
        self.force_calls += 1
        return self.report


def _record(task: asyncio.Task[None], worker: _Worker, correlation_id: int = 1):
    return SimpleNamespace(
        correlation_id=correlation_id,
        kind="listen",
        phase="perception",
        completion_mode="worker_fact",
        task=task,
        worker=worker,
    )


@pytest.mark.asyncio
async def test_m4_err_pi_001_four_disposition_paths() -> None:
    converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy())

    for disposition in (BackendDisposition.REUSABLE, BackendDisposition.NOT_APPLICABLE):
        task = asyncio.create_task(_failed_task(_fault(disposition)))
        await asyncio.sleep(0)
        worker = _Worker(ForceAbortReport())
        result = await converger.converge((_record(task, worker),), "error")
        assert result.destroyed_backends == ()
        assert worker.force_calls == 0

    for disposition in (BackendDisposition.REBUILD_REQUIRED, BackendDisposition.UNPROVEN):
        task = asyncio.create_task(_failed_task(_fault(disposition, (KEY,))))
        await asyncio.sleep(0)
        worker = _Worker(ForceAbortReport((KEY,)))
        result = await converger.converge((_record(task, worker),), "error")
        assert result.destroyed_backends == (KEY,)
        assert worker.force_calls == 1


@pytest.mark.asyncio
async def test_m4_err_pi_002_completed_fault_targets_only_owner() -> None:
    failed = asyncio.create_task(
        _failed_task(_fault(BackendDisposition.REBUILD_REQUIRED, (KEY,)))
    )
    idle = asyncio.create_task(asyncio.sleep(0))
    await asyncio.gather(idle, return_exceptions=True)
    await asyncio.sleep(0)
    owner = _Worker(ForceAbortReport((KEY,)))
    other = _Worker(ForceAbortReport(("other",)))
    result = await DefaultSessionConverger(
        timeouts=CancelTimeoutPolicy()
    ).converge((_record(failed, owner, 1), _record(idle, other, 2)), "error")
    assert result.destroyed_backends == (KEY,)
    assert owner.force_calls == 1
    assert other.force_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reported", [(), ("wrong",), (KEY, "other")])
async def test_m4_err_pi_003_recovery_key_mismatch_is_fatal(
    reported: tuple[str, ...],
) -> None:
    task = asyncio.create_task(
        _failed_task(_fault(BackendDisposition.REBUILD_REQUIRED, (KEY, KEY)))
    )
    await asyncio.sleep(0)
    with pytest.raises(ConvergenceFatalError) as raised:
        await DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy()
        ).converge((_record(task, _Worker(ForceAbortReport(reported))),), "error")
    assert raised.value.stage == "fault_recovery_key_mismatch"


class _Runtime(WorkerRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.forced = 0

    async def fail(self) -> None:
        async def body() -> None:
            raise _fault(BackendDisposition.REBUILD_REQUIRED, (KEY,))

        await self._run_call(body)

    async def _force_abort_resources(self) -> ForceAbortReport:
        self.forced += 1
        return ForceAbortReport((KEY,))


@pytest.mark.asyncio
async def test_worker_runtime_force_abort_after_outer_call_completed() -> None:
    runtime = _Runtime()
    with pytest.raises(ComponentSystemFault):
        await runtime.fail()
    assert await runtime.force_abort() == ForceAbortReport((KEY,))
    assert runtime.forced == 1
    assert await runtime.force_abort() == ForceAbortReport()


@pytest.mark.asyncio
async def test_m4_err_pi_004_rm_rebuild_success_and_failure_are_terminal() -> None:
    class Hook:
        def __init__(self, *, fail: bool = False) -> None:
            self.fail = fail
            self.calls = 0

        async def rebuild(self, bus, config) -> None:
            self.calls += 1
            if self.fail:
                raise RuntimeError("PRIVATE_RECOVERY_ROOT")

    async def prepared(hook: Hook) -> ResourceManager:
        rm = ResourceManager(DEFAULT_CONFIG, EventBus())
        rm.register(ResourceSpec(
            key=KEY,
            phase=StartPhase.BACKEND,
            factory=lambda resolver: DummyResource(KEY),
            recoverable=True,
            recovery_hook=hook,
        ))
        register_default_listen(rm)
        await rm.start()
        return rm

    success = Hook()
    rm = await prepared(success)
    ticket = rm.begin_recovery((KEY, KEY))
    await rm.wait_recovery(ticket)
    assert success.calls == 1 and rm.recovery_ready()

    failure = Hook(fail=True)
    rm = await prepared(failure)
    ticket = rm.begin_recovery((KEY,))
    with pytest.raises(RecoveryFatalError) as raised:
        await rm.wait_recovery(ticket)
    assert failure.calls == 1
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert not rm.recovery_ready()
