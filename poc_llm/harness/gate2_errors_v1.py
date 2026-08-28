"""Typed, sanitized result semantics shared by the Gate 2 runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Gate2Error(RuntimeError):
    """Base class whose name is safe to persist as evidence."""


class CandidateViolation(Gate2Error):
    """A mandatory candidate behavior was validly observed to be false."""


class EnvironmentInvalid(Gate2Error):
    """The target environment or a runtime probe invalidated the observation."""


class EvidenceInvalid(Gate2Error):
    """Required evidence could not be collected, validated, or written."""


class PacketDefect(Gate2Error):
    """The frozen method or packet cannot produce an adjudicable observation."""


class CleanupViolation(Gate2Error):
    """A POC-owned process or device remained after bounded cleanup."""


FAIL_ERRORS = (CandidateViolation, CleanupViolation)


def error_result(error: BaseException) -> str:
    """Return FAIL only for an observed candidate/cleanup rule violation."""

    return "FAIL" if isinstance(error, FAIL_ERRORS) else "INCONCLUSIVE"


def sanitized_error(error: BaseException) -> dict[str, Any]:
    """Persist only the controlled category and concrete exception type."""

    category = type(error).__name__ if isinstance(error, Gate2Error) else "EnvironmentInvalid"
    cause = error.__cause__
    return {
        "category": category,
        "error_type": type(cause).__name__ if cause is not None else type(error).__name__,
    }


def write_json_evidence(path: Path, value: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    except OSError as error:
        raise EvidenceInvalid("sanitized evidence write failed") from error
