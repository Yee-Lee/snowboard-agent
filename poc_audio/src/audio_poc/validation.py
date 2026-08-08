"""Dependency-free validation for tracked M1 JSON documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .models import TerminalStatus


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_run_result(document: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "source_sha",
        "candidate_id",
        "candidate_kind",
        "scenario",
        "started_at_utc",
        "duration_ms",
        "terminal_status",
        "worker_exit_code",
        "error_code",
        "force_abort_used",
        "cleanup",
    }
    _require_keys(document, required, "result")
    if not GIT_SHA_RE.fullmatch(str(document["source_sha"])):
        raise ValueError("result source_sha must be a full Git SHA")
    if document["terminal_status"] not in {status.value for status in TerminalStatus}:
        raise ValueError("result terminal_status is invalid")
    cleanup = document["cleanup"]
    _require_keys(
        cleanup,
        {"child_processes", "threads", "iterators", "streams", "device_owners", "clean"},
        "cleanup",
    )
    if cleanup["clean"] != all(
        cleanup[name] == 0
        for name in ("child_processes", "threads", "iterators", "streams", "device_owners")
    ):
        raise ValueError("cleanup clean flag disagrees with cleanup counts")


def validate_candidate_manifest(document: dict[str, Any], repo_root: Path) -> None:
    _require_keys(
        document,
        {
            "schema_version",
            "candidate_id",
            "kind",
            "engine",
            "engine_version",
            "artifact",
            "artifact_sha256",
            "license",
            "offline",
            "entrypoint",
            "parameters",
        },
        "candidate manifest",
    )
    _validate_tracked_checksum(
        repo_root / str(document["artifact"]), str(document["artifact_sha256"])
    )


def validate_fixture_catalog(document: dict[str, Any], repo_root: Path) -> None:
    _require_keys(document, {"schema_version", "fixtures"}, "fixture catalog")
    fixtures = document["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixture catalog must contain fixtures")
    fixture_ids: set[str] = set()
    for fixture in fixtures:
        _require_keys(
            fixture,
            {"fixture_id", "kind", "path", "sha256", "source", "license", "sensitivity"},
            "fixture",
        )
        fixture_id = str(fixture["fixture_id"])
        if fixture_id in fixture_ids:
            raise ValueError(f"duplicate fixture_id: {fixture_id}")
        fixture_ids.add(fixture_id)
        _validate_tracked_checksum(repo_root / str(fixture["path"]), str(fixture["sha256"]))


def _validate_tracked_checksum(path: Path, expected: str) -> None:
    if not SHA256_RE.fullmatch(expected):
        raise ValueError(f"invalid SHA-256 for {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path}")


def _require_keys(document: Any, required: set[str], label: str) -> None:
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be an object")
    missing = sorted(required - set(document))
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")
