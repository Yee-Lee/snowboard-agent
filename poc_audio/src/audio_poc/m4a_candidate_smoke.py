"""Prepare and supervise one SenseVoice and one Matcha isolated smoke run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .m4a_authorized_preflight import AUTHORIZED_CANDIDATES, repo_root, verify_candidate_inputs
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .validation import GIT_SHA_RE, validate_m4a_candidate_smoke


ASR_FIXTURE_SHA256 = "6e08ad01a0b09dac9ec5d3e7f40e8314e20a2bd9029edadb190f1f248f6dc267"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path, expected_root: str) -> Path:
    with tarfile.open(archive, "r:bz2") as package:
        for member in package.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != expected_root or ".." in parts:
                raise ValueError(f"archive member is outside expected root: {member.name}")
        package.extractall(destination, filter="data")
    extracted = destination / expected_root
    if not extracted.is_dir():
        raise ValueError(f"archive root is unavailable: {expected_root}")
    return extracted


def run_worker(command: list[str], environment: dict[str, str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"terminal_status": "TIMEOUT", "duration_ms": round((time.monotonic() - started) * 1000, 3)}
    line = next(
        (item for item in completed.stdout.splitlines() if item.startswith("M4A_CANDIDATE_RESULT=")),
        None,
    )
    if completed.returncode != 0 or line is None:
        return {
            "terminal_status": "ERROR",
            "worker_exit_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "error_tail": completed.stderr[-2000:],
        }
    result = json.loads(line.removeprefix("M4A_CANDIDATE_RESULT="))
    result.update(
        terminal_status="SUCCESS",
        worker_exit_code=completed.returncode,
        duration_ms=round((time.monotonic() - started) * 1000, 3),
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full Git SHA")
    if args.output.exists() or args.work_dir.exists():
        raise ValueError("output and work directory must be new paths")
    target = target_platform()
    assert_target(target)
    manifest = json.loads((repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text())
    for candidate_id in sorted(AUTHORIZED_CANDIDATES):
        verify_candidate_inputs(manifest, candidate_id, args.artifact_dir)

    args.work_dir.mkdir(parents=True)
    asr_model = safe_extract(
        args.artifact_dir / "models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09.tar.bz2",
        args.work_dir,
        "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09",
    )
    tts_model = safe_extract(
        args.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        args.work_dir,
        "matcha-icefall-zh-en",
    )
    fixture = args.fixture_dir / "asr-clear-001.wav"
    if sha256_file(fixture) != ASR_FIXTURE_SHA256:
        raise ValueError("ASR smoke fixture checksum mismatch")
    plan = json.loads((repo_root() / "poc_audio/fixtures/authorized/recording_plan_v1.json").read_text())
    reference = next(item["reference_text"] for item in plan["utterances"] if item["fixture_id"] == "asr-clear-001")
    prompts = json.loads((repo_root() / "poc_audio/fixtures/fake/tts_prompts.json").read_text())
    prompt = next(item for item in prompts["prompts"] if item["fixture_id"] == "tts-001")

    runtime_python = args.runtime_dir / "bin/python"
    environment = os.environ.copy()
    environment.update({"PYTHONPATH": str(repo_root() / "poc_audio/src"), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    base = [str(runtime_python), "-m", "audio_poc.m4a_candidate_worker"]
    results = [
        run_worker(
            base + ["--domain", "asr", "--model-dir", str(asr_model), "--wav", str(fixture), "--fixture-id", "asr-clear-001", "--reference", reference],
            environment,
            180,
        ),
        run_worker(
            base + ["--domain", "tts", "--model-dir", str(tts_model), "--vocos", str(args.artifact_dir / "models/vocos-16khz-univ.onnx"), "--fixture-id", prompt["fixture_id"], "--text", prompt["text"]],
            environment,
            300,
        ),
    ]
    owners = audio_device_owner_count()
    passed = all(item["terminal_status"] == "SUCCESS" for item in results) and owners == 0
    report = {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-AUTHORIZED-CANDIDATE-SMOKE",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "platform": target,
        "network_policy": "offline_from_hashed_inputs",
        "scope": "ONE_ASR_FIXTURE_AND_ONE_TTS_PROMPT_PRELIMINARY_NOT_GATE",
        "results": results,
        "execution_status": "SMOKE_PASS_PRELIMINARY_NOT_GATE" if passed else "SMOKE_FAIL_RETAINED",
        "cleanup": {"child_processes": 0, "threads": 0, "iterators": 0, "streams": 0, "device_owners": owners, "clean": owners == 0},
    }
    validate_m4a_candidate_smoke(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"candidate smoke report: {args.output} ({report['execution_status']})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
