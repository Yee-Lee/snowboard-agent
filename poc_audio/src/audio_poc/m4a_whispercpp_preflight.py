"""Fail-closed artifact preflight for the ACK-002 whisper.cpp recovery rows.

This module never builds whisper.cpp, loads a model, or runs inference.  It
only verifies the exact controlled inputs and enforces the Q8-before-Q5 gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


ACK_ID = "DELIVERY-AUDIO-POC-M4A-G1B-ASR-RECOVERY-ACK-002"
MANIFEST_ID = "M4A-G1B-ASR-RECOVERY-ACK-002"
PRIMARY_ID = "asr-whispercpp-small-q8_0-1.9.2"
FALLBACK_ID = "asr-whispercpp-small-q5_1-1.9.2"
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NOTICE_PATHS = {
    "repository_license": PurePosixPath("notices/model-repository-LICENSE"),
    "whispercpp_model_documentation": PurePosixPath(
        "notices/whispercpp-model-documentation.md"
    ),
    "upstream_whisper_lineage": PurePosixPath("notices/upstream-whisper-lineage.md"),
}


@dataclass(frozen=True, slots=True)
class VerifiedFile:
    role: str
    relative_path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "role": self.role,
            "relative_path": self.relative_path,
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


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys do not match the frozen ACK")


def validate_recovery_manifest(document: dict[str, Any]) -> None:
    """Validate the decision-bearing ACK manifest without third-party packages."""

    required = {
        "schema_version", "manifest_id", "ack_id", "reviewed_poc", "status",
        "controlled_artifact_policy", "engine_source", "model_repository",
        "candidates", "execution_policy", "runtime_profile", "gates",
        "build_closure",
    }
    _require_exact_keys(document, required, "recovery manifest")
    if (
        document["schema_version"] != "1.0"
        or document["manifest_id"] != MANIFEST_ID
        or document["ack_id"] != ACK_ID
        or document["status"] != "AUTHORIZED_NOT_EXECUTED"
    ):
        raise ValueError("recovery manifest identity is invalid")
    if document["reviewed_poc"] != {
        "branch": "audio",
        "commit": "ccfc2477a04cd2c53341fabb13a620fd89a51e5a",
    }:
        raise ValueError("recovery manifest reviewed POC binding is invalid")

    policy = document["controlled_artifact_policy"]
    if policy != {
        "locator_prefix": "controlled://audio-poc/gate1b/",
        "tracked_in_git": False,
        "network_policy": "offline_from_hashed_inputs",
    }:
        raise ValueError("recovery controlled-artifact policy is invalid")

    source = document["engine_source"]
    expected_source = {
        "name": "whisper.cpp",
        "version": "1.9.2",
        "git_commit": "306c88f4d1286aec1bf96e544632897886af5501",
        "filename": "whisper.cpp-v1.9.2.tar.gz",
        "size_bytes": 9613762,
        "sha256": "988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47",
        "controlled_locator": "controlled://audio-poc/gate1b/sources/whisper.cpp-v1.9.2.tar.gz",
        "license": "MIT",
        "required_archive_notice": "LICENSE",
    }
    if source != expected_source:
        raise ValueError("recovery engine source identity is invalid")

    repository = document["model_repository"]
    if repository != {
        "name": "ggerganov/whisper.cpp",
        "revision": "5359861c739e955e79d9a303bcbc70fb988958b1",
        "required_notices": [
            "repository_license",
            "whispercpp_model_documentation",
            "upstream_whisper_lineage",
        ],
        "legal_status": "POC_EXECUTION_ONLY_FINAL_REDISTRIBUTION_PENDING",
    }:
        raise ValueError("recovery model repository identity or notices are invalid")

    expected_candidates = {
        PRIMARY_ID: (
            "Q8_0", "PRIMARY", "ggml-small-q8_0.bin", 264464607,
            "49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f",
        ),
        FALLBACK_ID: (
            "Q5_1", "CONDITIONAL_FALLBACK", "ggml-small-q5_1.bin", 190085487,
            "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb",
        ),
    }
    candidates = document["candidates"]
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ValueError("recovery manifest must contain exactly two candidates")
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        if candidate_id not in expected_candidates:
            raise ValueError("recovery manifest contains an unauthorized candidate")
        quantization, disposition, filename, size_bytes, digest = expected_candidates[candidate_id]
        expected = {
            "candidate_id": candidate_id,
            "quantization": quantization,
            "disposition": disposition,
            "filename": filename,
            "size_bytes": size_bytes,
            "sha256": digest,
            "controlled_locator": f"controlled://audio-poc/gate1b/models/{filename}",
        }
        if candidate != expected:
            raise ValueError(f"recovery candidate identity is invalid: {candidate_id}")

    if document["execution_policy"] != {
        "default_candidate": PRIMARY_ID,
        "fallback_candidate": FALLBACK_ID,
        "fallback_requires": "Q8_QUALITY_PASS_AND_LATENCY_OR_RSS_TRIGGER",
        "stop_on_q8_quality_failure": True,
        "do_not_compare_when_q8_passes_without_trigger": True,
    }:
        raise ValueError("recovery execution policy is invalid")
    profile = document["runtime_profile"]
    if profile != {
        "cpu_threads": 4,
        "workers": 1,
        "decoding": "greedy",
        "beam_size": 1,
        "best_of": 1,
        "temperature": 0,
        "language": "zh",
        "translate": False,
        "condition_on_previous_text": False,
        "timestamps": False,
        "internal_vad": False,
        "input": "frozen_16khz_mono_bounded_utterance",
    }:
        raise ValueError("recovery decoding profile is invalid")

    if document["gates"] != {
        "hot_final_transcript_p95_seconds_max": 1.5,
        "hot_final_transcript_advisory_seconds_max": 1.0,
        "rtf_p95_max": 2.0,
        "taiwan_mandarin_core_cer_percent_max": 20.0,
        "overall_sentence_correctness_percent_min": 70.0,
        "peak_rss_fallback_trigger_mib": 1250.0,
    }:
        raise ValueError("recovery frozen gates are invalid")

    expected_cache = {
        "GGML_NATIVE": "OFF", "GGML_BLAS": "OFF", "GGML_CUDA": "OFF",
        "GGML_VULKAN": "OFF", "GGML_OPENCL": "OFF", "GGML_RPC": "OFF",
        "GGML_OPENMP": "OFF", "GGML_METAL": "OFF", "GGML_SYCL": "OFF",
        "GGML_KOMPUTE": "OFF", "GGML_CCACHE": "OFF", "WHISPER_CURL": "OFF",
        "WHISPER_BUILD_SERVER": "OFF", "WHISPER_COMMON_FFMPEG": "OFF",
        "WHISPER_SDL2": "OFF", "WHISPER_BUILD_TESTS": "OFF",
        "WHISPER_BUILD_EXAMPLES": "OFF", "WHISPER_USE_SYSTEM_GGML": "OFF",
        "WHISPER_COREML": "OFF", "WHISPER_OPENVINO": "OFF",
        "WHISPER_MKL": "OFF",
    }
    if document["build_closure"].get("cmake_cache") != expected_cache:
        raise ValueError("recovery CPU-only CMake closure is invalid")


def resolve_controlled_path(
    document: dict[str, Any], locator: str, filename: str, artifact_dir: Path
) -> Path:
    prefix = document["controlled_artifact_policy"]["locator_prefix"]
    if not locator.startswith(prefix):
        raise ValueError(f"controlled locator is outside the ACK store: {filename}")
    relative = PurePosixPath(locator.removeprefix(prefix))
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or relative.name != filename
    ):
        raise ValueError(f"controlled locator is invalid: {filename}")
    root = artifact_dir.resolve()
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"controlled locator escapes the ACK store: {filename}")
    return path


def verify_exact_file(path: Path, role: str, expected_size: int, expected_sha: str,
                      artifact_dir: Path) -> VerifiedFile:
    if not path.is_file():
        raise ValueError(f"required controlled file is unavailable: {path.name}")
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(f"controlled file size mismatch: {path.name}")
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise ValueError(f"controlled file checksum mismatch: {path.name}")
    return VerifiedFile(role, path.relative_to(artifact_dir.resolve()).as_posix(), actual_size, actual_sha)


def verify_source_license(archive: Path, required_name: str) -> None:
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
    except (tarfile.TarError, OSError) as error:
        raise ValueError("engine source archive is not a readable tar.gz") from error
    for member in members:
        relative = PurePosixPath(member.name)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("engine source archive contains an unsafe path")
        if member.issym() or member.islnk():
            link = PurePosixPath(member.linkname)
            if link.is_absolute() or ".." in link.parts:
                raise ValueError("engine source archive contains an unsafe link")
    if not any(PurePosixPath(member.name).name == required_name and member.isfile() for member in members):
        raise ValueError("engine source archive does not contain the required LICENSE")


def q5_fallback_reason(q8_result: dict[str, Any], expected_source_sha: str | None = None) -> str:
    if (
        q8_result.get("report_id") != "M4A-G1B-ASR-RECOVERY-QUALIFICATION"
        or q8_result.get("review_status") != "REVIEWED"
        or q8_result.get("candidate_id") != PRIMARY_ID
    ):
        raise ValueError("Q5 fallback proof is not a Q8 result")
    if expected_source_sha is not None and q8_result.get("poc_source_sha") != expected_source_sha:
        raise ValueError("Q5 fallback proof does not bind the current Candidate SHA")
    if (
        q8_result.get("execution_status") not in {
            "QUALITY_PASS_PERFORMANCE_FAIL_RETAINED",
            "QUALITY_PERFORMANCE_PASS_PENDING_REVIEW_AND_LIFECYCLE",
        }
        or q8_result.get("summary", {}).get("execution_complete") is not True
        or q8_result.get("cleanup", {}).get("clean") is not True
    ):
        raise ValueError("Q5 fallback proof is not a complete clean Q8 qualification")
    quality = q8_result.get("quality", {})
    try:
        cer = float(quality.get("taiwan_mandarin_core_cer_percent", float("inf")))
        sentence = float(quality.get("overall_sentence_correctness_percent", float("-inf")))
    except (TypeError, ValueError) as error:
        raise ValueError("Q8 quality metrics are invalid") from error
    if not math.isfinite(cer) or not math.isfinite(sentence) or cer > 20.0 or sentence < 70.0:
        raise ValueError("Q8 failed a quality gate; Q5 execution must stop")
    performance = q8_result.get("performance", {})
    try:
        latency = float(performance.get("hot_final_transcript_p95_seconds", -1.0))
        rss = float(performance.get("peak_rss_mib", -1.0))
    except (TypeError, ValueError) as error:
        raise ValueError("Q8 fallback metrics are invalid") from error
    if not math.isfinite(latency) or not math.isfinite(rss) or latency < 0.0 or rss < 0.0:
        raise ValueError("Q8 fallback metrics are invalid")
    reasons = []
    if latency > 1.5:
        reasons.append("Q8_LATENCY_HARD_GATE")
    if rss > 1250.0:
        reasons.append("Q8_PEAK_RSS_TRIGGER")
    if not reasons:
        raise ValueError("Q8 passed without a fallback trigger; Q5 must not execute")
    return "+".join(reasons)


def _candidate(document: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for candidate in document["candidates"]:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise ValueError(f"candidate is not authorized by ACK-002: {candidate_id}")


def create_preflight_report(
    document: dict[str, Any], candidate_id: str, artifact_dir: Path,
    source_sha: str, q8_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_recovery_manifest(document)
    if not GIT_SHA_RE.fullmatch(source_sha):
        raise ValueError("source SHA must be a full lowercase Git SHA")
    if not artifact_dir.is_dir():
        raise ValueError("controlled artifact directory is unavailable")
    fallback_reason = None
    if candidate_id == FALLBACK_ID:
        if q8_result is None:
            raise ValueError("Q5 requires a reviewed Q8 result")
        fallback_reason = q5_fallback_reason(q8_result, source_sha)
    elif candidate_id != PRIMARY_ID:
        raise ValueError(f"candidate is not authorized by ACK-002: {candidate_id}")

    source = document["engine_source"]
    source_path = resolve_controlled_path(
        document, source["controlled_locator"], source["filename"], artifact_dir
    )
    verified = [verify_exact_file(
        source_path, "engine_source", source["size_bytes"], source["sha256"], artifact_dir
    )]
    verify_source_license(source_path, source["required_archive_notice"])

    candidate = _candidate(document, candidate_id)
    model_path = resolve_controlled_path(
        document, candidate["controlled_locator"], candidate["filename"], artifact_dir
    )
    verified.append(verify_exact_file(
        model_path, "model", candidate["size_bytes"], candidate["sha256"], artifact_dir
    ))
    notices = []
    for kind in document["model_repository"]["required_notices"]:
        path = (artifact_dir.resolve() / NOTICE_PATHS[kind]).resolve()
        if not path.is_relative_to(artifact_dir.resolve()) or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"required model notice is unavailable: {kind}")
        notices.append(VerifiedFile(
            kind, path.relative_to(artifact_dir.resolve()).as_posix(),
            path.stat().st_size, sha256_file(path),
        ).to_dict())

    return {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-ASR-RECOVERY-ARTIFACT-PREFLIGHT",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": source_sha,
        "ack_id": ACK_ID,
        "manifest_id": MANIFEST_ID,
        "candidate_id": candidate_id,
        "fallback_reason": fallback_reason,
        "verified_files": [item.to_dict() for item in verified],
        "verified_notices": notices,
        "network_policy": "offline_from_hashed_inputs",
        "execution_status": "ARTIFACT_PREFLIGHT_PASS_BUILD_NOT_RUN",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", choices=(PRIMARY_ID, FALLBACK_ID), default=PRIMARY_ID)
    parser.add_argument("--q8-result", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError("output must be a new path")
    manifest = json.loads(
        (repo_root() / "poc_audio/manifests/m4a_asr_recovery_ack002.json").read_text(
            encoding="utf-8"
        )
    )
    q8_result = None
    if args.q8_result is not None:
        q8_result = json.loads(args.q8_result.read_text(encoding="utf-8"))
    report = create_preflight_report(
        manifest, args.candidate, args.artifact_dir, args.source_sha, q8_result
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ACK-002 artifact preflight passed; build not run: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
