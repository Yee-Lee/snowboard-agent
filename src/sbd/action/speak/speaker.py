"""Speak action worker."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sbd.adaptor.errors import AdapterError
from sbd.action.speak.tts import TTSAdapter
from sbd.core.audio.base import AudioOutput
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ErrorOccurred
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime


class Speak(WorkerRuntime):
    def __init__(self, *, tts: TTSAdapter, audio_output: AudioOutput, bus: EventBus) -> None:
        super().__init__()
        self._tts = tts
        self._audio_output = audio_output
        self._bus = bus
        self._pcm: AsyncIterator[bytes] | None = None

    async def start(self) -> None:
        await self._tts.start()

    async def stop(self) -> None:
        await self.abort()
        await self._tts.stop()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        async def body() -> None:
            unexpected: Exception | None = None
            status = "error"
            text = payload.get("text") if type(payload) is dict else None
            if type(text) is str and text.strip() and set(payload) == {"text"}:
                self._pcm = self._tts.synthesize(text)
                try:
                    await self._await_operation(self._audio_output.play(self._pcm))
                    status = "ok"
                except AdapterError:
                    status = "error"
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    unexpected = exc
                finally:
                    await self._close_pcm()
            if unexpected is not None:
                await self._bus.publish(ErrorOccurred("action.speak", "speak worker failed", type(unexpected).__name__))
                raise unexpected
            if self._may_publish():
                await self._bus.publish(ActionCompleted("speak", status, {}, session_id, turn_id, correlation_id))
        await self._run_call(body)

    async def _close_pcm(self) -> None:
        pcm = self._pcm
        self._pcm = None
        if pcm is not None:
            await pcm.aclose()

    async def _abort_resources(self) -> None:
        await self._tts.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._tts.force_abort()
