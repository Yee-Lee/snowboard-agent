"""Static AR1M0 exit-gate verifier; it does not run or acquire real models."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from asr_r1.data_safety import scan_repository
from asr_r1.paths import resolve_repo_resource


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL_SHA = "5694ead4ba6be928fdb4dbdf6da7155b214d72bd"
CONTRACT_PATH = Path(
    "docs/handoff/inbound/DELIVERY-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001.md"
)
RECEIPT_PATH = Path(
    "docs/handoff/outbound/ACK-AUDIO-POC-ASR-PRODUCT-R1-CONTRACT-001.md"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _git_json(specifier: str) -> dict:
    return json.loads(_git("show", specifier))


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify(root: Path, expect_tag: bool = False) -> list[str]:
    root = root.resolve()
    failures: list[str] = []

    _require(_git("branch", "--show-current") == "asr_r1", "branch must be asr_r1", failures)
    _require(
        _git("rev-list", "-n", "1", "audio_m4") == CONTROL_SHA,
        "audio_m4 must resolve to the immutable control SHA",
        failures,
    )
    _require(
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", CONTROL_SHA, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0,
        "asr_r1 must retain ancestry from audio_m4",
        failures,
    )

    contract = resolve_repo_resource(root, CONTRACT_PATH)
    receipt = resolve_repo_resource(root, RECEIPT_PATH).read_text(encoding="utf-8")
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    match = re.search(r"Contract SHA-256\*\*:\s*\n\s*`([0-9a-f]{64})`", receipt)
    _require(match is not None and match.group(1) == digest, "contract receipt digest mismatch", failures)

    required_paths = [
        Path("asr_r1/manifests/candidate_tracker.json"),
        Path("asr_r1/manifests/control_provenance.json"),
        Path("asr_r1/manifests/fixture_reuse_audit_plan.json"),
        Path("asr_r1/schemas/lifecycle_command.schema.json"),
        Path("asr_r1/schemas/pcm_chunk.schema.json"),
        Path("asr_r1/schemas/streaming_event.schema.json"),
        Path("asr_r1/protocol.py"),
        Path("asr_r1/fake_runtime.py"),
    ]
    for path in required_paths:
        _require(resolve_repo_resource(root, path).is_file(), f"missing {path}", failures)

    tracker = _json(resolve_repo_resource(root, "asr_r1/manifests/candidate_tracker.json"))
    _require(len(tracker.get("candidates", [])) == 3, "candidate tracker must contain three rows", failures)
    _require(
        tracker.get("status") == "IDENTITY_TRACKING_ONLY_NO_EXECUTION_AUTHORIZED",
        "candidate tracker must deny execution",
        failures,
    )

    provenance = _json(resolve_repo_resource(root, "asr_r1/manifests/control_provenance.json"))
    _require(
        provenance.get("historical_control", {}).get("commit") == CONTROL_SHA,
        "control provenance SHA mismatch",
        failures,
    )
    _require(
        provenance.get("whisper_control", {}).get("model", {}).get("sha256")
        == "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9",
        "Whisper control identity mismatch",
        failures,
    )
    _require(
        provenance.get("silero_control", {}).get("model", {}).get("sha256")
        == "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3",
        "Silero control identity mismatch",
        failures,
    )
    old_whisper = _git_json("audio_m4:poc_audio/manifests/m2b_base_q8_probe.json")
    old_recipe = _git_json("audio_m4:poc_audio/manifests/m2b_c_asr_recipe_proposal.json")
    old_packet = _git_json("audio_m4:poc_audio/manifests/m3_risk_qualification_packet.json")
    old_silero = _git_json("audio_m4:poc_audio/manifests/m2_vad_silero_fallback.json")
    old_candidates = _git_json("audio_m4:poc_audio/manifests/m4a_gate1b_candidates.json")
    old_whisper_engine = next(
        item["engine"]
        for item in old_candidates["candidates"]
        if item["candidate_id"] == "asr-whispercpp-base-q5_1-1.9.2"
    )
    _require(
        provenance["whisper_control"]["model"]["sha256"]
        == old_whisper["artifact"]["sha256"]
        == old_recipe["primary"]["artifact"]["sha256"]
        == old_packet["candidates"]["asr_primary"]["model_sha256"],
        "Whisper provenance does not agree across immutable historical records",
        failures,
    )
    _require(
        provenance["whisper_control"]["engine"]["revision"]
        == old_whisper_engine["immutable_revision"].removeprefix("git:")
        and provenance["whisper_control"]["engine"]["source_archive_sha256"]
        == old_whisper_engine["source_sha256"],
        "Whisper engine provenance differs from audio_m4",
        failures,
    )
    _require(
        provenance["whisper_control"]["accepted_configuration"]
        == {
            key: old_recipe["shared_recipe"][key]
            for key in [
                "pcm",
                "endpoint",
                "threads",
                "language",
                "decoder",
                "context",
                "timestamps",
                "internal_vad",
                "initial_prompt_sha256",
            ]
        },
        "Whisper accepted configuration differs from audio_m4",
        failures,
    )
    _require(
        provenance["silero_control"]["engine"]["revision"]
        == old_silero["engine"]["commit"]
        and provenance["silero_control"]["model"]["sha256"]
        == old_silero["model"]["sha256"],
        "Silero provenance differs from audio_m4",
        failures,
    )

    fixtures = _json(
        resolve_repo_resource(root, "asr_r1/manifests/fixture_reuse_audit_plan.json")
    )
    _require(
        all(item.get("assigned_role") is None for item in fixtures.get("sources_to_audit", [])),
        "fixture plan must not assign roles at AR1M0",
        failures,
    )
    _require(
        "NO_HOLDOUT_ASSIGNED" in fixtures.get("status", ""),
        "fixture plan must explicitly deny premature holdout assignment",
        failures,
    )
    fixture_gates = fixtures.get("policy", {}).get("milestone_gates", [])
    _require(
        [gate.get("milestone") for gate in fixture_gates]
        == [
            "AR1M0",
            "AR1M1_ENTRY_BEFORE_REAL_SMOKE",
            "AR1M1_EXIT_AR1M2_ENTRY",
            "BEFORE_AR1M2A_FORMAL",
            "AR1M3_ENTRY_AFTER_PIPELINE_FREEZE",
        ],
        "fixture collection milestone gates are missing or out of order",
        failures,
    )
    if fixture_gates:
        _require(
            fixture_gates[0].get("collection") == "PROHIBITED"
            and "QUALIFICATION_ONLY" in fixture_gates[-1].get("collection", ""),
            "fixture collection boundaries are not fail-closed",
            failures,
        )
    for source in fixtures.get("sources_to_audit", []):
        reference = source.get("historical_reference", "")
        result = subprocess.run(
            ["git", "cat-file", "-e", reference],
            cwd=root,
            check=False,
            capture_output=True,
        )
        _require(result.returncode == 0, f"missing historical fixture source {reference}", failures)

    for path in [
        "docs/specs/evaluation.md",
        "docs/specs/data_safety.md",
        "docs/specs/fixture_policy.md",
        "docs/specs/outcome_checklist.md",
        "docs/specs/streaming_protocol.md",
    ]:
        text = resolve_repo_resource(root, path).read_text(encoding="utf-8")
        _require("Status: `AUTHORITATIVE / FROZEN AT AR1M0`" in text, f"{path} is not frozen", failures)

    milestone = resolve_repo_resource(
        root, "docs/milestone/ar1_m0_research_readiness.md"
    ).read_text(encoding="utf-8")
    index = resolve_repo_resource(root, "docs/milestone/README.md").read_text(
        encoding="utf-8"
    )
    _require("Status: `COMPLETE`" in milestone, "AR1M0 milestone is not complete", failures)
    _require("| AR1M0 | `COMPLETE` |" in index, "milestone index does not mark AR1M0 complete", failures)

    if expect_tag:
        tag_type = subprocess.run(
            ["git", "cat-file", "-t", "refs/tags/asr_r1_m0"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        _require(
            tag_type.returncode == 0 and tag_type.stdout.strip() == "tag",
            "asr_r1_m0 must exist as an annotated tag",
            failures,
        )
        if tag_type.returncode == 0:
            _require(
                _git("rev-list", "-n", "1", "asr_r1_m0") == _git("rev-parse", "HEAD"),
                "asr_r1_m0 must resolve to HEAD",
                failures,
            )
        _require(not _git("status", "--porcelain"), "post-tag worktree must be clean", failures)

    for finding in scan_repository(root):
        failures.append(f"data safety: {finding.path}: {finding.reason}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-tag", action="store_true")
    args = parser.parse_args()
    failures = verify(REPO_ROOT, expect_tag=args.expect_tag)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS AR1M0 static exit-gate verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
