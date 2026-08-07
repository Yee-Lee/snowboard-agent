"""Barrier-based acceptance tests for M1-CAN-001 through M1-CAN-003."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from sbd.core.lifecycle import ForceAbortReport
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy,
    ConvergenceContractViolation,
    ConvergenceFatalError,
    ConvergenceResult,
    DefaultSessionConverger,
)


async def wait(event: asyncio.Event) -> None:
    await asyncio.wait_for(event.wait(), timeout=1)


@dataclass
class MockRecord:
    correlation_id: int
    kind: str
    phase: str
    worker: Any
    task: asyncio.Task[None]


class BarrierWorker:
    def __init__(
        self,
        outer_release: asyncio.Event,
        *,
        block_abort: bool = False,
        block_force_abort: bool = False,
        abort_error: Exception | None = None,
        force_abort_error: Exception | None = None,
        destroyed: tuple[str, ...] = (),
    ) -> None:
        self.outer_release = outer_release
        self.block_abort = block_abort
        self.block_force_abort = block_force_abort
        self.abort_error = abort_error
        self.force_abort_error = force_abort_error
        self.destroyed = destroyed
        self.abort_started = asyncio.Event()
        self.abort_release = asyncio.Event()
        self.force_abort_started = asyncio.Event()
        self.force_abort_release = asyncio.Event()

    async def abort(self) -> None:
        self.abort_started.set()
        if self.abort_error is not None:
            raise self.abort_error
        if self.block_abort:
            await self.abort_release.wait()
        self.outer_release.set()

    async def force_abort(self) -> ForceAbortReport:
        self.force_abort_started.set()
        if self.force_abort_error is not None:
            raise self.force_abort_error
        if self.block_force_abort:
            await self.force_abort_release.wait()
        self.outer_release.set()
        return ForceAbortReport(destroyed_backends=self.destroyed)


async def outer_task(release: asyncio.Event) -> None:
    await release.wait()


def record(
    correlation_id: int,
    kind: str,
    worker: BarrierWorker,
    release: asyncio.Event,
) -> MockRecord:
    return MockRecord(
        correlation_id,
        kind,
        "perception",
        worker,
        asyncio.create_task(outer_task(release)),
    )


def test_can_001_empty_records_returns_immediately() -> None:
    async def run() -> None:
        converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy())
        assert await converger.converge((), trigger="rest") == ConvergenceResult()

    asyncio.run(run())


def test_can_001_duplicate_records_rejected_before_worker_calls() -> None:
    async def run() -> None:
        release = asyncio.Event()
        worker = BarrierWorker(release)
        first = record(1, "listen", worker, release)
        duplicate = MockRecord(1, "look", "perception", worker, first.task)
        converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy())
        with pytest.raises(ConvergenceContractViolation, match="Duplicate"):
            await converger.converge((first, duplicate), trigger="rest")
        assert not worker.abort_started.is_set()
        release.set()
        await first.task

    asyncio.run(run())


def test_can_001_all_level_one_aborts_start_in_parallel() -> None:
    async def run() -> None:
        release_one, release_two = asyncio.Event(), asyncio.Event()
        one = BarrierWorker(release_one, block_abort=True)
        two = BarrierWorker(release_two, block_abort=True)
        first = record(1, "listen", one, release_one)
        second = record(2, "look", two, release_two)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(abort_default_seconds=0.5)
        )

        convergence = asyncio.create_task(
            converger.converge((first, second), trigger="interrupt")
        )
        await asyncio.gather(wait(one.abort_started), wait(two.abort_started))
        assert not one.force_abort_started.is_set()
        assert not two.force_abort_started.is_set()
        one.abort_release.set()
        two.abort_release.set()

        assert await convergence == ConvergenceResult()
        assert first.task.done() and second.task.done()

    asyncio.run(run())


def test_can_001_level_one_timeout_escalates_only_failed_target() -> None:
    async def run() -> None:
        release = asyncio.Event()
        worker = BarrierWorker(
            release,
            block_abort=True,
            destroyed=("backend.perception.listen.asr",),
        )
        target = record(1, "listen", worker, release)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(
                abort_default_seconds=0.01,
                force_abort_default_seconds=0.5,
            )
        )

        result = await converger.converge((target,), trigger="error")
        assert worker.abort_started.is_set()
        assert worker.force_abort_started.is_set()
        assert not target.task.cancelled()
        assert result.destroyed_backends == ("backend.perception.listen.asr",)

    asyncio.run(run())


def test_can_002_force_abort_timeout_is_fatal_without_task_cancel() -> None:
    async def run() -> None:
        release = asyncio.Event()
        worker = BarrierWorker(
            release,
            block_abort=True,
            block_force_abort=True,
        )
        target = record(1, "listen", worker, release)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(
                abort_default_seconds=0.01,
                force_abort_default_seconds=0.01,
            )
        )

        with pytest.raises(ConvergenceFatalError) as raised:
            await converger.converge((target,), trigger="shutdown")
        assert raised.value.stage == "force_abort_timeout"
        assert raised.value.correlation_id == 1
        assert worker.force_abort_started.is_set()
        assert not target.task.cancelled()
        release.set()
        await target.task

    asyncio.run(run())


def test_can_002_force_abort_exception_is_fatal() -> None:
    async def run() -> None:
        release = asyncio.Event()
        worker = BarrierWorker(
            release,
            abort_error=RuntimeError("abort failed"),
            force_abort_error=RuntimeError("force abort failed"),
        )
        target = record(1, "listen", worker, release)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(force_abort_default_seconds=0.5)
        )

        with pytest.raises(ConvergenceFatalError) as raised:
            await converger.converge((target,), trigger="shutdown")
        assert raised.value.stage == "force_abort_error"
        assert not target.task.cancelled()
        release.set()
        await target.task

    asyncio.run(run())


def test_can_003_reports_are_deduplicated_and_sorted() -> None:
    async def run() -> None:
        release_one, release_two = asyncio.Event(), asyncio.Event()
        one = BarrierWorker(
            release_one,
            abort_error=RuntimeError("abort one"),
            destroyed=("backend.b", "backend.a"),
        )
        two = BarrierWorker(
            release_two,
            abort_error=RuntimeError("abort two"),
            destroyed=("backend.a", "backend.c"),
        )
        first = record(1, "listen", one, release_one)
        second = record(2, "look", two, release_two)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(force_abort_default_seconds=0.5)
        )

        result = await converger.converge((first, second), trigger="rest")
        assert result.destroyed_backends == (
            "backend.a",
            "backend.b",
            "backend.c",
        )
        assert not first.task.cancelled() and not second.task.cancelled()

    asyncio.run(run())


def test_can_003_reentry_is_fatal_and_finally_allows_reuse() -> None:
    async def run() -> None:
        release = asyncio.Event()
        converger = DefaultSessionConverger(timeouts=CancelTimeoutPolicy())

        class ReenteringWorker(BarrierWorker):
            async def abort(self) -> None:
                self.abort_started.set()
                await converger.converge((), trigger="rest")

        worker = ReenteringWorker(release)
        target = record(1, "listen", worker, release)
        with pytest.raises(ConvergenceContractViolation, match="reentry"):
            await converger.converge((target,), trigger="rest")
        assert await converger.converge((), trigger="rest") == ConvergenceResult()
        release.set()
        await target.task

    asyncio.run(run())


def test_can_003_orchestration_cancellation_passes_through() -> None:
    async def run() -> None:
        release = asyncio.Event()
        worker = BarrierWorker(release, block_abort=True)
        target = record(1, "listen", worker, release)
        converger = DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(abort_default_seconds=0.5)
        )
        convergence = asyncio.create_task(
            converger.converge((target,), trigger="interrupt")
        )
        await wait(worker.abort_started)
        convergence.cancel()
        with pytest.raises(asyncio.CancelledError):
            await convergence
        assert not target.task.cancelled()
        assert await converger.converge((), trigger="rest") == ConvergenceResult()
        release.set()
        await target.task

    asyncio.run(run())
