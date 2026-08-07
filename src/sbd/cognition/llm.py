"""LLM adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@dataclass(frozen=True, slots=True)
class LLMGeneration:
    text: str
    finish_reason: str | None = None


@runtime_checkable
class LLMEngineAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def generate(self, prompt: str) -> LLMGeneration: ...


class MockLLMEngineAdapter:
    def __init__(
        self,
        outcomes: tuple[LLMGeneration | Exception, ...],
        *,
        blocked: bool = False,
    ) -> None:
        self._outcomes = deque(outcomes)
        self.prompts: list[str] = []
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

    async def generate(self, prompt: str) -> LLMGeneration:
        self.prompts.append(prompt)
        self.entered.set()
        await self.release.wait()
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
