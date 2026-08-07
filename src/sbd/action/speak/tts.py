"""TTS adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@runtime_checkable
class TTSAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    def synthesize(self, text: str) -> AsyncIterator[bytes]: ...


class MockTTSAdapter:
    def __init__(
        self,
        frames: tuple[bytes, ...] = (b"\x01\x00",),
        *,
        error: Exception | None = None,
        blocked: bool = False,
    ) -> None:
        self._frames = frames
        self._error = error
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        if not blocked:
            self.release.set()

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        self.release.set()

    async def abort(self) -> None:
        self.release.set()

    async def force_abort(self) -> ForceAbortReport:
        self.release.set()
        return ForceAbortReport()

    def synthesize(self, text: str) -> AsyncIterator[bytes]:
        async def generate() -> AsyncIterator[bytes]:
            self.entered.set()
            await self.release.wait()
            if self._error is not None:
                raise self._error
            for frame in self._frames:
                yield frame
        return generate()
