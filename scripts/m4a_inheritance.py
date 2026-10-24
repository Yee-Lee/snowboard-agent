#!/usr/bin/env python3
"""Validate and create the Tester-owned M4a POC inheritance index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


ACCEPTED_AUDIO_SHA = "5694ead4ba6be928fdb4dbdf6da7155b214d72bd"
DELIVERY_ID = "POC-audio-DEL-2026-001-R1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_LOCATOR = re.compile(r"^(?P<repo>.+)@(?P<sha>[0-9a-f]{40}):(?P<path>[^:].+)$")
TEST_IDS = {
    "M4A-CFG-001", "M4A-LOCK-001", "M4A-IPC-001", "M4A-ASR-001",
    "M4A-ASR-002", "M4A-ASR-003", "M4A-TTS-001", "M4A-TTS-002",
    "M4A-PRIV-001", "M4A-OFF-001", "M4A-RES-001", "M4A-PKG-001",
    "M4A-INH-001",
}
REQUIRED_AREAS = {
    "candidate_provenance", *(f"P{index}" for index in range(1, 13)),
    "audio_internal_20_session", "audio_internal_failure",
    "audio_internal_offline",
}
ROW_FIELDS = {
    "area", "poc_delivery_id", "accepted_audio_sha", "poc_locator",
    "poc_sha256", "classification", "inheritance_reason", "product_sha",
    "delta_test_id", "delta_result", "result_locator",
}


class InheritanceError(RuntimeError):
    """The proposed inheritance index is incomplete or unprovable."""


def resolve_locator(locator: str) -> bytes:
    """Resolve immutable Git content or an explicit local file."""
    match = GIT_LOCATOR.fullmatch(locator)
    if match:
        repo = Path(match.group("repo")).resolve()
        if not repo.is_dir():
            raise InheritanceError("Git locator repository is missing")
        completed = subprocess.run(
            ["git", "-C", str(repo), "show", f"{match.group('sha')}:{match.group('path')}"],
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            raise InheritanceError("Git locator content cannot be resolved")
        return completed.stdout
    path = Path(locator)
    if not path.is_file() or path.is_symlink() or not path.stat().st_mode & 0o444:
        raise InheritanceError("local locator is missing, unreadable, or not a regular file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise InheritanceError("local locator cannot be read") from error


def _resolved(locator: Any, resolver: Callable[[str], bytes], label: str) -> bytes:
    if not isinstance(locator, str) or not locator:
        raise InheritanceError(f"{label} must be a non-empty locator")
    try:
        content = resolver(locator)
    except (OSError, subprocess.SubprocessError, KeyError) as error:
        raise InheritanceError(f"{label} cannot be resolved") from error
    if not isinstance(content, bytes):
        raise InheritanceError(f"{label} resolver must return bytes")
    return content


def validate_rows(
    rows: Any,
    candidate_sha: str,
    *,
    resolver: Callable[[str], bytes] = resolve_locator,
) -> list[dict[str, str]]:
    if not SHA40.fullmatch(candidate_sha):
        raise InheritanceError("candidate SHA must be externally supplied 40-hex")
    if not isinstance(rows, list) or not rows:
        raise InheritanceError("inheritance input must be a non-empty array")
    validated: list[dict[str, str]] = []
    areas: set[str] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict) or set(raw) != ROW_FIELDS:
            raise InheritanceError(f"row {index} has missing or extra fields")
        if any(not isinstance(raw[field], str) for field in ROW_FIELDS):
            raise InheritanceError(f"row {index} fields must be strings")
        row = dict(raw)
        if not row["area"] or row["area"] in areas:
            raise InheritanceError("areas must be non-empty and unique")
        areas.add(row["area"])
        if row["poc_delivery_id"] != DELIVERY_ID:
            raise InheritanceError("POC delivery identity mismatch")
        if row["accepted_audio_sha"] != ACCEPTED_AUDIO_SHA:
            raise InheritanceError("Accepted Audio SHA mismatch")
        if row["product_sha"] != candidate_sha:
            raise InheritanceError("mixed or unexpected product SHA")
        if row["delta_test_id"] not in TEST_IDS:
            raise InheritanceError("unknown delta Test ID")
        if row["delta_result"] not in {"PASS", "FAIL", "BLOCKED"}:
            raise InheritanceError("invalid delta result")
        if not row["classification"]:
            raise InheritanceError("classification must be non-empty")
        reason = row["inheritance_reason"].strip()
        if not reason or reason in {"沿用POC", "沿用 POC"}:
            raise InheritanceError("inheritance reason must state a concrete delta")
        poc = _resolved(row["poc_locator"], resolver, "POC locator")
        if not SHA256.fullmatch(row["poc_sha256"]):
            raise InheritanceError("POC checksum must be lowercase SHA-256")
        if hashlib.sha256(poc).hexdigest() != row["poc_sha256"]:
            raise InheritanceError("POC locator checksum mismatch")
        if row["delta_result"] == "PASS":
            result_bytes = _resolved(row["result_locator"], resolver, "result locator")
            try:
                result = json.loads(result_bytes)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InheritanceError("result locator is not JSON") from error
            if not isinstance(result, dict) or (
                result.get("candidate_sha") != candidate_sha
                or result.get("test_id") != row["delta_test_id"]
                or result.get("status") != "Pass"
            ):
                raise InheritanceError("result locator identity or status mismatch")
        validated.append(row)
    missing = REQUIRED_AREAS - areas
    if missing:
        raise InheritanceError("required inheritance areas are missing: " + ", ".join(sorted(missing)))
    return validated


def generate(input_path: Path, output: Path, candidate_sha: str) -> None:
    if output.exists():
        raise InheritanceError("output must be a new path")
    try:
        rows = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InheritanceError("input is unreadable or invalid JSON") from error
    validated = validate_rows(rows, candidate_sha)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        generate(args.input, args.output, args.candidate_sha)
    except InheritanceError as error:
        print(json.dumps({"status": "Fail", "error_code": type(error).__name__}))
        return 2
    print(json.dumps({"status": "Pass", "row_count": len(json.loads(args.output.read_text()))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
