"""Null audio output that fully consumes PCM."""

import logging
from collections.abc import AsyncIterator


class NullAudioOutput:
    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self._logger.info("audio output running in null mode")
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def play(self, pcm: AsyncIterator[bytes]) -> None:
        async for _ in pcm:
            pass
