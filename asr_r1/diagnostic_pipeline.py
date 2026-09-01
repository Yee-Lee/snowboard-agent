"""Dependency-free diagnostic VAD and second-pass scorer scaffolds for AR1M1."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from .protocol import EventKind, TranscriptAlternative, TranscriptEvent


class VadEventKind(str, Enum):
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"


@dataclass(frozen=True)
class VadObservation:
    kind: VadEventKind
    timestamp_ms: int

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")


class FakeVadEndpoint:
    """Exercise endpoint transitions using caller-supplied speech labels only."""

    def __init__(self) -> None:
        self._speech_active = False
        self._cancelled = False
        self._last_timestamp_ms = -1

    def observe(self, timestamp_ms: int, is_speech: bool) -> VadObservation | None:
        if self._cancelled:
            raise RuntimeError("fake VAD is cancelled")
        if timestamp_ms <= self._last_timestamp_ms:
            raise ValueError("VAD timestamps must be strictly increasing")
        self._last_timestamp_ms = timestamp_ms
        if is_speech and not self._speech_active:
            self._speech_active = True
            return VadObservation(VadEventKind.SPEECH_START, timestamp_ms)
        if not is_speech and self._speech_active:
            self._speech_active = False
            return VadObservation(VadEventKind.SPEECH_END, timestamp_ms)
        return None

    def reset(self) -> None:
        self._speech_active = False
        self._cancelled = False
        self._last_timestamp_ms = -1

    def cancel(self) -> None:
        self._speech_active = False
        self._cancelled = True


class DiagnosticScorer(Protocol):
    def score(self, text: str) -> float: ...


class FakeSecondPassScorer:
    """Deterministic injected scores; it is not a language or product model."""

    def __init__(self, scores: Mapping[str, float]) -> None:
        self._scores = dict(scores)

    def score(self, text: str) -> float:
        return self._scores.get(text, 0.0)


@dataclass(frozen=True)
class DiagnosticCandidate:
    input_rank: int
    text_sha256: str
    fake_score: float


@dataclass(frozen=True)
class DiagnosticScoringResult:
    candidates: tuple[DiagnosticCandidate, ...]
    recommended_input_rank: int
    top_one_fallback: bool
    confidence_available: bool
    token_timestamps_available: bool
    final_unchanged: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "formal_result": False,
            "interpretation": "DIAGNOSTIC_FAKE_SCORER_ONLY",
            "candidate_count": len(self.candidates),
            "recommended_input_rank": self.recommended_input_rank,
            "top_one_fallback": self.top_one_fallback,
            "confidence_available": self.confidence_available,
            "token_timestamps_available": self.token_timestamps_available,
            "final_unchanged": self.final_unchanged,
            "candidates": [
                {
                    "input_rank": item.input_rank,
                    "text_sha256": item.text_sha256,
                    "fake_score": item.fake_score,
                }
                for item in self.candidates
            ],
        }


def inspect_final_with_fake_scorer(
    event: TranscriptEvent,
    scorer: DiagnosticScorer,
    *,
    token_timestamps_available: bool = False,
) -> DiagnosticScoringResult:
    """Inspect a final event without changing the event or downstream transcript."""

    if event.kind is not EventKind.FINAL:
        raise ValueError("diagnostic scoring accepts final events only")
    alternatives = event.alternatives or (
        TranscriptAlternative(text=event.text or "", rank=1),
    )
    if alternatives[0].text != event.text:
        raise ValueError("rank-one alternative must match the emitted final")
    scored = tuple(
        DiagnosticCandidate(
            input_rank=item.rank,
            text_sha256=hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
            fake_score=scorer.score(item.text),
        )
        for item in alternatives
    )
    recommended = max(scored, key=lambda item: (item.fake_score, -item.input_rank))
    return DiagnosticScoringResult(
        candidates=scored,
        recommended_input_rank=recommended.input_rank,
        top_one_fallback=not event.alternatives or len(event.alternatives) == 1,
        confidence_available=all(
            item.confidence is not None for item in alternatives
        ),
        token_timestamps_available=token_timestamps_available,
    )
