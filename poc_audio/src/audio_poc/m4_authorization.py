"""Fail-closed identity guards for the formal M4 Pi candidate runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .m3_packet import sha256_file
from .m4_packet import CORE_HAL_SHA, PACKET_ID, PUBLICATION_STATUS
from .validation import GIT_SHA_RE, SHA256_RE


AUTHORIZATION_STATUS = "M4_FORMAL_EXECUTION_AUTHORIZED"
RESULT_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE"}
CLEANUP_KEYS = {
    "child_processes", "threads", "tasks", "iterators", "streams",
    "file_descriptors", "device_owners",
}


def load_authorization(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("M4 formal authorization document is unavailable")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("M4 formal authorization must be a JSON object")
    validate_authorization_document(document)
    return document


def validate_authorization_document(document: dict[str, Any]) -> None:
    required = {
        "schema_version", "status", "packet_id", "audio_execution_sha",
        "core_execution_sha", "packet_manifest_sha256", "user_authorization_id",
        "p9_1_execution_authorized",
    }
    if set(document) != required:
        raise ValueError("M4 formal authorization fields are incomplete or unexpected")
    if document["schema_version"] != "1.0" or document["status"] != AUTHORIZATION_STATUS:
        raise ValueError("M4 formal authorization status is invalid")
    if document["packet_id"] != PACKET_ID:
        raise ValueError("M4 formal authorization packet identity mismatch")
    if not GIT_SHA_RE.fullmatch(document["audio_execution_sha"]):
        raise ValueError("M4 formal authorization Audio SHA is invalid")
    if document["core_execution_sha"] != CORE_HAL_SHA:
        raise ValueError("M4 formal authorization Core HAL SHA mismatch")
    if not SHA256_RE.fullmatch(document["packet_manifest_sha256"]):
        raise ValueError("M4 formal authorization packet checksum is invalid")
    if not isinstance(document["user_authorization_id"], str) or not document["user_authorization_id"].strip():
        raise ValueError("M4 formal authorization User authorization ID is required")
    if document["p9_1_execution_authorized"] is not True:
        raise ValueError("M4 formal authorization must explicitly authorize P9.1 execution")


def validate_formal_authorization(
    authorization: dict[str, Any],
    packet_path: Path,
    poc_root: Path,
    core_root: Path,
) -> None:
    validate_authorization_document(authorization)
    if sha256_file(packet_path) != authorization["packet_manifest_sha256"]:
        raise ValueError("M4 formal authorization packet checksum mismatch")
    if _git(poc_root, "rev-parse", "HEAD") != authorization["audio_execution_sha"]:
        raise ValueError("M4 formal POC checkout does not match the authorized SHA")
    if _git(core_root, "rev-parse", "HEAD") != authorization["core_execution_sha"]:
        raise ValueError("M4 formal Core checkout does not match the authorized SHA")
    if _git(poc_root, "status", "--porcelain"):
        raise ValueError("M4 formal execution requires a clean POC checkout")
    if _git(core_root, "status", "--porcelain"):
        raise ValueError("M4 formal execution requires a clean Core checkout")


def validate_formal_result(document: dict[str, Any]) -> None:
    required = {
        "schema_version", "packet_id", "test_id", "publication_status", "result",
        "audio_execution_sha", "core_execution_sha", "command", "cleanup",
        "controlled_evidence", "details",
    }
    if set(document) != required:
        raise ValueError("M4 formal result fields are incomplete or unexpected")
    if document["schema_version"] != "1.0" or document["packet_id"] != PACKET_ID:
        raise ValueError("M4 formal result identity is invalid")
    if not isinstance(document["test_id"], str) or not document["test_id"].startswith("M4-"):
        raise ValueError("M4 formal result requires a fixed M4 test ID")
    if document["publication_status"] != PUBLICATION_STATUS:
        raise ValueError("M4 formal result must remain pending User confirmation")
    if document["result"] not in RESULT_STATUSES:
        raise ValueError("M4 formal result disposition is invalid")
    if not GIT_SHA_RE.fullmatch(document["audio_execution_sha"]):
        raise ValueError("M4 formal result Audio SHA is invalid")
    if document["core_execution_sha"] != CORE_HAL_SHA:
        raise ValueError("M4 formal result Core SHA is invalid")
    if not isinstance(document["command"], list) or not document["command"]:
        raise ValueError("M4 formal result command is required")
    cleanup = document["cleanup"]
    if not isinstance(cleanup, dict) or set(cleanup) != CLEANUP_KEYS or any(
        not isinstance(value, int) or value < 0 for value in cleanup.values()
    ):
        raise ValueError("M4 formal result cleanup proof is invalid")
    if document["result"] == "PASS" and any(cleanup.values()):
        raise ValueError("M4 formal PASS requires zero cleanup residue")
    evidence = document["controlled_evidence"]
    if (
        not isinstance(evidence, dict) or set(evidence) != {"locator", "sha256"}
        or not isinstance(evidence["locator"], str) or not evidence["locator"].startswith("controlled://")
        or not SHA256_RE.fullmatch(str(evidence["sha256"]))
    ):
        raise ValueError("M4 formal result controlled evidence identity is invalid")
    if not isinstance(document["details"], dict):
        raise ValueError("M4 formal result details must be an object")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()
