"""Private single-call runtime shared by pure-async M2 workers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from sbd.core.lifecycle import ForceAbortReport


T = TypeVar("T")


@dataclass(slots=True)
class _ActiveCall:
    outer_task: asyncio.Task[None]
    cancel_requested: asyncio.Event = field(default_factory=asyncio.Event)
    done: asyncio.Event = field(default_factory=asyncio.Event)
    operation_task: asyncio.Task[Any] | None = None


class WorkerRuntime:
    """Enforce non-reentry and cancellation without cancelling the outer task."""

    def __init__(self) -> None:
        self._active: _ActiveCall | None = None

    async def _run_call(self, body: Callable[[], Awaitable[None]]) -> None:
        if self._active is not None:
            raise RuntimeError("worker already has an active call")
        outer = asyncio.current_task()
        if outer is None:
            raise RuntimeError("worker call requires an asyncio Task")
        active = _ActiveCall(outer_task=outer)
        self._active = active
        try:
            if active.cancel_requested.is_set():
                return
            await body()
        except asyncio.CancelledError:
            if not active.cancel_requested.is_set():
                raise
        finally:
            operation = active.operation_task
            if operation is not None:
                if not operation.done():
                    operation.cancel()
                await asyncio.gather(operation, return_exceptions=True)
                active.operation_task = None
            active.done.set()
            if self._active is active:
                self._active = None

    async def _await_operation(self, value: Awaitable[T]) -> T:
        active = self._require_active()
        if active.operation_task is not None:
            raise RuntimeError("worker already owns an internal operation")
        operation = asyncio.create_task(value)
        active.operation_task = operation
        if active.cancel_requested.is_set():
            operation.cancel()
        try:
            # A caller-owned deadline must not cancel the backend operation
            # before the worker has invoked its typed abort protocol.  The
            # operation remains owned by this runtime until terminal cleanup.
            return await asyncio.shield(operation)
        finally:
            if active.operation_task is operation and operation.done():
                active.operation_task = None

    def _may_publish(self) -> bool:
        return self._active is not None and not self._active.cancel_requested.is_set()

    async def abort(self) -> None:
        active = self._active
        if active is None:
            return
        active.cancel_requested.set()
        await self._abort_resources()
        await self._cancel_operation(active)
        await active.done.wait()

    async def force_abort(self) -> ForceAbortReport:
        active = self._active
        if active is None:
            return ForceAbortReport()
        active.cancel_requested.set()
        report = await self._force_abort_resources()
        await self._cancel_operation(active)
        await active.done.wait()
        return report

    async def _abort_resources(self) -> None:
        pass

    async def _force_abort_resources(self) -> ForceAbortReport:
        await self._abort_resources()
        return ForceAbortReport()

    def _require_active(self) -> _ActiveCall:
        if self._active is None:
            raise RuntimeError("worker has no active call")
        return self._active

    @staticmethod
    async def _cancel_operation(active: _ActiveCall) -> None:
        operation = active.operation_task
        if operation is not None and not operation.done():
            operation.cancel()
            await asyncio.gather(operation, return_exceptions=True)
