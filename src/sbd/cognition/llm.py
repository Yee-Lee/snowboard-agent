"""Structured LLM adapter protocol and deterministic mock."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Mapping, Protocol, runtime_checkable

from sbd.cognition.prompt_builder import ReasoningInput
from sbd.core.lifecycle import ForceAbortReport

if TYPE_CHECKING:
    from sbd.cognition.litert_lm.resource import SystemResourceSample
    from sbd.core.resource_manager.models import RecoveryTicket
    from sbd.core.state_manager.ports import ConversationReady, ConversationOpenRejected, ConversationCloseProof


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
class AdmissionSnapshot:
    ticket: str
    session_id: str
    generation: int
    input_sha256: str
    user_tokens: int
    current_kv_tokens: int
    rendered_incremental_tokens: int
    runtime_prefill_tokens: int
    output_reserve_tokens: int
    engine_context_tokens: int


@dataclass(frozen=True, slots=True)
class TicketDiscardProof:
    session_id: str
    generation: int
    conversation_revision: int
    ticket: str
    input_sha256: str
    native_render_scrubbed: Literal[True]
    ticket_invalidated: Literal[True]
    private_input_erased: Literal[True]
    conversation_state: Literal["ready"]


@dataclass(frozen=True, slots=True)
class GenerationMetrics:
    user_tokens: int
    current_kv_tokens: int
    rendered_incremental_tokens: int
    runtime_prefill_tokens: int
    decode_tokens: int
    conversation_kv_tokens: int
    llm_send_monotonic_ns: int
    first_safe_text_monotonic_ns: int | None
    terminal_monotonic_ns: int


@dataclass(frozen=True, slots=True)
class SemanticGeneration:
    text: str
    end: bool
    safe_fragments: tuple[str, ...]
    metrics: GenerationMetrics


class LLMFatalError(RuntimeError):
    """Unsafe backend/protocol failure; never a retry Fact."""


class ReplaceableGenerationFailure(RuntimeError):
    request_terminal_proven = True
    engine_usable = True

    def __init__(self, code: str) -> None:
        if code not in {"INVALID_SEMANTIC", "GENERATION_REJECTED", "GENERATION_TIMEOUT"}:
            raise LLMFatalError("invalid replaceable failure code")
        self.code = code
        super().__init__(code)


class MemoryAdmissionDenied(RuntimeError):
    def __init__(self, *, speak_allowed: bool) -> None:
        self.speak_allowed = speak_allowed
        super().__init__("MEMORY_NOTICE" if speak_allowed else "MEMORY_SILENT")


@dataclass(frozen=True, slots=True)
class LLMResourceSample:
    owner_pss_bytes: int
    mem_available_bytes: int


@runtime_checkable
class LLMResourceSampler(Protocol):
    def sample(self, *, child_pid: int, child_pgid: int) -> SystemResourceSample: ...


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
    async def open_conversation(self, session_id: str, generation: int) -> ConversationReady | ConversationOpenRejected: ...
    async def measure(self, session_id: str, generation: int, text: str) -> AdmissionSnapshot: ...
    async def discard_ticket(self, snapshot: AdmissionSnapshot) -> TicketDiscardProof: ...
    async def generate(self, snapshot: AdmissionSnapshot, text: str) -> SemanticGeneration: ...
    async def close_conversation(self, session_id: str, generation: int, reason: str) -> ConversationCloseProof: ...


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
    "AdmissionSnapshot",
    "TicketDiscardProof",
    "GenerationMetrics",
    "SemanticGeneration",
    "LLMFatalError",
    "ReplaceableGenerationFailure",
    "MemoryAdmissionDenied",
    "LLMEngineAdapter",
    "LLMGeneration",
    "LLMGenerationMetrics",
    "LLMResourceSample",
    "LLMResourceSampler",
    "MockLLMEngineAdapter",
    "ScheduleRecovery",
    "WaitRecovery",
]
