"""Current exact-SHA evidence reconciliation; historical POC rows cannot satisfy it."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts.m4b_target_metrics import PORTABLE_IDS, TARGET_IDS


class InheritanceError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("M4B_EVIDENCE_INVALID")


RESULT_FIELDS = frozenset({"schema_version", "test_id", "case_id", "candidate_sha", "profile_id",
    "profile_sha256", "matrix", "platform", "python", "start_monotonic_ns", "end_monotonic_ns",
    "status", "evidence_sha256"})


def validate_result_record(value: object, *, candidate_sha: str, profile_sha256: str) -> dict:
    """Validate metadata only; callers must inspect and authenticate the actual evidence."""
    if (type(value) is not dict or set(value) != RESULT_FIELDS
            or value["schema_version"] != 1 or type(value["schema_version"]) is not int
            or value["test_id"] not in PORTABLE_IDS | TARGET_IDS
            or value["candidate_sha"] != candidate_sha or value["profile_sha256"] != profile_sha256
            or value["profile_id"] != "core-m4b-cognition-001"
            or re.fullmatch(r"[0-9a-f]{40}", candidate_sha) is None
            or re.fullmatch(r"[0-9a-f]{64}", profile_sha256) is None
            or type(value["case_id"]) is not str
            or re.fullmatch(r"[A-Z][0-9]{2}", value["case_id"]) is None
            or value["status"] not in {"Pass", "Fail", "Blocked", "Incomplete", "Pending"}
            or any(type(value[k]) is not int or value[k] < 0
                   for k in ("start_monotonic_ns", "end_monotonic_ns"))
            or value["end_monotonic_ns"] < value["start_monotonic_ns"]
            or type(value["evidence_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value["evidence_sha256"]) is None):
        raise InheritanceError()
    target = value["test_id"] in TARGET_IDS
    if target:
        if (value["matrix"] not in {"PM", "PR", "PH"}
                or value["platform"] != "pi5-4gb-debian13-aarch64"
                or value["python"] != "3.13.5"):
            raise InheritanceError()
    elif (value["matrix"] not in {"PU", "PI", "PS"}
            or value["platform"] not in {"linux", "darwin", "win32"}
            or type(value["python"]) is not str
            or re.fullmatch(r"3\.(11|12|13)\.[0-9]+", value["python"]) is None
            or (value["matrix"] == "PS" and
                (value["platform"] != "linux" or not value["python"].startswith("3.13.")))):
        raise InheritanceError()
    return dict(value)


def validate_rows(rows: object, candidate_sha: str, *, profile_sha256: str, resolver,
                  required_ids=PORTABLE_IDS | TARGET_IDS) -> list[dict]:
    if type(rows) is not list or not rows or not set(required_ids).issubset(PORTABLE_IDS | TARGET_IDS):
        raise InheritanceError()
    result, identities = [], set()
    for row in rows:
        if type(row) is not dict or set(row) != {"record", "evidence_locator"}:
            raise InheritanceError()
        record = validate_result_record(row["record"], candidate_sha=candidate_sha,
                                        profile_sha256=profile_sha256)
        identity = (record["test_id"], record["case_id"], record["matrix"], record["platform"], record["python"])
        locator = row["evidence_locator"]
        if (identity in identities or record["status"] != "Pass" or type(locator) is not str
                or re.fullmatch(r"sha256/[0-9a-f]{64}", locator) is None):
            raise InheritanceError()
        try:
            raw = resolver(locator)
        except Exception:
            raise InheritanceError() from None
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != record["evidence_sha256"]:
            raise InheritanceError()
        if locator != f"sha256/{record['evidence_sha256']}":
            raise InheritanceError()
        identities.add(identity)
        result.append(record)
    if not set(required_ids).issubset({r["test_id"] for r in result}):
        raise InheritanceError()
    return result
