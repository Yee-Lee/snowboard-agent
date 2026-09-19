"""Frozen case accounting helpers; no target execution occurs here."""

from __future__ import annotations

from dataclasses import dataclass

from poc_llm.m4c_ss.mapping import CANDIDATES


CONTROLLER_CASES = (
    "C01-ONE",
    "C02-MULTI",
    "C03-BACKPRESSURE",
    "C04-INVALID-TERMINAL",
    "C05-PREFIX-MISMATCH",
    "C06-POST-TERMINAL",
    "C07-INTERRUPT-QUEUED",
    "C07-INTERRUPT-SYNTHESIZING",
    "C07-INTERRUPT-PLAYING",
    "C08-SHUTDOWN-SYNTHESIZING",
    "C08-SHUTDOWN-PLAYING",
    "C09-TTS-FAILURE-ERROR",
    "C09-TTS-FAILURE-TIMEOUT",
    "C09-TTS-FAILURE-FORCE-ABORT",
    "C10-LATE-OUTPUT",
)
MAPPING_TRACES = ("T01", "T02", "T03")
SELECTED_B = "SELECTED-B"
LIVE_CASES = ("L01-IDENTITY", "L02-EXPLAIN", "L03-ADVICE", "L04-END")
NEGATIVE_CASES = (
    "N01-INVALID-TERMINAL",
    "N02-PREFIX-MISMATCH",
    "N03-INTERRUPT-QUEUED",
    "N03-INTERRUPT-SYNTHESIZING",
    "N03-INTERRUPT-PLAYING",
    "N04-SHUTDOWN-QUEUED",
    "N04-SHUTDOWN-PLAYING",
    "N05-QUEUE-SATURATION",
    "N06-TTS-TIMEOUT-FORCE-ABORT",
)


@dataclass(frozen=True, slots=True)
class PlannedCase:
    partition: str
    case_id: str
    candidate: str | None = None
    repetition: int | None = None
    arm: str | None = None
    order: str | None = None


def build_plan() -> tuple[PlannedCase, ...]:
    result = [PlannedCase("controller", case_id) for case_id in CONTROLLER_CASES]
    for trace in MAPPING_TRACES:
        for repetition in range(1, 4):
            order = CANDIDATES if repetition % 2 else tuple(reversed(CANDIDATES))
            result.extend(
                PlannedCase("mapping", trace, candidate=candidate, repetition=repetition)
                for candidate in order
            )
    for case_id in LIVE_CASES:
        for repetition in range(1, 6):
            order = "A-B" if repetition % 2 else "B-A"
            for arm in order.split("-"):
                result.append(PlannedCase(
                    "live", case_id, repetition=repetition, arm=arm, order=order,
                ))
    result.extend(PlannedCase("negative", case_id, candidate=SELECTED_B) for case_id in NEGATIVE_CASES)
    plan = tuple(result)
    identifiers = [case_key(item) for item in plan]
    if len(plan) != 82 or len(set(identifiers)) != len(identifiers):
        raise RuntimeError("M4C-SS plan accounting defect")
    return plan


def case_key(item: PlannedCase) -> str:
    fields = (item.partition, item.case_id, item.candidate, item.repetition, item.arm, item.order)
    return ":".join("-" if value is None else str(value) for value in fields)
