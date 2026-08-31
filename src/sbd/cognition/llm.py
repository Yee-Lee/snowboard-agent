"""Structured LLM adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Protocol, runtime_checkable

from sbd.cognition.prompt_builder import ReasoningInput
from sbd.core.lifecycle import ForceAbortReport

if TYPE_CHECKING:
    from sbd.core.resource_manager.models import RecoveryTicket


@dataclass(frozen=True, slots=True)
class LLMGenerationMetrics:
    init_ms: float
    ttft_ms: float
    prefill_tokens: int
    prefill_tokens_per_second: float
    decode_tokens: int
    decode_tokens_per_second: float
    kv_tokens: int


@dataclass(frozen=True, slots=True)
class LLMGeneration:
    response: Mapping[str, object]
    metrics: LLMGenerationMetrics


@dataclass(frozen=True, slots=True)
class LLMResourceSample:
    owner_pss_bytes: int
    mem_available_bytes: int


@runtime_checkable
class LLMResourceSampler(Protocol):
    def sample(self, *, child_pid: int, child_pgid: int) -> LLMResourceSample: ...


@runtime_checkable
class ScheduleRecovery(Protocol):
    def __call__(self, keys: tuple[str, ...]) -> RecoveryTicket: ...


@runtime_checkable
class WaitRecovery(Protocol):
    async def __call__(self, ticket: RecoveryTicket) -> None: ...


@runtime_checkable
class LLMEngineAdapter(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...
    async def generate(self, value: ReasoningInput) -> LLMGeneration: ...


class MockLLMEngineAdapter:
    def __init__(
        self,
        outcomes: tuple[LLMGeneration | Exception, ...],
        *,
        blocked: bool = False,
    ) -> None:
        self._outcomes = deque(outcomes)
        self.inputs: list[ReasoningInput] = []
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

    async def generate(self, value: ReasoningInput) -> LLMGeneration:
        self.inputs.append(value)
        self.entered.set()
        await self.release.wait()
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


__all__ = [
    "LLMEngineAdapter",
    "LLMGeneration",
    "LLMGenerationMetrics",
    "LLMResourceSample",
    "LLMResourceSampler",
    "MockLLMEngineAdapter",
    "ScheduleRecovery",
    "WaitRecovery",
]
