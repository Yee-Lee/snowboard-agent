"""Selected M3 Option A ALSA capture and explicit input adaptation."""

from __future__ import annotations

import asyncio
import struct
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sbd.core.config.models import AudioConfig


NATIVE_RATE = 48_000
NATIVE_CHANNELS = 2
NATIVE_PERIOD_FRAMES = 960
NATIVE_PERIODS = 4
STREAM_SAMPLES = 320
STREAM_BYTES = 640
_NATIVE_FRAME_BYTES = NATIVE_CHANNELS * 4


class _AlsaFrameStream(AsyncIterator[bytes]):
    def __init__(self, owner: "AlsaAudioInput") -> None:
        self._owner = owner
        self._closed = False

    def __aiter__(self) -> "_AlsaFrameStream":
        return self

    async def __anext__(self) -> bytes:
        if self._closed:
            raise StopAsyncIteration
        return await self._owner._next_frame(self)

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._owner._release(self)


class AlsaAudioInput:
    """One-worker ALSA capture with selected 48k stereo → 16k mono adaptation.

    ``source_factory`` and ``resampler_factory`` are private test seams.  The
    production defaults are lazy imports, so default host imports never load
    ALSA, numpy, or samplerate.
    """

    def __init__(
        self,
        config: AudioConfig,
        *,
        source_factory: Callable[[], Any] | None = None,
        resampler_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._config = config
        self._source_factory = source_factory or self._make_alsa_source
        self._resampler_factory = resampler_factory or self._make_resampler
        self._executor: ThreadPoolExecutor | None = None
        self._source: Any | None = None
        self._resampler: Any | None = None
        self._raw = bytearray()
        self._samples: list[int] = []
        self._active: _AlsaFrameStream | None = None
        self._native_info: dict[str, Any] | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            raise RuntimeError("ALSA audio input already started")
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sbd-alsa-capture")
        try:
            await self._run_worker(self._ensure_open_worker)
        except Exception:
            self._shutdown_executor()
            raise
        self._started = True

    async def stop(self) -> None:
        active = self._active
        if active is not None:
            active._closed = True
            self._active = None
        if self._executor is not None:
            try:
                await self._run_worker(self._close_worker)
            finally:
                self._shutdown_executor()
        self._started = False

    def frames(self) -> AsyncIterator[bytes]:
        if not self._started:
            raise RuntimeError("ALSA audio input is not started")
        if self._active is not None:
            raise RuntimeError("AudioInput already streaming")
        stream = _AlsaFrameStream(self)
        self._active = stream
        return stream

    async def _next_frame(self, stream: _AlsaFrameStream) -> bytes:
        if self._active is not stream or not self._started:
            raise StopAsyncIteration
        try:
            frame = await self._run_worker(self._next_frame_worker)
        except asyncio.CancelledError:
            # Cancellation is a normal stream-termination path.  Since
            # CancelledError is a BaseException on supported Python versions,
            # it must be handled explicitly or the active owner and ALSA
            # source remain attached to this input instance.
            task = asyncio.current_task()
            cancelling = task.cancelling() if task and hasattr(task, "cancelling") else 0
            if cancelling > 0:
                task.uncancel()
            try:
                await self._release(stream)
            finally:
                if cancelling > 0:
                    raise asyncio.CancelledError()
            raise
        except Exception:
            await self._release(stream)
            raise
        if len(frame) != STREAM_BYTES:
            await self._release(stream)
            raise RuntimeError("selected audio adapter produced an invalid frame length")
        return frame

    async def _release(self, stream: _AlsaFrameStream) -> None:
        if self._active is stream:
            self._active = None
            if self._executor is not None:
                await self._run_worker(self._close_worker)

    async def _run_worker(self, operation: Callable[[], Any]) -> Any:
        executor = self._executor
        if executor is None:
            raise RuntimeError("ALSA capture worker is unavailable")
        return await asyncio.get_running_loop().run_in_executor(executor, operation)

    def _ensure_open_worker(self) -> None:
        if self._source is None:
            self._source = self._source_factory()
        if self._resampler is None:
            self._resampler = self._resampler_factory()

    def _next_frame_worker(self) -> bytes:
        self._ensure_open_worker()
        while len(self._samples) < STREAM_SAMPLES:
            assert self._source is not None
            try:
                payload = self._read_payload(self._source.read())
            except StopIteration:
                payload = b""
            if not payload:
                raise EOFError("ALSA capture returned no frames")
            self._raw.extend(payload)
            complete = len(self._raw) // _NATIVE_FRAME_BYTES * _NATIVE_FRAME_BYTES
            if not complete:
                continue
            native = self._raw[:complete]
            del self._raw[:complete]
            selected = self._decode_selected_channel(native)
            assert self._resampler is not None
            converted = self._resampler.process(selected, 1 / 3)
            self._samples.extend(self._to_s16(sample) for sample in converted)
        frame = self._samples[:STREAM_SAMPLES]
        del self._samples[:STREAM_SAMPLES]
        return struct.pack("<320h", *frame)

    def _close_worker(self) -> None:
        source, self._source = self._source, None
        self._resampler = None
        self._raw.clear()
        self._samples.clear()
        self._native_info = None
        if source is not None:
            close = getattr(source, "close", None)
            if close is not None:
                close()

    def _shutdown_executor(self) -> None:
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    def _decode_selected_channel(self, raw: bytes) -> list[float]:
        channel = self._config.input.channel_index
        if channel not in {0, 1}:
            raise ValueError("selected ALSA input channel is invalid")
        return [
            (struct.unpack_from("<i", raw, offset + channel * 4)[0] >> 8) / 8_388_608
            for offset in range(0, len(raw), _NATIVE_FRAME_BYTES)
        ]

    @staticmethod
    def _to_s16(sample: float) -> int:
        return max(-32_768, min(32_767, round(float(sample) * 32_768)))

    @staticmethod
    def _read_payload(result: Any) -> bytes:
        if isinstance(result, tuple):
            count, payload = result
            if count < 0:
                raise OSError(f"ALSA read failed with status {count}")
            return bytes(payload)
        return bytes(result)

    def _make_alsa_source(self) -> Any:
        try:
            import alsaaudio
        except ImportError as exc:
            raise RuntimeError("pyalsaaudio==0.11.0 is required for core.audio.driver=alsa") from exc
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            device=self._config.input.device,
        )
        pcm.setchannels(NATIVE_CHANNELS)
        pcm.setrate(NATIVE_RATE)
        pcm.setformat(alsaaudio.PCM_FORMAT_S32_LE)
        pcm.setperiodsize(NATIVE_PERIOD_FRAMES)
        if hasattr(pcm, "setperiods"):
            pcm.setperiods(NATIVE_PERIODS)
        info = pcm.info()
        actual = (
            info.get("rate"), info.get("channels"),
            str(info.get("format_name", "")).upper(), info.get("period_size"),
        )
        expected = (NATIVE_RATE, NATIVE_CHANNELS, "S32_LE", NATIVE_PERIOD_FRAMES)
        if actual != expected:
            pcm.close()
            raise RuntimeError(
                f"ALSA capture negotiation mismatch: expected={expected} actual={actual}"
            )
        self._native_info = dict(info)
        return pcm

    @staticmethod
    def _make_resampler() -> Any:
        try:
            import numpy as np
            import samplerate
        except ImportError as exc:
            raise RuntimeError("samplerate==0.2.4 and numpy are required for ALSA input adaptation") from exc

        class _SelectedResampler:
            def __init__(self) -> None:
                self._resampler = samplerate.Resampler(converter_type="sinc_best", channels=1)

            def process(self, samples: list[float], ratio: float):
                return self._resampler.process(np.asarray(samples, dtype=np.float32), ratio=ratio)

        return _SelectedResampler()
