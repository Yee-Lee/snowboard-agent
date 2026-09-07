"""Single-flight ownership for a clean held MVA Conversation.

This is POC orchestration only. It prevents a late pre-open result, expired hold,
or identity mismatch from being adopted by a product session.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, Callable

from poc_llm.harness.mva_contract import ContractViolation, validate_session_facts


@dataclass(frozen=True)
class ReadinessIdentity:
    facts_digest: str
    profile_digest: str
    child_generation: int


class ReadinessError(ContractViolation):
    pass


class ConversationReadinessPool:
    """Own zero or one opening/held/adopted Conversation at a time."""

    def __init__(self, close: Callable[[Any], None], *, hold_seconds: float = 30.0) -> None:
        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be positive")
        self._close = close
        self._hold_seconds = hold_seconds
        self._lock = threading.Lock()
        self._state = "EMPTY"
        self._generation = 0
        self._identity: ReadinessIdentity | None = None
        self._conversation: Any | None = None
        self._held_at: float | None = None

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def live_count(self) -> int:
        with self._lock:
            return int(self._state in {"OPENING", "HELD", "ADOPTED"})

    def begin_open(self, identity: ReadinessIdentity, facts: object) -> int:
        validate_session_facts(facts)
        if not isinstance(identity, ReadinessIdentity):
            raise ReadinessError("invalid readiness identity")
        with self._lock:
            if self._state != "EMPTY":
                raise ReadinessError("readiness open is single-flight")
            self._generation += 1
            self._state = "OPENING"
            self._identity = identity
            return self._generation

    def finish_open(self, ticket: int, conversation: Any, *, now: float) -> bool:
        stale = False
        with self._lock:
            if (self._state != "OPENING" or ticket != self._generation
                    or conversation is None):
                stale = conversation is not None
            else:
                self._conversation = conversation
                self._held_at = now
                self._state = "HELD"
                return True
        if stale:
            self._close(conversation)
        return False

    def cancel_open(self) -> bool:
        with self._lock:
            if self._state != "OPENING":
                return False
            self._generation += 1
            self._state = "EMPTY"
            self._identity = None
            return True

    def adopt(self, identity: ReadinessIdentity, *, now: float) -> Any | None:
        close_value = None
        with self._lock:
            if self._state != "HELD":
                return None
            assert self._held_at is not None
            if identity != self._identity or now - self._held_at > self._hold_seconds:
                close_value = self._take_locked()
            else:
                conversation = self._conversation
                self._state = "ADOPTED"
                self._held_at = None
                return conversation
        if close_value is not None:
            self._close(close_value)
        return None

    def close_unclaimed(self) -> bool:
        with self._lock:
            if self._state != "HELD":
                return False
            conversation = self._take_locked()
        self._close(conversation)
        return True

    def release_adopted(self, conversation: Any) -> None:
        with self._lock:
            if self._state != "ADOPTED" or conversation is not self._conversation:
                raise ReadinessError("conversation ownership mismatch")
            owned = self._take_locked()
        self._close(owned)

    def _take_locked(self) -> Any:
        conversation = self._conversation
        self._conversation = None
        self._identity = None
        self._held_at = None
        self._state = "EMPTY"
        return conversation
