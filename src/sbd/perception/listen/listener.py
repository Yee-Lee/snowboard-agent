"""Listen perception worker."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sbd.adaptor.errors import AdapterError
from sbd.core.audio.base import AudioInput
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime
from sbd.perception.listen.asr import ASRAdapter


class Listen(WorkerRuntime):
    def __init__(self, *, audio_input: AudioInput, asr: ASRAdapter, bus: EventBus) -> None:
        super().__init__()
        self._audio_input = audio_input
        self._asr = asr
        self._bus = bus
        self._frames: AsyncIterator[bytes] | None = None

    async def start(self) -> None:
        await self._asr.start()

    async def stop(self) -> None:
        await self.abort()
        await self._asr.stop()

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        async def body() -> None:
            result: PerceptionResult | None = None
            unexpected: Exception | None = None
            self._frames = self._audio_input.frames()
            try:
                async with asyncio.timeout(timeout_seconds):
                    value = await self._await_operation(
                        self._asr.transcribe(self._frames)
                    )
                if value.text.strip():
                    extra = {}
                    if value.confidence is not None:
                        extra["confidence"] = value.confidence
                    if value.language is not None:
                        extra["language"] = value.language
                    result = PerceptionResult(
                        "listen", "ok", value.text, extra,
                        session_id, turn_id, correlation_id,
                    )
                else:
                    result = PerceptionResult(
                        "listen", "timeout", None, {},
                        session_id, turn_id, correlation_id,
                    )
            except TimeoutError:
                await self._asr.abort()
                result = PerceptionResult(
                    "listen", "timeout", None, {},
                    session_id, turn_id, correlation_id,
                )
            except AdapterError:
                result = PerceptionResult(
                    "listen", "error", None, {},
                    session_id, turn_id, correlation_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                unexpected = exc
            finally:
                await self._close_frames()
            if unexpected is not None:
                await self._bus.publish(
                    ErrorOccurred(
                        where="perception.listen",
                        error="listen worker failed",
                        exception_type=type(unexpected).__name__,
                    )
                )
                raise unexpected
            if result is not None and self._may_publish():
                await self._bus.publish(result)

        await self._run_call(body)

    async def _close_frames(self) -> None:
        frames = self._frames
        self._frames = None
        if frames is not None:
            await frames.aclose()

    async def _abort_resources(self) -> None:
        await self._asr.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._asr.force_abort()
