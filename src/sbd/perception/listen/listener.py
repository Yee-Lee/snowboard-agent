"""Listen perception worker."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable

from sbd.adaptor.errors import AdapterError, AdapterRejected
from sbd.core.audio.base import AudioInput
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.faults import (
    BackendDisposition,
    ComponentSystemFault,
    legacy_error_event,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime
from sbd.perception.listen.asr import ASRAdapter


class _AudioCaptureFailure(RuntimeError):
    pass


class Listen(WorkerRuntime):
    def __init__(self, *, audio_input: AudioInput, asr: ASRAdapter, bus: EventBus,
                 observe: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._audio_input = audio_input
        self._asr = asr
        self._bus = bus
        self._observe = observe
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
            fault: ComponentSystemFault | None = None
            cause: BaseException | None = None
            self._frames = self._audio_input.frames()
            try:
                async with asyncio.timeout(timeout_seconds):
                    value = await self._await_operation(
                        self._asr.transcribe(self._capture_frames())
                    )
                if self._observe is not None:
                    self._observe("asr_final")
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
            except TimeoutError as exc:
                await self._asr.abort()
                if self._asr.ready_for_next:
                    result = PerceptionResult(
                        "listen", "timeout", None, {},
                        session_id, turn_id, correlation_id,
                    )
                else:
                    cause = exc
                    fault = ComponentSystemFault.create(
                        where="perception.listen",
                        code="ASR_TIMEOUT_UNPROVEN",
                        backend=BackendDisposition.UNPROVEN,
                        recovery_keys=("backend.perception.listen.asr",),
                    )
            except AdapterRejected as exc:
                code = getattr(exc, "code", None)
                extra = {"asr_error_code": code} if code in {
                    "NO_SPEECH", "MULTIPLE_UTTERANCES"
                } else {}
                result = PerceptionResult(
                    "listen", "error", None, extra,
                    session_id, turn_id, correlation_id,
                )
            except ComponentSystemFault as exc:
                fault = exc
                cause = exc.__cause__
            except AdapterError as exc:
                cause = exc
                fault = ComponentSystemFault.create(
                    where="perception.listen",
                    code="ASR_PROTOCOL_FAILED",
                    backend=BackendDisposition.UNPROVEN,
                    recovery_keys=("backend.perception.listen.asr",),
                )
            except asyncio.CancelledError:
                raise
            except _AudioCaptureFailure as exc:
                cause = exc
                fault = ComponentSystemFault.create(
                    where="perception.listen",
                    code="AUDIO_CAPTURE_FAILED",
                    backend=BackendDisposition.UNPROVEN,
                    recovery_keys=("core.audio.input",),
                )
            except Exception as exc:
                if getattr(self._asr, "legacy_neutral", False):
                    await self._bus.publish(legacy_error_event(
                        where="perception.listen",
                        error="listen failed",
                        exception_type=type(exc).__name__,
                    ))
                    raise
                cause = exc
                fault = ComponentSystemFault.create(
                    where="perception.listen",
                    code="ASR_UNEXPECTED",
                    backend=BackendDisposition.UNPROVEN,
                    recovery_keys=("backend.perception.listen.asr",),
                )
            finally:
                await self._close_frames()
            if fault is not None:
                await self._bus.publish(fault.to_event())
                if cause is None:
                    raise fault
                raise fault from cause
            if result is not None and self._may_publish():
                await self._bus.publish(result)

        await self._run_call(body)

    async def _close_frames(self) -> None:
        frames = self._frames
        self._frames = None
        if frames is not None:
            await frames.aclose()

    async def _capture_frames(self) -> AsyncIterator[bytes]:
        frames = self._frames
        assert frames is not None
        try:
            async for frame in frames:
                yield frame
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise _AudioCaptureFailure() from exc

    async def _abort_resources(self) -> None:
        await self._asr.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._asr.force_abort()
