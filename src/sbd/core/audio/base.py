"""Audio HAL contract.

Only raw PCM in/out. VAD and segmentation belong to upper layers
(perception/listen, wake/voice).
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol


class AudioInput(Protocol):
    async def frames(self) -> AsyncIterator[bytes]:
        """Yield PCM frames from the microphone until stopped."""
        ...

    async def close(self) -> None: ...


class AudioOutput(Protocol):
    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        """Consume PCM frames and play to the speaker."""
        ...

    async def close(self) -> None: ...
