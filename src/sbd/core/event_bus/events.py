"""Event type definitions.

Three categories, distinguished by naming convention:
- Fact reports (past tense / state): WakeDetected, TranscriptReady, SpeechFinished
- Commands (imperative): StartListening, StopSpeaking, ExecuteTool
- State changes: StateChanged
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Fact reports ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WakeDetected:
    source: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UtteranceCaptured:
    pcm: bytes
    duration_ms: int


@dataclass(frozen=True)
class PerceptionResult:
    kind: str
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True)
class ToolExecuted:
    name: str
    result: Any


@dataclass(frozen=True)
class SpeechStarted:
    text: str


@dataclass(frozen=True)
class SpeechFinished:
    pass


@dataclass(frozen=True)
class TurnCompleted:
    pass


@dataclass(frozen=True)
class ErrorOccurred:
    where: str
    error: BaseException


@dataclass(frozen=True)
class InterruptRequested:
    pass


@dataclass(frozen=True)
class ShutdownRequested:
    pass


# ─── Commands ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StartListening:
    pass


@dataclass(frozen=True)
class StartPerception:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StartReasoning:
    input: PerceptionResult


@dataclass(frozen=True)
class ExecuteTool:
    call: ToolCall


@dataclass(frozen=True)
class SpeakRequested:
    text: str


@dataclass(frozen=True)
class StopSpeaking:
    pass


@dataclass(frozen=True)
class GoIdle:
    pass


# ─── State changes ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StateChanged:
    old: str
    new: str
