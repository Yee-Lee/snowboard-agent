"""Fail-closed authorization and identity guards for formal M3 execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .m3_packet import CORE_HAL_EXECUTION_SHA, PACKET_ID, PREVIOUS_CORE_HAL_SHA, sha256_file
from .validation import GIT_SHA_RE


SIGNOFF_STATUS = "CORE_PACKET_SIGNED_OFF"
RESULT_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE"}
PUBLICATION_STATUS = "DRAFT_USER_CONFIRMATION_PENDING"
CLEANUP_KEYS = {
    "child_processes", "threads", "tasks", "iterators", "streams",
    "file_descriptors", "device_owners",
}


def load_signoff(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Core signoff must be a JSON object")
    validate_signoff_document(document)
    return document


def validate_signoff_document(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0":
        raise ValueError("unsupported Core signoff schema")
    if document.get("status") != SIGNOFF_STATUS:
        raise ValueError("formal M3 execution requires Core packet signoff")
    if document.get("packet_id") != PACKET_ID:
        raise ValueError("Core signoff packet identity mismatch")
    for field in ("poc_execution_sha", "core_execution_sha", "core_acceptance_sha"):
        value = document.get(field)
        if not isinstance(value, str) or not GIT_SHA_RE.fullmatch(value):
            raise ValueError(f"Core signoff {field} must be a full Git SHA")
    if document["core_execution_sha"] == PREVIOUS_CORE_HAL_SHA:
        raise ValueError("old Core HAL SHA lacks the required output adaptation")
    if document["core_execution_sha"] != CORE_HAL_EXECUTION_SHA:
        raise ValueError("Core signoff does not name the packet-pinned HAL SHA")
    packet_hash = document.get("packet_manifest_sha256")
    if not isinstance(packet_hash, str) or len(packet_hash) != 64:
        raise ValueError("Core signoff packet manifest SHA-256 is required")
    response_id = document.get("response_id")
    if not isinstance(response_id, str) or not response_id.strip():
        raise ValueError("Core signoff response identity is required")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_formal_authorization(
    signoff: dict[str, Any],
    packet_manifest: Path,
    poc_root: Path,
    core_root: Path,
) -> None:
    validate_signoff_document(signoff)
    if sha256_file(packet_manifest) != signoff["packet_manifest_sha256"]:
        raise ValueError("signed packet manifest checksum mismatch")
    if _git(poc_root, "rev-parse", "HEAD") != signoff["poc_execution_sha"]:
        raise ValueError("POC checkout does not match Core signoff")
    if _git(core_root, "rev-parse", "HEAD") != signoff["core_execution_sha"]:
        raise ValueError("Core checkout does not match Core signoff")
    if _git(poc_root, "status", "--porcelain"):
        raise ValueError("formal M3 requires a clean POC checkout")
    if _git(core_root, "status", "--porcelain"):
        raise ValueError("formal M3 requires a clean Core checkout")


def validate_m3_result(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0":
        raise ValueError("unsupported M3 result schema")
    if document.get("packet_id") != PACKET_ID:
        raise ValueError("M3 result packet identity mismatch")
    if document.get("publication_status") != PUBLICATION_STATUS:
        raise ValueError("new M3 result must remain pending User confirmation")
    if document.get("result") not in RESULT_STATUSES:
        raise ValueError("M3 result must be PASS, FAIL or INCONCLUSIVE")
    for field in ("poc_execution_sha", "core_execution_sha"):
        value = document.get(field)
        if not isinstance(value, str) or not GIT_SHA_RE.fullmatch(value):
            raise ValueError(f"M3 result {field} must be a full Git SHA")
    if not isinstance(document.get("test_id"), str) or not document["test_id"].startswith("M3-"):
        raise ValueError("M3 result requires a fixed test ID")
    if not isinstance(document.get("command"), list) or not document["command"]:
        raise ValueError("M3 result requires the exact argv command")
    cleanup = document.get("cleanup")
    if not isinstance(cleanup, dict) or set(cleanup) != CLEANUP_KEYS:
        raise ValueError("M3 result cleanup proof is incomplete")
    if any(not isinstance(value, int) or value < 0 for value in cleanup.values()):
        raise ValueError("M3 cleanup counters must be non-negative integers")
    if document["result"] == "PASS" and any(cleanup.values()):
        raise ValueError("PASS requires zero cleanup residue")
    controlled = document.get("controlled_evidence")
    if not isinstance(controlled, dict) or not controlled.get("locator"):
        raise ValueError("M3 result requires a controlled evidence locator")
    if not isinstance(controlled.get("sha256"), str) or len(controlled["sha256"]) != 64:
        raise ValueError("M3 controlled evidence SHA-256 is required")
