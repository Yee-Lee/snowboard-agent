"""Event dataclasses, type aliases, and ID generation.

Authoritative source: docs/implement/ch01_events.md
All events are @dataclass(frozen=True, slots=True) with no internal version field.
Nested payloads (dict/list) are protected by behavioural contract, not deep-copy.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias


# ---------------------------------------------------------------------------
# 1.1  Shared types & identifiers
# ---------------------------------------------------------------------------

SessionId: TypeAlias = str
TurnId: TypeAlias = int
CorrelationId: TypeAlias = int
MessageId: TypeAlias = str


def new_session_id() -> SessionId:
    """Generate a new UUIDv4 session identifier."""
    return str(uuid.uuid4())


def new_message_id() -> MessageId:
    """Generate a new UUIDv4 message identifier."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# 1.2  State literal
# ---------------------------------------------------------------------------

State: TypeAlias = Literal[
    "IDLE", "WAKE", "PERCEPTION", "THINK", "ACTION", "ERROR"
]


# ---------------------------------------------------------------------------
# 1.3  Worker Facts
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PerceptionResult:
    """Terminal fact from a perception worker."""

    kind: Literal["listen", "read", "look"]
    status: Literal["ok", "timeout", "error"]
    text: str | None
    extra: dict[str, Any] = field(default_factory=dict)
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Terminal fact from the Reasoner."""

    action_kind: Literal["speak", "tool", "rest"]
    action_payload: dict[str, Any]
    next_perceptions: tuple[str, ...]
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0


@dataclass(frozen=True, slots=True)
class ActionCompleted:
    """Terminal fact from an action worker."""

    kind: Literal["speak", "tool", "rest"]
    status: Literal["ok", "error"]
    result: dict[str, Any] = field(default_factory=dict)
    session_id: SessionId = ""
    turn_id: TurnId = 0
    correlation_id: CorrelationId = 0


@dataclass(frozen=True, slots=True)
class ErrorOccurred:
    """Observer-only error event.  No session/turn/severity fields."""

    where: str
    error: str
    exception_type: str | None = None


# ---------------------------------------------------------------------------
# 1.4  State Broadcast
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StateChanged:
    """Published on every SM state transition."""

    old: State
    new: State
    at: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# 1.5  Signals
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ButtonPressed:
    """GPIO button event."""

    button_id: str
    duration_ms: int


@dataclass(frozen=True, slots=True)
class ExternalMessageArrived:
    """External message buffered and ready for consumption."""

    channel: str
    arrived_at: float
    message_id: MessageId


@dataclass(frozen=True, slots=True)
class WakeWordDetected:
    """Voice wake word detected by daemon."""

    phrase: str
    confidence: float


@dataclass(frozen=True, slots=True)
class InterruptRequested:
    """User-initiated interrupt signal."""

    pass


@dataclass(frozen=True, slots=True)
class ShutdownRequested:
    """System shutdown signal."""

    pass


# ---------------------------------------------------------------------------
# 1.6  Event family union aliases
# ---------------------------------------------------------------------------

WorkerFact: TypeAlias = (
    PerceptionResult | LLMResponse | ActionCompleted | ErrorOccurred
)

StateBroadcast: TypeAlias = StateChanged

Signal: TypeAlias = (
    ButtonPressed
    | ExternalMessageArrived
    | WakeWordDetected
    | InterruptRequested
    | ShutdownRequested
)

Event: TypeAlias = WorkerFact | StateBroadcast | Signal
