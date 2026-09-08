"""Frozen-order and descriptive-analysis helpers for efficiency execution."""

from __future__ import annotations

import math
import statistics
from typing import Iterable


ENCODING_ORDER = tuple(f"A-{encoding}{pair}" for pair in range(1, 6) for encoding in ("J", "P"))
READINESS_ORDER = tuple(f"B-{mode}{pair}" for pair in range(1, 6) for mode in ("D", "H"))
FUNCTIONAL_ORDER = ("F-NO-REQUEST", "F-CANCEL-OPEN", "F-END-NEW", "F-IDENTITY-MISMATCH")
FULL_ORDER = ENCODING_ORDER + READINESS_ORDER + FUNCTIONAL_ORDER


class PlanError(ValueError):
    pass


def verify_next_case(entries: list[dict[str, object]], case_id: str) -> None:
    """Enforce append-only exact order and forbid retry/backfill."""

    if len(entries) >= len(FULL_ORDER) or case_id != FULL_ORDER[len(entries)]:
        raise PlanError("case order or no-retry ledger violation")
    seen = []
    for index, entry in enumerate(entries):
        if entry.get("case_id") != FULL_ORDER[index]:
            raise PlanError("ledger order drift")
        if entry.get("case_id") in seen:
            raise PlanError("duplicate case in no-retry ledger")
        seen.append(entry.get("case_id"))


def _finite(values: Iterable[float | int]) -> list[float]:
    result = [float(value) for value in values]
    if not result or any(not math.isfinite(value) for value in result):
        raise PlanError("analysis requires finite nonempty values")
    return result


def descriptive(values: Iterable[float | int]) -> dict[str, float | int]:
    """Return only the approved small-sample descriptive statistics."""

    samples = _finite(values)
    return {
        "count": len(samples),
        "median": statistics.median(samples),
        "minimum": min(samples),
        "maximum": max(samples),
    }


def paired_deltas(
    rows: Iterable[dict[str, object]], *, left: str, right: str, metric: str,
) -> dict[str, object]:
    """Compute right-minus-left deltas for exactly five fixed pairs."""

    indexed: dict[tuple[int, str], float] = {}
    for row in rows:
        pair = row.get("pair")
        variant = row.get("variant")
        metrics = row.get("metrics")
        if (not isinstance(pair, int) or isinstance(pair, bool) or pair not in range(1, 6)
                or variant not in {left, right} or not isinstance(metrics, dict)
                or not isinstance(metrics.get(metric), (int, float))
                or isinstance(metrics.get(metric), bool)):
            raise PlanError("paired input is incomplete or invalid")
        key = (pair, str(variant))
        if key in indexed:
            raise PlanError("duplicate paired sample")
        indexed[key] = float(metrics[metric])
    expected = {(pair, variant) for pair in range(1, 6) for variant in (left, right)}
    if set(indexed) != expected:
        raise PlanError("paired input is incomplete or invalid")
    deltas = [{"pair": pair, "delta": indexed[(pair, right)] - indexed[(pair, left)]}
              for pair in range(1, 6)]
    return {"direction": f"{right}_minus_{left}", "pairs": deltas,
            "summary": descriptive(item["delta"] for item in deltas)}
