"""Vision adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@dataclass(frozen=True, slots=True)
class VisionResult:
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VisionAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def describe(self, image: bytes) -> VisionResult: ...


class MockVisionAdapter:
    def __init__(
        self,
        outcomes: tuple[VisionResult | Exception, ...] = (VisionResult("fixture scene"),),
        *,
        blocked: bool = False,
    ) -> None:
        self._outcomes = deque(outcomes)
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

    async def describe(self, image: bytes) -> VisionResult:
        self.entered.set()
        await self.release.wait()
        outcome = self._outcomes.popleft() if self._outcomes else VisionResult("")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
