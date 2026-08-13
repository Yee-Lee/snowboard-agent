"""Format-valid, exclusive null audio input."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from sbd.core.config.models import AudioConfig


class _FrameStream(AsyncIterator[bytes]):
    def __init__(
        self,
        owner: "NullAudioInput",
        frames: tuple[bytes, ...] | None,
    ) -> None:
        self._owner = owner
        self._frames = frames
        self._index = 0
        self._closed = False

    def __aiter__(self) -> "_FrameStream":
        return self

    async def __anext__(self) -> bytes:
        if self._closed:
            raise StopAsyncIteration
        if self._frames is not None:
            if self._index >= len(self._frames):
                await self.aclose()
                raise StopAsyncIteration
            value = self._frames[self._index]
            self._index += 1
            return value
        await asyncio.sleep(self._owner.frame_duration_seconds)
        if self._closed:
            raise StopAsyncIteration
        return self._owner.silence_frame

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._owner._release(self)


class NullAudioInput:
    def __init__(
        self,
        config: AudioConfig | None = None,
        *,
        finite_frames: tuple[bytes, ...] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config or AudioConfig(driver="null")
        self._logger = logger or logging.getLogger(__name__)
        input_config = self._config.input
        stream_format = input_config.stream_format
        samples = stream_format.sample_rate * input_config.frame_duration_ms // 1000
        container_bytes = {"s16_le": 2, "s32_le": 4}[stream_format.sample_format]
        self.silence_frame = bytes(
            samples * stream_format.channels * container_bytes
        )
        self.frame_duration_seconds = input_config.frame_duration_ms / 1000.0
        self._finite_frames = finite_frames
        self._active: _FrameStream | None = None
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self._logger.info("audio input running in null mode")
        self._started = True

    async def stop(self) -> None:
        active = self._active
        if active is not None:
            await active.aclose()
        self._started = False

    def frames(self) -> AsyncIterator[bytes]:
        if self._active is not None:
            raise RuntimeError("AudioInput already streaming")
        stream = _FrameStream(self, self._finite_frames)
        self._active = stream
        return stream

    def _release(self, stream: _FrameStream) -> None:
        if self._active is stream:
            self._active = None
