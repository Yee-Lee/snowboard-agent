"""Look perception worker."""

from __future__ import annotations

import asyncio

from sbd.adaptor.errors import AdapterError
from sbd.core.camera.base import Camera
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime
from sbd.perception.look.vision import VisionAdapter


class Look(WorkerRuntime):
    def __init__(self, *, camera: Camera, vision: VisionAdapter, bus: EventBus) -> None:
        super().__init__()
        self._camera = camera
        self._vision = vision
        self._bus = bus

    async def start(self) -> None:
        await self._vision.start()

    async def stop(self) -> None:
        await self.abort()
        await self._vision.stop()

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        async def body() -> None:
            async def capture_and_describe():
                image = await self._camera.capture()
                return await self._vision.describe(image)

            try:
                async with asyncio.timeout(timeout_seconds):
                    value = await self._await_operation(capture_and_describe())
                status = "ok" if value.text.strip() else "error"
                result = PerceptionResult(
                    "look",
                    status,
                    value.text if status == "ok" else None,
                    value.extra if status == "ok" else {},
                    session_id,
                    turn_id,
                    correlation_id,
                )
            except TimeoutError:
                await self._vision.abort()
                result = PerceptionResult(
                    "look", "timeout", None, {},
                    session_id, turn_id, correlation_id,
                )
            except AdapterError:
                result = PerceptionResult(
                    "look", "error", None, {},
                    session_id, turn_id, correlation_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._bus.publish(
                    ErrorOccurred(
                        where="perception.look",
                        error="look worker failed",
                        exception_type=type(exc).__name__,
                    )
                )
                raise
            if self._may_publish():
                await self._bus.publish(result)

        await self._run_call(body)

    async def _abort_resources(self) -> None:
        await self._vision.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._vision.force_abort()
