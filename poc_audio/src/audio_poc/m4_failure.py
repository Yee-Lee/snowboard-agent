"""Fail-closed result contract for the twelve M4 failure/recovery cases.

This module deliberately validates *evidence descriptions*, not just supervisor
return codes.  A formal runner may only report a row as passing once its named
finalist (or the explicitly permitted force-abort double) reached the expected
terminal state, cleanup was measured, and the same finalist was reopened for a
successful recovery probe.
"""

from __future__ import annotations

from typing import Any

from .m4_authorization import CLEANUP_KEYS
from .m4_packet import CORE_HAL_SHA, FAILURE_ROWS, PACKET_ID, PUBLICATION_STATUS
from .validation import GIT_SHA_RE, SHA256_RE


FAILURE_TEST_ID = "M4-FAILURE-INJECTION-RECOVERY-001"
TERMINALS = {
    "error": "ERROR",
    "timeout": "TIMEOUT",
    "cancel": "CANCELLED",
    "force_abort": "FORCE_ABORTED",
}
ACTUAL_FINALIST_SCENARIOS = {"error", "timeout", "cancel"}
FORCE_ABORT_SOURCE = "CONTROLLED_FORCE_ABORT_DOUBLE"


def validate_failure_bundle(document: dict[str, Any]) -> None:
    """Validate the exact catalog and proof needed for an M4 formal run."""
    required = {
        "schema_version", "packet_id", "test_id", "publication_status",
        "audio_execution_sha", "core_execution_sha", "controlled_evidence",
        "cases", "cleanup", "proposed_disposition", "decision_boundary",
    }
    if set(document) != required:
        raise ValueError("M4 failure bundle fields are incomplete or unexpected")
    if document["schema_version"] != "1.0" or document["packet_id"] != PACKET_ID:
        raise ValueError("M4 failure bundle identity is invalid")
    if document["test_id"] != FAILURE_TEST_ID:
        raise ValueError("M4 failure bundle test ID is invalid")
    if document["publication_status"] != PUBLICATION_STATUS:
        raise ValueError("M4 failure bundle must remain pending User confirmation")
    if not GIT_SHA_RE.fullmatch(str(document["audio_execution_sha"])):
        raise ValueError("M4 failure bundle Audio SHA is invalid")
    if document["core_execution_sha"] != CORE_HAL_SHA:
        raise ValueError("M4 failure bundle Core SHA is invalid")
    _validate_evidence(document["controlled_evidence"])
    cases = document["cases"]
    if not isinstance(cases, list) or [
        (item.get("test_id"), item.get("domain"), item.get("scenario"))
        for item in cases if isinstance(item, dict)
    ] != list(FAILURE_ROWS):
        raise ValueError("M4 failure bundle catalog/order mismatch")
    if len(cases) != len(FAILURE_ROWS):
        raise ValueError("M4 failure bundle requires all twelve cases")
    for case in cases:
        _validate_case(case)
    _validate_cleanup(document["cleanup"], "M4 failure bundle")
    if document["proposed_disposition"] not in {"PASS", "FAIL", "INCONCLUSIVE"}:
        raise ValueError("M4 failure bundle disposition is invalid")
    if document["proposed_disposition"] == "PASS":
        if any(document["cleanup"].values()) or any(_case_has_residue(item) for item in cases):
            raise ValueError("M4 failure PASS requires zero cleanup residue for every case")
    if not isinstance(document["decision_boundary"], str) or "User confirmation" not in document["decision_boundary"]:
        raise ValueError("M4 failure bundle decision boundary is incomplete")


def _validate_case(case: object) -> None:
    required = {
        "test_id", "domain", "scenario", "terminal_status", "injection_source",
        "injection_observed", "duration_ms", "force_abort_used", "cleanup", "recovery",
    }
    if not isinstance(case, dict) or set(case) != required:
        raise ValueError("M4 failure case fields are incomplete or unexpected")
    scenario = case["scenario"]
    if case["terminal_status"] != TERMINALS.get(scenario):
        raise ValueError(f"M4 failure terminal mismatch: {case.get('test_id')}")
    expected_source = FORCE_ABORT_SOURCE if scenario == "force_abort" else "ACTUAL_FINALIST"
    if case["injection_source"] != expected_source:
        raise ValueError(f"M4 failure injection source mismatch: {case.get('test_id')}")
    if case["injection_observed"] is not True:
        raise ValueError(f"M4 failure injection was not observed: {case.get('test_id')}")
    if not isinstance(case["duration_ms"], (int, float)) or case["duration_ms"] < 0:
        raise ValueError(f"M4 failure duration is invalid: {case.get('test_id')}")
    if not isinstance(case["force_abort_used"], bool) or case["force_abort_used"] != (scenario == "force_abort"):
        raise ValueError(f"M4 failure force-abort proof mismatch: {case.get('test_id')}")
    _validate_cleanup(case["cleanup"], "M4 failure case")
    recovery = case["recovery"]
    if not isinstance(recovery, dict) or set(recovery) != {"attempted", "terminal_status", "same_finalist", "cleanup"}:
        raise ValueError(f"M4 failure recovery proof is invalid: {case.get('test_id')}")
    if recovery["attempted"] is not True or recovery["terminal_status"] != "SUCCESS" or recovery["same_finalist"] is not True:
        raise ValueError(f"M4 failure recovery did not prove finalist reopen: {case.get('test_id')}")
    _validate_cleanup(recovery["cleanup"], "M4 failure recovery")


def _validate_cleanup(value: object, label: str) -> None:
    if not isinstance(value, dict) or set(value) != CLEANUP_KEYS or any(
        not isinstance(count, int) or count < 0 for count in value.values()
    ):
        raise ValueError(f"{label} cleanup proof is invalid")


def _case_has_residue(case: dict[str, Any]) -> bool:
    return any(case["cleanup"].values()) or any(case["recovery"]["cleanup"].values())


def _validate_evidence(value: object) -> None:
    if (
        not isinstance(value, dict) or set(value) != {"locator", "sha256"}
        or not isinstance(value["locator"], str) or not value["locator"].startswith("controlled://")
        or not SHA256_RE.fullmatch(str(value["sha256"]))
    ):
        raise ValueError("M4 failure controlled evidence identity is invalid")
