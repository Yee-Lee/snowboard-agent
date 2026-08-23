"""Run one Matcha inference in a disabled network namespace for M4a P12."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .m4a_authorized_preflight import repo_root, verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_tts_lifecycle import PROMPTS_SHA256, TTS_ID, run_scenario, sha256_file
from .validation import GIT_SHA_RE, validate_m4a_tts_offline


def namespace_interfaces() -> list[dict[str, object]]:
    command = [
        "unshare", "--user", "--map-root-user", "--net", "--",
        "ip", "-json", "link",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    interfaces = json.loads(completed.stdout)
    if not isinstance(interfaces, list):
        raise ValueError("network namespace interface output is invalid")
    return interfaces


def offline_trace_summary(path: Path, interfaces: list[dict[str, object]]) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    active_lines = [line for line in lines if line.strip()]
    interface_summary = [
        {
            "ifname": str(item.get("ifname", "")),
            "operstate": str(item.get("operstate", "")),
            "flags": sorted(str(flag) for flag in item.get("flags", [])),
        }
        for item in interfaces
    ]
    isolated = (
        len(interface_summary) == 1
        and interface_summary[0]["ifname"] == "lo"
        and interface_summary[0]["operstate"] != "UP"
    )
    return {
        "method": "unshare_user_and_network_namespace_loopback_down_plus_strace_network",
        "network_disabled": isolated,
        "interfaces": interface_summary,
        "trace_sha256": sha256_file(path) if path.is_file() else None,
        "network_syscall_line_count": len(active_lines) if path.is_file() else None,
        "zero_network_syscalls": path.is_file() and not active_lines,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
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
    for executable in ("unshare", "ip", "strace"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"required P12 executable is absent: {executable}")

    target = target_platform()
    assert_target(target)
    manifest = json.loads((repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text())
    verify_candidate_inputs(manifest, TTS_ID, args.artifact_dir)
    prompts_path = repo_root() / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(prompts_path) != PROMPTS_SHA256:
        raise ValueError("tracked TTS prompt checksum mismatch")
    prompt = json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"][0]

    args.work_dir.mkdir(parents=True)
    model = safe_extract(
        args.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        args.work_dir,
        "matcha-icefall-zh-en",
    )
    trace_path = args.work_dir / "network.trace"
    interfaces = namespace_interfaces()
    worker = [
        str(args.runtime_dir / "bin/python"), "-m", "audio_poc.m4a_tts_lifecycle_worker",
        "--model-dir", str(model),
        "--vocos", str(args.artifact_dir / "models/vocos-16khz-univ.onnx"),
    ]
    isolated_worker = [
        "unshare", "--user", "--map-root-user", "--net", "--", *worker,
    ]
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(repo_root() / "poc_audio/src"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
    })
    owners_before = audio_device_owner_count()
    run = run_scenario(isolated_worker, environment, "p12_offline", prompt, trace_path)
    owners_after = audio_device_owner_count()
    network = offline_trace_summary(trace_path, interfaces)
    passed = (
        run["terminal_status"] == "SUCCESS"
        and run["cleanup"]["clean"]
        and network["network_disabled"] is True
        and network["zero_network_syscalls"] is True
        and owners_before == owners_after == 0
    )
    report = {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-WP3-MATCHA-OFFLINE",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "candidate_id": TTS_ID,
        "platform": target,
        "scope": "MATCHA_NETWORK_DISABLED_INFERENCE_NO_PLAYBACK",
        "prompt_identity": {
            "fixture_id": prompt["fixture_id"],
            "prompts_sha256": PROMPTS_SHA256,
        },
        "offline_run": run,
        "network_evidence": network,
        "security": {
            "pcm_emitted": False,
            "audio_device_opened": False,
            "speaker_playback": False,
        },
        "execution_status": "P12_PASS" if passed else "P12_FAIL_RETAINED",
        "cleanup": {
            "child_processes": 0,
            "threads": 0,
            "iterators": 0,
            "streams": 0,
            "device_owners": owners_after,
            "clean": owners_after == 0,
        },
    }
    validate_m4a_tts_offline(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Matcha offline report: {args.output} ({report['execution_status']})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
