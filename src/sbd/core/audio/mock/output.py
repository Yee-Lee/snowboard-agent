"""Mock audio output recording consumed PCM frames."""

from collections.abc import AsyncIterator

from sbd.core.audio.null.output import NullAudioOutput


class MockAudioOutput(NullAudioOutput):
    def __init__(self) -> None:
        super().__init__()
        self.frames_played: list[bytes] = []

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        async for frame in pcm:
            self.frames_played.append(frame)
