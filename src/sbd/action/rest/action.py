"""No-op Rest action worker."""

from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted
from sbd.core.worker_runtime import WorkerRuntime


class Rest(WorkerRuntime):
    def __init__(self, *, bus: EventBus) -> None:
        super().__init__()
        self._bus = bus

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        await self.abort()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        async def body() -> None:
            status = "ok" if type(payload) is dict and not payload else "error"
            if self._may_publish():
                await self._bus.publish(ActionCompleted("rest", status, {}, session_id, turn_id, correlation_id))
        await self._run_call(body)
