"""Startup-configured gain for the canonical S16_LE output stream."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from sbd.core.audio.base import AudioOutput


@runtime_checkable
class VolumeControl(Protocol):
    def get_volume_percent(self) -> int: ...
    def set_volume_percent(self, value: int) -> None: ...


def _validate_percent(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError("volume_percent must be an integer in 0..100")
    return value


class VolumeControlledAudioOutput:
    """Apply exactly one gain step before native AudioOutput adaptation."""

    def __init__(self, output: AudioOutput, volume_percent: int = 100) -> None:
        if not isinstance(output, AudioOutput):
            raise TypeError("output must implement AudioOutput")
        self._output = output
        self._volume_percent = _validate_percent(volume_percent)

    @property
    def raw_output(self) -> AudioOutput:
        """Composition/test identity; callers must play through this wrapper."""
        return self._output

    def get_volume_percent(self) -> int:
        return self._volume_percent

    def set_volume_percent(self, value: int) -> None:
        self._volume_percent = _validate_percent(value)

    async def start(self) -> None:
        await self._output.start()

    async def stop(self) -> None:
        await self._output.stop()

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        await self._output.play(self._scaled(pcm))

    async def _scaled(self, pcm: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        async for chunk in pcm:
            if type(chunk) is not bytes or len(chunk) % 2:
                raise ValueError("volume input requires complete S16_LE byte frames")
            percent = self._volume_percent
            if percent == 100:
                yield chunk
                continue
            if percent == 0:
                yield bytes(len(chunk))
                continue
            scaled = bytearray(len(chunk))
            for offset in range(0, len(chunk), 2):
                sample = int.from_bytes(chunk[offset:offset + 2], "little", signed=True)
                value = (abs(sample) * percent // 100) * (-1 if sample < 0 else 1)
                scaled[offset:offset + 2] = value.to_bytes(2, "little", signed=True)
            yield bytes(scaled)


__all__ = ["VolumeControl", "VolumeControlledAudioOutput"]
