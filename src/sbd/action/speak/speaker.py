"""Speak action worker."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable

from sbd.adaptor.errors import AdapterError
from sbd.action.speak.tts import TTSAdapter
from sbd.core.audio.base import AudioOutput
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ErrorOccurred
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime


class Speak(WorkerRuntime):
    def __init__(self, *, tts: TTSAdapter, audio_output: AudioOutput, bus: EventBus,
                 observe: Callable[[str], None] | None = None,
                 on_completion: Callable[[str], Awaitable[None] | None] | None = None,
                 before_start: Callable[[], Awaitable[None] | None] | None = None) -> None:
        super().__init__()
        self._tts = tts
        self._audio_output = audio_output
        self._bus = bus
        self._observe = observe
        self._on_completion = on_completion
        self._before_start = before_start
        self._pcm: AsyncIterator[bytes] | None = None

    async def start(self) -> None:
        await self._tts.start()

    async def stop(self) -> None:
        await self.abort()
        await self._tts.stop()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        async def body() -> None:
            fault: ComponentSystemFault | None = None
            cause: BaseException | None = None
            status = "error"
            text = payload.get("text") if type(payload) is dict else None
            if type(text) is str and text.strip() and set(payload) == {"text"}:
                try:
                    if self._before_start is not None:
                        started = self._before_start()
                        if inspect.isawaitable(started):
                            await started
                    self._pcm = self._tts.synthesize(text)
                    playback = self._pcm if self._observe is None else self._observed_pcm()
                    try:
                        await self._await_operation(self._audio_output.play(playback))
                    finally:
                        if playback is not self._pcm:
                            await playback.aclose()
                    status = "ok"
                except ComponentSystemFault as exc:
                    fault = exc
                    cause = exc.__cause__
                except AdapterError as exc:
                    if not self._may_publish():
                        status = "cancelled"
                    elif getattr(self._tts, "legacy_neutral", False):
                        status = "error"
                    else:
                        cause = exc
                        fault = ComponentSystemFault.create(
                            where="action.speak.tts",
                            code="TTS_GENERATION_FAILED",
                            backend=BackendDisposition.REBUILD_REQUIRED,
                            recovery_keys=("backend.action.speak.tts",),
                        )
                except asyncio.CancelledError:
                    status = "cancelled"
                    raise
                except Exception as exc:
                    cause = exc
                    fault = ComponentSystemFault.create(
                        where="action.speak.audio",
                        code="AUDIO_PLAYBACK_FAILED",
                        backend=BackendDisposition.UNPROVEN,
                        recovery_keys=("core.audio.output",),
                    )
                finally:
                    await self._close_pcm()
                    if self._on_completion is not None:
                        try:
                            completed = self._on_completion(status)
                            if inspect.isawaitable(completed):
                                await completed
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            # Do not bypass worker supervision from a finally
                            # callback, nor mask an already pending cancellation.
                            if status != "cancelled":
                                cause = exc
                                fault = ComponentSystemFault.create(
                                    where="action.speak",
                                    code="SPEAK_UNEXPECTED",
                                    backend=BackendDisposition.UNPROVEN,
                                    recovery_keys=("core.audio.output",),
                                )
            if fault is not None:
                await self._bus.publish(fault.to_event())
                if cause is None:
                    raise fault
                raise fault from cause
            if self._may_publish():
                await self._bus.publish(ActionCompleted("speak", status, {}, session_id, turn_id, correlation_id))
        await self._run_call(body)

    async def _observed_pcm(self) -> AsyncIterator[bytes]:
        first = True
        assert self._pcm is not None
        async for chunk in self._pcm:
            if first and type(chunk) is bytes and chunk:
                first = False
                assert self._observe is not None
                self._observe("tts_pcm_ready")
            yield chunk

    async def _close_pcm(self) -> None:
        pcm = self._pcm
        self._pcm = None
        if pcm is not None:
            await pcm.aclose()

    async def _abort_resources(self) -> None:
        await self._tts.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._tts.force_abort()
