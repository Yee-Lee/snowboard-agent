"""Dependency-free AR1M0 streaming and lifecycle protocol types."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class EventKind(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"
    ERROR = "error"


class ErrorCode(str, Enum):
    INVALID_STATE = "invalid_state"
    INVALID_CHUNK = "invalid_chunk"
    OUT_OF_ORDER = "out_of_order"
    SESSION_NOT_FOUND = "session_not_found"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


class SessionState(str, Enum):
    OPEN = "open"
    STREAMING = "streaming"
    INPUT_FINISHED = "input_finished"
    FINAL = "final"
    CANCELLED = "cancelled"
    ERROR = "error"


class LifecycleOperation(str, Enum):
    MODEL_LOAD = "model_load"
    SESSION_CREATE = "session_create"
    SESSION_RESET = "session_reset"
    INPUT_FINISHED = "input_finished"
    CANCEL = "cancel"
    SHUTDOWN = "shutdown"


class ProtocolError(RuntimeError):
    """Protocol failure with a stable machine-readable error code."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _non_empty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


@dataclass(frozen=True)
class LifecycleCommand:
    operation: LifecycleOperation
    request_id: str
    session_id: str | None = None
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        _non_empty(self.request_id, "request_id")
        needs_session = self.operation in {
            LifecycleOperation.SESSION_RESET,
            LifecycleOperation.INPUT_FINISHED,
            LifecycleOperation.CANCEL,
        }
        if needs_session and not self.session_id:
            raise ValueError(f"{self.operation.value} requires session_id")
        if self.operation is LifecycleOperation.SHUTDOWN and self.timeout_ms is None:
            raise ValueError("shutdown requires timeout_ms")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "operation": self.operation.value,
            "request_id": self.request_id,
        }
        if self.session_id is not None:
            result["session_id"] = self.session_id
        if self.timeout_ms is not None:
            result["timeout_ms"] = self.timeout_ms
        return result


@dataclass(frozen=True)
class PCMChunk:
    session_id: str
    sequence: int
    timestamp_ms: int
    samples_s16le: bytes
    sample_rate_hz: int = 16_000

    def __post_init__(self) -> None:
        _non_empty(self.session_id, "session_id")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if self.sample_rate_hz != 16_000:
            raise ValueError("AR1 PCM must be 16000 Hz")
        if not self.samples_s16le or len(self.samples_s16le) % 2:
            raise ValueError("samples_s16le must contain whole, non-empty S16_LE samples")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "session_id": self.session_id,
            "sequence": self.sequence,
            "timestamp_ms": self.timestamp_ms,
            "sample_rate_hz": self.sample_rate_hz,
            "encoding": "PCM_S16_LE_MONO",
            "samples_base64": base64.b64encode(self.samples_s16le).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PCMChunk":
        if payload.get("schema_version") != "1.0":
            raise ValueError("unsupported PCM-chunk schema_version")
        if payload.get("encoding") != "PCM_S16_LE_MONO":
            raise ValueError("unsupported PCM encoding")
        try:
            samples = base64.b64decode(payload["samples_base64"], validate=True)
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid samples_base64") from exc
        return cls(
            session_id=payload["session_id"],
            sequence=payload["sequence"],
            timestamp_ms=payload["timestamp_ms"],
            sample_rate_hz=payload["sample_rate_hz"],
            samples_s16le=samples,
        )


@dataclass(frozen=True)
class TranscriptAlternative:
    text: str
    rank: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        _non_empty(self.text, "alternative text")
        if self.rank < 1:
            raise ValueError("alternative rank must start at one")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between zero and one")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"text": self.text, "rank": self.rank}
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result


@dataclass(frozen=True)
class TranscriptEvent:
    kind: EventKind
    session_id: str
    sequence: int
    emitted_at_ms: int
    text: str | None = None
    alternatives: tuple[TranscriptAlternative, ...] = ()
    error_code: ErrorCode | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.session_id, "session_id")
        if self.sequence < 0 or self.emitted_at_ms < 0:
            raise ValueError("event sequence and emitted_at_ms must be non-negative")
        if self.kind in {EventKind.PARTIAL, EventKind.FINAL}:
            _non_empty(self.text or "", "transcript text")
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("transcript events cannot contain error fields")
        if self.kind is EventKind.ERROR:
            if self.text is not None or self.alternatives:
                raise ValueError("error events cannot contain transcript fields")
            if self.error_code is None:
                raise ValueError("error events require error_code")
            _non_empty(self.error_message or "", "error_message")
        ranks = [item.rank for item in self.alternatives]
        if ranks and ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("alternative ranks must be contiguous and ordered")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "kind": self.kind.value,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "emitted_at_ms": self.emitted_at_ms,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.alternatives:
            result["alternatives"] = [item.to_dict() for item in self.alternatives]
        if self.error_code is not None:
            result["error"] = {
                "code": self.error_code.value,
                "message": self.error_message,
            }
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TranscriptEvent":
        if payload.get("schema_version") != "1.0":
            raise ValueError("unsupported transcript-event schema_version")
        alternatives = tuple(
            TranscriptAlternative(
                text=item["text"],
                rank=item["rank"],
                confidence=item.get("confidence"),
            )
            for item in payload.get("alternatives", [])
        )
        error = payload.get("error")
        return cls(
            kind=EventKind(payload["kind"]),
            session_id=payload["session_id"],
            sequence=payload["sequence"],
            emitted_at_ms=payload["emitted_at_ms"],
            text=payload.get("text"),
            alternatives=alternatives,
            error_code=ErrorCode(error["code"]) if error else None,
            error_message=error["message"] if error else None,
        )


def final_text_for_downstream(event: TranscriptEvent) -> str | None:
    """Expose only final text to downstream product logic."""

    return event.text if event.kind is EventKind.FINAL else None
