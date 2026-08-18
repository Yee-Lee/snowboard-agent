"""Verify the exact Gate 1B-approved offline candidate inputs.

This module deliberately does not import, install, or execute candidate code.
It is safe to run before the Pi clean-build packet is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ACK_COMMIT = "790c0f86e12422542ef94cacd3c4dd850e346bca"
PROPOSAL_COMMIT = "756ded69dd7b4661fcbac272d4d234c387890fc8"
AUTHORIZED_CANDIDATES = {
    "asr-sherpa-sensevoice-int8-2025-09-09",
    "tts-sherpa-matcha-zh-en-1.13.5",
}


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    role: str
    filename: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "role": self.role,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorized_candidate(document: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    if candidate_id not in AUTHORIZED_CANDIDATES:
        raise ValueError(f"candidate is not authorized by focused Gate 1B ACK: {candidate_id}")
    for candidate in document.get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            if candidate.get("requested_disposition") != "REQUEST_AUTHORIZE":
                raise ValueError(f"candidate manifest disposition is not authorize: {candidate_id}")
            return candidate
    raise ValueError(f"candidate is absent from Gate 1B proposal: {candidate_id}")


def verify_candidate_inputs(
    document: dict[str, Any], candidate_id: str, artifact_dir: Path
) -> list[VerifiedArtifact]:
    candidate = authorized_candidate(document, candidate_id)
    verified: list[VerifiedArtifact] = []
    seen_filenames: set[str] = set()
    for artifact in candidate["artifacts"]:
        filename = str(artifact["filename"])
        if filename in seen_filenames:
            continue
        seen_filenames.add(filename)
        path = artifact_dir / filename
        if not path.is_file():
            raise ValueError(f"required controlled artifact is unavailable: {filename}")
        actual_size = path.stat().st_size
        expected_size = int(artifact["size_bytes"])
        if actual_size != expected_size:
            raise ValueError(f"artifact size mismatch: {filename}")
        actual_sha = sha256_file(path)
        expected_sha = str(artifact["sha256"])
        if actual_sha != expected_sha:
            raise ValueError(f"artifact checksum mismatch: {filename}")
        verified.append(
            VerifiedArtifact(str(artifact["role"]), filename, actual_size, actual_sha)
        )
    return verified


def create_report(
    document: dict[str, Any], source_sha: str, artifact_dir: Path, candidate_ids: list[str]
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(source_sha):
        raise ValueError("source SHA must be a full lowercase Git SHA")
    if not artifact_dir.is_dir():
        raise ValueError("artifact directory is unavailable")
    reports = []
    for candidate_id in candidate_ids:
        candidate = authorized_candidate(document, candidate_id)
        reports.append(
            {
                "candidate_id": candidate_id,
                "domain": candidate["domain"],
                "engine": {
                    "name": candidate["engine"]["name"],
                    "version": candidate["engine"]["version"],
                },
                "verified_artifacts": [
                    item.to_dict()
                    for item in verify_candidate_inputs(document, candidate_id, artifact_dir)
                ],
                "execution_status": "PREFLIGHT_PASS_NOT_EXECUTED",
            }
        )
    return {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-AUTHORIZED-PREFLIGHT",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": source_sha,
        "core_gate1b_ack_commit": ACK_COMMIT,
        "poc_gate1b_proposal_commit": PROPOSAL_COMMIT,
        "network_policy": "offline_from_hashed_inputs",
        "candidate_reports": reports,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--candidate",
        action="append",
        choices=sorted(AUTHORIZED_CANDIDATES),
        help="repeat to preflight one or both authorized candidates (default: both)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError("output must be a new path")
    manifest_path = repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidate_ids = args.candidate or sorted(AUTHORIZED_CANDIDATES)
    report = create_report(document, args.source_sha, args.artifact_dir, candidate_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"authorized preflight passed: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
