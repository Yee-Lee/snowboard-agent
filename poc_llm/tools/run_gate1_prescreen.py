#!/usr/bin/env python3
"""Execute one frozen Gate 1 candidate command and validate P2/P3 output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
from typing import Any


PACKET_ID = "G1-UBUNTU-PRESCREEN-001"
COMMAND_TIMEOUT_SECONDS = 1800
TERM_GRACE_SECONDS = 2
ARCHITECTURES = {"ubuntu-x86_64": "x86_64", "ubuntu-aarch64": "aarch64"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_lock(lock: dict[str, Any], paths: dict[str, Path]) -> None:
    for key, path in paths.items():
        expected = lock["artifacts"][key]["sha256"]
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"{key} checksum mismatch: {actual}")


def candidate_errors(candidate: dict[str, Any]) -> list[str]:
    errors = []
    if not candidate.get("candidate_id", "").startswith("CAND-"):
        errors.append("candidate_id is invalid")
    for path in (("runtime", "source_sha256"), ("model", "artifact_sha256")):
        value = candidate.get(path[0], {}).get(path[1], "")
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            errors.append(f"{path[0]}.{path[1]} must be a lowercase SHA-256")
    if not candidate.get("license"):
        errors.append("license is required")
    if candidate.get("offline") is not True:
        errors.append("offline eligibility is required")
    if candidate.get("aarch64_compatible") is not True:
        errors.append("aarch64 compatibility is required")
    return errors


def run_bounded(command: list[str], stdout_path: Path, stderr_path: Path) -> tuple[int, bool]:
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        timed_out = False
        try:
            return_code = process.wait(timeout=COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=TERM_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait(timeout=TERM_GRACE_SECONDS)
    return return_code, timed_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=tuple(ARCHITECTURES), required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()

    actual_arch = platform.machine()
    if actual_arch != ARCHITECTURES[args.platform]:
        print(json.dumps({"packet_id": PACKET_ID, "result": "INCONCLUSIVE", "reason": f"expected {ARCHITECTURES[args.platform]}, got {actual_arch}"}))
        return 2

    lock = load(args.lock)
    verify_lock(lock, {"catalog": args.catalog, "validator": args.validator})
    candidate = load(args.candidate_manifest)
    errors = candidate_errors(candidate)
    command = candidate.get("commands", {}).get(args.platform)
    if not isinstance(command, list) or not command:
        errors.append(f"missing fixed command for {args.platform}")
    if errors:
        print(json.dumps({"packet_id": PACKET_ID, "result": "FAIL", "violations": errors}, sort_keys=True))
        return 1

    args.raw_dir.mkdir(parents=True, exist_ok=False)
    result_path = args.raw_dir / "candidate-results.json"
    stderr_path = args.raw_dir / "candidate-stderr.txt"
    return_code, timed_out = run_bounded(command, result_path, stderr_path)
    if timed_out:
        print(json.dumps({"packet_id": PACKET_ID, "result": "FAIL", "reason": "candidate command timeout and cleanup escalation"}))
        return 1
    if return_code != 0:
        print(json.dumps({"packet_id": PACKET_ID, "result": "FAIL", "reason": f"candidate exit {return_code}"}))
        return 1

    validation = subprocess.run(
        [sys.executable, str(args.validator), "--catalog", str(args.catalog), "--results", str(result_path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if validation.returncode not in (0, 1):
        print(json.dumps({"packet_id": PACKET_ID, "result": "INCONCLUSIVE", "reason": "validator execution invalid"}))
        return 2
    validator_report = json.loads(validation.stdout)
    report = {
        "candidate_id": candidate["candidate_id"],
        "packet_id": PACKET_ID,
        "platform": args.platform,
        "raw_result_sha256": digest(result_path),
        "result": validator_report["result"],
        "stderr_sha256": digest(stderr_path),
        "validator": validator_report,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return validation.returncode


if __name__ == "__main__":
    raise SystemExit(main())
