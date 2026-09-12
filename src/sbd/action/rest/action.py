"""No-op Rest action worker."""

import inspect
from collections.abc import Awaitable, Callable

from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ErrorOccurred
from sbd.core.worker_runtime import WorkerRuntime


class Rest(WorkerRuntime):
    def __init__(self, *, bus: EventBus,
                 on_completion: Callable[[str], Awaitable[None] | None] | None = None) -> None:
        super().__init__()
        self._bus = bus
        self._on_completion = on_completion

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        await self.abort()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        async def body() -> None:
            status = "ok" if type(payload) is dict and not payload else "error"
            if self._on_completion is not None:
                try:
                    completed = self._on_completion(status)
                    if inspect.isawaitable(completed):
                        await completed
                except Exception:
                    await self._bus.publish(ErrorOccurred(
                        "action.rest", "REST_OBSERVATION_FAILED", "RuntimeError"))
                    raise RuntimeError("REST_OBSERVATION_FAILED") from None
            if self._may_publish():
                await self._bus.publish(ActionCompleted("rest", status, {}, session_id, turn_id, correlation_id))
        await self._run_call(body)
