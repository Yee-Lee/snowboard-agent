"""External-message data and private ownership models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


MessageState = Literal["queued", "session", "pending", "turn"]
ReadWindowState = Literal["active", "closed"]


@dataclass(frozen=True, slots=True)
class ExternalMessage:
    message_id: str
    channel: str
    arrived_at: float
    sequence: int
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _BufferedMessage:
    value: ExternalMessage
    state: MessageState = "queued"
    session_id: str | None = None
    turn_id: int | None = None


@dataclass(slots=True)
class _ReadWindow:
    session_id: str
    turn_id: int
    state: ReadWindowState = "active"
