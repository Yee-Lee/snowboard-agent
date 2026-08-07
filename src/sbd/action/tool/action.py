"""Tool dispatch action worker."""

from __future__ import annotations

import asyncio

from sbd.action.tool.registry import ToolExecutionControl, ToolRegistry, ToolRegistryError
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ErrorOccurred
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime


class Tool(WorkerRuntime):
    def __init__(self, *, registry: ToolRegistry, bus: EventBus) -> None:
        super().__init__()
        self._registry = registry
        self._bus = bus
        self._execution_control: ToolExecutionControl | None = None

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        await self.abort()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        async def body() -> None:
            status = "error"
            unexpected: Exception | None = None
            try:
                if type(payload) is not dict or set(payload) != {"name", "arguments"}:
                    raise ToolRegistryError("invalid tool envelope")
                name = payload["name"]
                arguments = payload["arguments"]
                registered = self._registry._registered(name)
                self._execution_control = registered.execution_control
                await self._await_operation(self._registry.dispatch(name, arguments))
                status = "ok"
            except (ToolRegistryError, ValueError, TypeError):
                status = "error"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                unexpected = exc
            finally:
                self._execution_control = None
            if unexpected is not None:
                await self._bus.publish(ErrorOccurred("action.tool", "tool worker failed", type(unexpected).__name__))
                raise unexpected
            if self._may_publish():
                await self._bus.publish(ActionCompleted("tool", status, {}, session_id, turn_id, correlation_id))
        await self._run_call(body)

    async def _abort_resources(self) -> None:
        control = self._execution_control
        if control is not None:
            await control.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        control = self._execution_control
        if control is None:
            return ForceAbortReport()
        return await control.force_abort()
