"""Prepare and validate M1 P4 Option A evidence packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DELIVERY_ID = "DELIVERY-AUDIO-POC-M3-VALIDATION-001"
P4_TEST_IDS = tuple(f"P4-A{index:02d}" for index in range(1, 11))
P4_STATUSES = {"Pending", "Blocked", "INCONCLUSIVE", "PASS", "FAIL"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ("git", "-C", str(root), *args),
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def relative_artifact(root: Path, path: Path) -> dict[str, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"artifact must be inside repository: {path}") from error
    return {"path": relative, "sha256": sha256_file(resolved)}


def resolve_repo_artifact(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"artifact path must be repository-relative: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"artifact path escapes repository: {value}") from error
    return resolved


def pending_cleanup() -> dict[str, int | bool | None]:
    return {
        "tasks": None,
        "threads": None,
        "file_descriptors": None,
        "alsa_owners": None,
        "clean": None,
    }


def create_manifest(
    root: Path,
    source_sha: str,
    packet_id: str,
    config_path: Path,
) -> dict[str, Any]:
    runner_path = Path(__file__)
    conversion_runner_path = root / "poc_audio/src/audio_poc/run_option_a_conversion.py"
    live_runner_path = root / "poc_audio/src/audio_poc/option_a_live.py"
    valid_bits_runner_path = root / "poc_audio/src/audio_poc/option_a_valid_bits.py"
    fixture_path = root / "poc_audio/src/audio_poc/option_a_fixtures.py"
    provenance_path = root / "poc_audio/manifests/option_a_candidates.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0",
        "delivery_id": DELIVERY_ID,
        "test_packet_id": packet_id,
        "poc_source_sha": source_sha,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "ended_at_utc": None,
        "hardware": {
            "platform": "Raspberry Pi 5",
            "microphone": "INMP441",
            "speaker": "MAX98357A",
            "soundcard": "googlevoicehat-soundcard",
            "environment_evidence": "pending",
        },
        "wiring": {"attestation": "pending-p4-a02"},
        "sanitized_config": relative_artifact(root, config_path),
        "runner": relative_artifact(root, runner_path),
        "conversion_runner": relative_artifact(root, conversion_runner_path),
        "live_runner": relative_artifact(root, live_runner_path),
        "valid_bits_runner": relative_artifact(root, valid_bits_runner_path),
        "fixture_generator": relative_artifact(root, fixture_path),
        "candidate_provenance": relative_artifact(root, provenance_path),
        "candidates": provenance["candidates"],
        "tests": [
            {
                "test_id": test_id,
                "status": "Pending",
                "command": None,
                "raw_artifact_paths": [],
                "cleanup": pending_cleanup(),
            }
            for test_id in P4_TEST_IDS
        ],
        "reproduction_command": "bash poc_audio/tools/run_option_a_validation.sh prepare",
    }


def validate_manifest(document: dict[str, Any], root: Path) -> None:
    required = {
        "schema_version", "delivery_id", "test_packet_id", "poc_source_sha",
        "started_at_utc", "ended_at_utc", "hardware", "wiring",
        "sanitized_config", "runner", "conversion_runner", "live_runner", "valid_bits_runner", "fixture_generator", "candidate_provenance", "candidates",
        "tests", "reproduction_command",
    }
    missing = sorted(required - set(document))
    if missing:
        raise ValueError(f"Option A manifest missing keys: {', '.join(missing)}")
    if document["schema_version"] != "1.0" or document["delivery_id"] != DELIVERY_ID:
        raise ValueError("Option A manifest identity is invalid")
    source_sha = str(document["poc_source_sha"])
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise ValueError("poc_source_sha must be a full lowercase Git SHA")

    tests = document["tests"]
    if not isinstance(tests, list) or [item.get("test_id") for item in tests] != list(P4_TEST_IDS):
        raise ValueError("tests must contain ordered P4-A01 through P4-A10 entries")
    for item in tests:
        if item.get("status") not in P4_STATUSES:
            raise ValueError(f"invalid status for {item.get('test_id')}")
        cleanup = item.get("cleanup")
        if not isinstance(cleanup, dict):
            raise ValueError(f"cleanup missing for {item.get('test_id')}")
        counts = [cleanup.get(name) for name in ("tasks", "threads", "file_descriptors", "alsa_owners")]
        if cleanup.get("clean") is True and (None in counts or any(count != 0 for count in counts)):
            raise ValueError(f"clean flag disagrees with counters for {item.get('test_id')}")
        if item.get("status") == "PASS":
            if cleanup.get("clean") is not True:
                raise ValueError(f"PASS requires clean cleanup proof for {item.get('test_id')}")
            if not item.get("command") or not item.get("raw_artifact_paths"):
                raise ValueError(f"PASS requires command and raw evidence for {item.get('test_id')}")
            if item.get("test_id") == "P4-A10" and any(
                candidate.get("target_build_status") != "PASS"
                or not candidate.get("runtime_identity")
                for candidate in document["candidates"]
            ):
                raise ValueError("P4-A10 PASS requires target build and runtime identity")

    for key in (
        "sanitized_config",
        "runner",
        "conversion_runner",
        "live_runner",
        "valid_bits_runner",
        "fixture_generator",
        "candidate_provenance",
    ):
        artifact = document[key]
        artifact_path = resolve_repo_artifact(root, artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != artifact["sha256"]:
            raise ValueError(f"artifact checksum mismatch: {key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="create a Pending evidence packet")
    prepare.add_argument("--evidence-dir", type=Path)
    prepare.add_argument("--config", type=Path)
    prepare.add_argument("--allow-dirty", action="store_true")
    validate = subparsers.add_parser("validate", help="validate a packet manifest")
    validate.add_argument("manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required")
    args = parse_args()
    root = repo_root()
    if args.command == "validate":
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(document, root)
        print(f"Option A manifest valid: {args.manifest}")
        return 0

    dirty = git_output(root, "status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise RuntimeError("Git worktree must be clean for an evidence packet")
    source_sha = git_output(root, "rev-parse", "HEAD")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    packet_id = f"M1-P4-{stamp}"
    evidence_dir = args.evidence_dir or root / "poc_audio/evidence/m3_option_a" / stamp
    evidence_dir.mkdir(parents=True, exist_ok=False)
    (evidence_dir / "raw").mkdir()
    config_path = (args.config or root / "poc_audio/config/option_a.sanitized.json").resolve()
    manifest = create_manifest(root, source_sha, packet_id, config_path)
    validate_manifest(manifest, root)
    manifest_path = evidence_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Option A Pending packet prepared: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
