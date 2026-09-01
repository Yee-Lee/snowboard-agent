"""Deterministic fake runtime for AR1M0 protocol and lifecycle verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic

from .protocol import (
    ErrorCode,
    EventKind,
    PCMChunk,
    ProtocolError,
    SessionState,
    TranscriptAlternative,
    TranscriptEvent,
)


@dataclass
class _Session:
    state: SessionState = SessionState.OPEN
    next_chunk_sequence: int = 0
    last_timestamp_ms: int = -1
    event_sequence: int = 0
    chunks: list[bytes] = field(default_factory=list)


class FakeStreamingRuntime:
    """In-memory fake; it never imports, loads, or executes a real model."""

    MODEL_ID = "fake-asr-ar1m0-v1"

    def __init__(self) -> None:
        self._model_loaded = False
        self._shutdown = False
        self._sessions: dict[str, _Session] = {}
        self._next_session = 1

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def load_model(self) -> str:
        self._require_running()
        self._model_loaded = True
        return self.MODEL_ID

    def create_session(self) -> str:
        self._require_running()
        if not self._model_loaded:
            raise ProtocolError(ErrorCode.INVALID_STATE, "load the fake model first")
        session_id = f"fake-session-{self._next_session}"
        self._next_session += 1
        self._sessions[session_id] = _Session()
        return session_id

    def state(self, session_id: str) -> SessionState:
        return self._session(session_id).state

    def accept_chunk(self, chunk: PCMChunk) -> TranscriptEvent:
        self._require_running()
        session = self._session(chunk.session_id)
        if session.state not in {SessionState.OPEN, SessionState.STREAMING}:
            raise ProtocolError(ErrorCode.INVALID_STATE, "session no longer accepts PCM")
        if chunk.sequence != session.next_chunk_sequence:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "chunk sequence is not contiguous")
        if chunk.timestamp_ms <= session.last_timestamp_ms:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "chunk timestamp is not increasing")
        session.state = SessionState.STREAMING
        session.next_chunk_sequence += 1
        session.last_timestamp_ms = chunk.timestamp_ms
        session.chunks.append(chunk.samples_s16le)
        event = TranscriptEvent(
            kind=EventKind.PARTIAL,
            session_id=chunk.session_id,
            sequence=session.event_sequence,
            emitted_at_ms=chunk.timestamp_ms,
            text=f"fake partial {len(session.chunks)}",
        )
        session.event_sequence += 1
        return event

    def finish_input(self, session_id: str, emitted_at_ms: int) -> TranscriptEvent:
        self._require_running()
        session = self._session(session_id)
        if session.state is not SessionState.STREAMING:
            raise ProtocolError(ErrorCode.INVALID_STATE, "input-finished requires streamed PCM")
        if emitted_at_ms < session.last_timestamp_ms:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "final event precedes the last PCM chunk")
        session.state = SessionState.INPUT_FINISHED
        text = f"fake final {len(session.chunks)}"
        event = TranscriptEvent(
            kind=EventKind.FINAL,
            session_id=session_id,
            sequence=session.event_sequence,
            emitted_at_ms=emitted_at_ms,
            text=text,
            alternatives=(TranscriptAlternative(text=text, rank=1, confidence=1.0),),
        )
        session.event_sequence += 1
        session.state = SessionState.FINAL
        return event

    def reset_session(self, session_id: str) -> None:
        self._require_running()
        self._session(session_id)
        self._sessions[session_id] = _Session()

    def cancel_session(self, session_id: str, emitted_at_ms: int) -> TranscriptEvent:
        self._require_running()
        session = self._session(session_id)
        if session.state in {SessionState.FINAL, SessionState.CANCELLED}:
            raise ProtocolError(ErrorCode.INVALID_STATE, "terminal session cannot be cancelled")
        session.state = SessionState.CANCELLED
        event = TranscriptEvent(
            kind=EventKind.ERROR,
            session_id=session_id,
            sequence=session.event_sequence,
            emitted_at_ms=emitted_at_ms,
            error_code=ErrorCode.CANCELLED,
            error_message="fake session cancelled",
        )
        session.event_sequence += 1
        return event

    def shutdown(self, timeout_ms: int) -> int:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        started = monotonic()
        self._sessions.clear()
        self._model_loaded = False
        self._shutdown = True
        elapsed_ms = int((monotonic() - started) * 1000)
        if elapsed_ms > timeout_ms:
            raise ProtocolError(ErrorCode.SHUTDOWN, "fake shutdown exceeded its bound")
        return elapsed_ms

    def _require_running(self) -> None:
        if self._shutdown:
            raise ProtocolError(ErrorCode.SHUTDOWN, "runtime is shut down")

    def _session(self, session_id: str) -> _Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise ProtocolError(ErrorCode.SESSION_NOT_FOUND, session_id) from exc
