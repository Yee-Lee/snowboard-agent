"""ASR adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@dataclass(frozen=True, slots=True)
class ASRResult:
    text: str
    confidence: float | None = None
    language: str | None = None


@runtime_checkable
class ASRAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def transcribe(self, frames: AsyncIterator[bytes]) -> ASRResult: ...


class MockASRAdapter:
    def __init__(
        self,
        outcomes: tuple[ASRResult | Exception, ...] = (ASRResult("fixture transcript"),),
        *,
        blocked: bool = False,
    ) -> None:
        self._outcomes = deque(outcomes)
        self._blocked = blocked
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

    async def transcribe(self, frames: AsyncIterator[bytes]) -> ASRResult:
        self.entered.set()
        await self.release.wait()
        await anext(frames)
        outcome = self._outcomes.popleft() if self._outcomes else ASRResult("")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
