"""Static AR1M1 workstation-development verifier; it never loads a model."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from asr_r1.data_safety import scan_repository
from asr_r1.paths import resolve_repo_resource


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CANDIDATES = [
    "asr-sherpa-streaming-zipformer-zh-xlarge-int8-2025-06-30",
    "asr-sherpa-wenet-wenetspeech-streaming-ctc-int8",
    "asr-nvidia-nemotron-3-5-streaming-0-6b-q8-0",
    "asr-sherpa-streaming-zipformer-zh-large-int8-2025-06-30",
    "asr-sherpa-wenet-aishell-streaming-ctc-int8",
]


def _json(root: Path, relative: str) -> dict:
    with resolve_repo_resource(root, relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify(root: Path, require_clean: bool = False) -> list[str]:
    root = root.resolve()
    failures: list[str] = []
    required = [
        "asr_r1/diagnostic_pipeline.py",
        "asr_r1/m1_baseline.py",
        "asr_r1/m1_lifecycle.py",
        "asr_r1/m1_native_smoke.py",
        "asr_r1/m1_offline_audit.py",
        "asr_r1/m1_preflight.py",
        "asr_r1/m1_streaming_probe.py",
        "asr_r1/nemo_adapter.py",
        "asr_r1/sherpa_adapter.py",
        "asr_r1/manifests/m1_baseline_method.json",
        "asr_r1/manifests/m1_fixture_coverage_audit.json",
        "asr_r1/manifests/m1_identity_screening.json",
        "asr_r1/manifests/m1_postprocess_research.json",
        "asr_r1/manifests/m1_smoke_fixture.json",
        "docs/research/ar1_m1_workstation_development_report.md",
    ]
    for relative in required:
        _require(
            resolve_repo_resource(root, relative).is_file(),
            f"missing {relative}",
            failures,
        )

    identity = _json(root, "asr_r1/manifests/m1_identity_screening.json")
    _require(
        [row.get("candidate_id") for row in identity.get("rows", [])]
        == EXPECTED_CANDIDATES,
        "M1 candidate identities or order changed",
        failures,
    )

    method = _json(root, "asr_r1/manifests/m1_baseline_method.json")
    _require(method.get("formal_result") is False, "M1 method must be non-formal", failures)
    _require(
        [row.get("candidate_id") for row in method.get("candidate_commands", [])]
        == EXPECTED_CANDIDATES,
        "M1 method candidate order changed",
        failures,
    )
    metrics = method.get("metrics", {})
    for key in (
        "full_utterance_decode_wall_seconds",
        "full_utterance_rtf",
        "ttft_ms",
        "speech_end_to_final_ms",
    ):
        _require(key in metrics, f"M1 method lacks {key}", failures)

    fixture = _json(root, "asr_r1/manifests/m1_smoke_fixture.json")
    speech = fixture.get("speech_interval", {})
    _require(
        speech.get("annotation_status") == "HUMAN_REVIEWED_FROZEN"
        and speech.get("derived_start_ms") == 0
        and speech.get("derived_end_ms") == 2660,
        "frozen fixture speech interval is missing or changed",
        failures,
    )

    postprocess = _json(root, "asr_r1/manifests/m1_postprocess_research.json")
    _require(
        postprocess.get("formal_result") is False
        and "REAL_POSTPROCESS_NOT_RUN" in postprocess.get("status", ""),
        "post-process research must remain diagnostic only",
        failures,
    )
    _require(
        postprocess.get("observed_m1_adapter_surface", {}).get("nbest")
        == "TOP_ONE_FALLBACK_ONLY",
        "current N-best limitation is not preserved",
        failures,
    )

    report = resolve_repo_resource(
        root, "docs/research/ar1_m1_workstation_development_report.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "NOT PI 5",
        "Ubuntu 24.04",
        "exactly 2 online vCPUs",
        "Full-utterance RTF",
        "TTFT",
        "not a frozen advance decision",
    ):
        _require(phrase in report, f"M1 report lacks boundary: {phrase}", failures)

    milestone = resolve_repo_resource(
        root, "docs/milestone/ar1_m1_runtime_feasibility.md"
    ).read_text(encoding="utf-8")
    _require("Status: `IN_PROGRESS`" in milestone, "AR1M1 must remain in progress", failures)
    _require("not Raspberry Pi 5" in milestone, "M1 milestone lacks Pi boundary", failures)

    if require_clean:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        _require(not status, "worktree must be clean", failures)

    for finding in scan_repository(root):
        failures.append(f"data safety: {finding.path}: {finding.reason}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    failures = verify(REPO_ROOT, require_clean=args.require_clean)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS AR1M1 workstation-development static readiness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
