"""Selected M3 direct ALSA playback backend."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sbd.core.config.models import AudioConfig


_NATIVE_FRAME_BYTES = 8  # 48 kHz / stereo / S32_LE


class AlsaAudioOutput:
    def __init__(self, config: AudioConfig) -> None:
        self._config = config
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
            self._shutdown_executor()
            raise
        self._started = True

    async def stop(self) -> None:
        if self._executor is not None:
            try:
                await self._run(self._close_worker)
            finally:
                self._shutdown_executor()
        self._started = False

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        if not self._started:
            raise RuntimeError("ALSA audio output is not started")
        async for chunk in pcm:
            if type(chunk) is not bytes or len(chunk) % _NATIVE_FRAME_BYTES:
                raise ValueError("ALSA output requires complete 48k stereo S32_LE frames")
            await self._run(lambda: self._write_worker(chunk))

    async def _run(self, operation):
        if self._executor is None:
            raise RuntimeError("ALSA playback worker is unavailable")
        return await asyncio.get_running_loop().run_in_executor(self._executor, operation)

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

    def _close_worker(self) -> None:
        pcm, self._pcm = self._pcm, None
        self._native_info = None
        if pcm is not None and hasattr(pcm, "close"):
            pcm.close()

    def _shutdown_executor(self) -> None:
        executor, self._executor = self._executor, None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
