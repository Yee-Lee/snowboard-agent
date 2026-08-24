"""Selected M3 direct ALSA playback backend."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from .adaptation import StreamFormatAdapter
from sbd.core.config.models import AudioConfig


_NATIVE_FRAME_BYTES = 8  # 48 kHz / stereo / S32_LE
_STREAM_FRAME_BYTES = 2  # 16 kHz / mono / S16_LE


class AlsaAudioOutput:
    def __init__(
        self, config: AudioConfig, *, adapter_factory: Callable[[], StreamFormatAdapter] | None = None,
    ) -> None:
        self._config = config
        stream = config.output.stream_format
        native = config.output.native_format or stream
        if (native.sample_rate, native.channels, native.sample_format) != (48_000, 2, "s32_le"):
            raise ValueError("AlsaAudioOutput native format must be 48kHz/stereo/S32_LE")
        if native != stream and not (
            (stream.sample_rate, stream.channels, stream.sample_format) == (16_000, 1, "s16_le")
            and (native.sample_rate, native.channels, native.sample_format) == (48_000, 2, "s32_le")
        ):
            raise ValueError(
                "AlsaAudioOutput supports only 16kHz/mono/S16_LE to 48kHz/stereo/S32_LE conversion"
            )
        self._adapter = (
            (adapter_factory or StreamFormatAdapter)() if native != stream else None
        )
        self._executor: ThreadPoolExecutor | None = None
        self._pcm: Any | None = None
        self._native_info: dict[str, Any] | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            raise RuntimeError("ALSA audio output already started")
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sbd-alsa-playback")
        try:
            await self._run(self._open_worker)
        except Exception:
            await self._shutdown_executor()
            raise
        self._started = True

    async def stop(self) -> None:
        if self._executor is not None:
            try:
                await self._run(self._close_worker)
            finally:
                await self._shutdown_executor()
        self._started = False
        self._reset_adapter()

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        if not self._started:
            raise RuntimeError("ALSA audio output is not started")
        adapter = self._adapter
        self._reset_adapter()
        try:
            async for chunk in pcm:
                frame_bytes = _STREAM_FRAME_BYTES if adapter is not None else _NATIVE_FRAME_BYTES
                if type(chunk) is not bytes or len(chunk) % frame_bytes:
                    description = "16k mono S16_LE" if adapter is not None else "48k stereo S32_LE"
                    raise ValueError(f"ALSA output requires complete {description} frames")
                native = adapter.convert(chunk) if adapter is not None else chunk
                if native:
                    await self._run(lambda payload=native: self._write_worker(payload))
            if adapter is not None:
                tail = adapter.flush()
                if tail:
                    await self._run(lambda payload=tail: self._write_worker(payload))
            # A successful play() means the physical device has consumed the
            # complete stream, not merely that ALSA accepted it into a userspace
            # or kernel buffer.  snd_pcm_close() drops queued playback, so an
            # explicit drain is required before the success path returns.
            # Error and cancellation paths skip this call and retain the bounded
            # close/drop behavior in stop().
            await self._run(self._drain_worker)
        finally:
            self._reset_adapter()

    async def _run(self, operation):
        executor = self._executor
        if executor is None:
            raise RuntimeError("ALSA playback worker is unavailable")
        # Keep native calls on one worker without using run_in_executor().
        # On the supported Python 3.12 runtime, the second bridged future can
        # remain pending after the worker has completed; polling preserves
        # cancellation responsiveness and deterministic cleanup.
        worker_future = executor.submit(operation)
        while not worker_future.done():
            await asyncio.sleep(0.001)
        return worker_future.result()

    def _open_worker(self) -> None:
        try:
            import alsaaudio
        except ImportError as exc:
            raise RuntimeError("pyalsaaudio==0.11.0 is required for core.audio.driver=alsa") from exc
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_PLAYBACK,
            mode=alsaaudio.PCM_NORMAL,
            device=self._config.output.device,
        )
        pcm.setchannels(2)
        pcm.setrate(48_000)
        pcm.setformat(alsaaudio.PCM_FORMAT_S32_LE)
        pcm.setperiodsize(960)
        if hasattr(pcm, "setperiods"):
            pcm.setperiods(4)
        info = pcm.info()
        actual = (
            info.get("rate"), info.get("channels"),
            str(info.get("format_name", "")).upper(), info.get("period_size"),
        )
        expected = (48_000, 2, "S32_LE", 960)
        if actual != expected:
            pcm.close()
            raise RuntimeError(
                f"ALSA playback negotiation mismatch: expected={expected} actual={actual}"
            )
        self._native_info = dict(info)
        self._pcm = pcm

    def _write_worker(self, chunk: bytes) -> None:
        if self._pcm is None:
            raise RuntimeError("ALSA playback is unavailable")
        remaining = memoryview(chunk)
        while remaining:
            written = self._pcm.write(remaining.tobytes())
            if not isinstance(written, int):
                raise OSError("ALSA write returned a non-integer frame count")
            if written < 0:
                raise OSError(f"ALSA write failed with status {written}")
            if written == 0:
                raise OSError("ALSA write made no progress")
            consumed = written * _NATIVE_FRAME_BYTES
            if consumed > len(remaining):
                raise OSError("ALSA write returned an invalid frame count")
            remaining = remaining[consumed:]

    def _drain_worker(self) -> None:
        if self._pcm is None:
            raise RuntimeError("ALSA playback is unavailable")
        drain = getattr(self._pcm, "drain", None)
        if drain is None:
            raise RuntimeError("ALSA playback completion requires drain support")
        drain()

    def _close_worker(self) -> None:
        pcm, self._pcm = self._pcm, None
        self._native_info = None
        if pcm is not None and hasattr(pcm, "close"):
            pcm.close()

    def _reset_adapter(self) -> None:
        if self._adapter is not None:
            self._adapter.reset()

    async def _shutdown_executor(self) -> None:
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
