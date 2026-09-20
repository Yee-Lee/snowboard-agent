"""Workstation entrypoint for the M4C-SS plan and deterministic cases."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import re

from poc_llm.m4c_ss.deterministic import run_controller_case
from poc_llm.m4c_ss.duplex import run_duplex_calibration
from poc_llm.m4c_ss.mapping import CANDIDATES
from poc_llm.m4c_ss.mapping_acoustic import make_usb_capture, run_acoustic_mapping_trace
from poc_llm.m4c_ss.plan import CONTROLLER_CASES, MAPPING_TRACES, build_plan, case_key
from poc_llm.m4c_ss.preflight import preflight_environment
from poc_llm.m4c_ss.surface import build_manifest, surface_digest, verify_manifest
from poc_llm.m4c_ss.target_factory import load_target_binding, materialize_core_backend


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "poc_llm/contracts/m4c_ss/m4c-ss-profile-001.json"
LOCK = ROOT / "poc_llm/m4c_ss/m4c-ss-surface-lock-v1.json"
_RUN_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    snapshot = subcommands.add_parser("snapshot")
    snapshot.add_argument("--output", type=Path, required=True)
    verify = subcommands.add_parser("verify-snapshot")
    verify.add_argument("--surface-sha256", required=True)
    preflight = subcommands.add_parser("preflight")
    preflight.add_argument("--operator-authorized", action="store_true")
    preflight.add_argument("--implementation-sha", required=True)
    preflight.add_argument("--surface-sha256", required=True)
    preflight.add_argument("--private-receipt", type=Path, required=True)
    controller = subcommands.add_parser("controller")
    controller.add_argument("case_id", choices=CONTROLLER_CASES)
    calibrate = subcommands.add_parser("calibrate")
    calibrate.add_argument("--operator-authorized", action="store_true")
    mapping = subcommands.add_parser("mapping-engineering")
    mapping.add_argument("trace_id", choices=MAPPING_TRACES)
    mapping.add_argument("candidate", choices=CANDIDATES)
    mapping.add_argument("repetition", type=int, choices=range(1, 4))
    mapping.add_argument("--run-id", required=True)
    mapping.add_argument("--operator-authorized", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan":
        plan = build_plan()
        print(json.dumps({
            "format": "m4c-ss-plan-v1",
            "expected_case_count": len(plan),
            "case_keys": [case_key(item) for item in plan],
        }, sort_keys=True))
        return 0
    if args.command == "snapshot":
        manifest = build_manifest(ROOT)
        with args.output.open("x", encoding="utf-8") as output:
            output.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"status": "WORKSTATION_SNAPSHOT", "surface_sha256": surface_digest(manifest)}))
        return 0
    if args.command == "verify-snapshot":
        manifest = json.loads(LOCK.read_text())
        verify_manifest(ROOT, manifest, args.surface_sha256)
        print(json.dumps({"status": "PASS", "surface_sha256": args.surface_sha256}))
        return 0
    if args.command == "preflight":
        if not args.operator_authorized:
            raise SystemExit("PREFLIGHT_BLOCKED")
        manifest = json.loads(LOCK.read_text())
        verify_manifest(ROOT, manifest, args.surface_sha256)
        result = preflight_environment(
            root=ROOT, implementation_sha=args.implementation_sha,
            receipt_path=args.private_receipt, profile_path=PROFILE,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "mapping-engineering":
        if not args.operator_authorized:
            raise SystemExit("MAPPING_ENGINEERING_BLOCKED")
        if _RUN_ID.fullmatch(args.run_id) is None:
            raise SystemExit("RUN_ID_INVALID")
        binding_value = os.environ.get("M4C_SS_TARGET_BINDING")
        private_value = os.environ.get("M4C_SS_PRIVATE_RUNS")
        core_sha = os.environ.get("M4C_SS_ENGINEERING_CORE_SHA")
        if not binding_value or not private_value or not core_sha:
            raise SystemExit("PRIVATE_ENVIRONMENT_MISSING")
        binding_path = Path(binding_value)
        private_root = Path(private_value)
        if (
            not private_root.is_absolute()
            or private_root.is_symlink()
            or not private_root.is_dir()
        ):
            raise SystemExit("PRIVATE_ROOT_INVALID")
        profile = json.loads(PROFILE.read_text())
        capture_device = profile["acoustic_measurement"]["capture_device"]
        events: list[dict[str, object]] = []

        def observe(name: str, stamp: int) -> None:
            events.append({"event": name, "monotonic_ns": stamp})

        def first_audio_write() -> int | None:
            return next(
                (int(item["monotonic_ns"]) for item in events
                 if item["event"] == "audio_first_write"),
                None,
            )

        backend = materialize_core_backend(
            load_target_binding(binding_path, expected_core_sha=core_sha),
            observe=observe,
        )
        case_name = f"{args.trace_id}-{args.candidate}-R{args.repetition}"
        result = asyncio.run(run_acoustic_mapping_trace(
            trace_id=args.trace_id,
            candidate=args.candidate,
            backend=backend,
            capture=make_usb_capture(capture_device),
            private_pcm_path=private_root / args.run_id / "mapping" / f"{case_name}.pcm",
            onset_not_before=first_audio_write,
        ))
        value = {
            "status": f"ENGINEERING_{result.status}_NOT_FORMAL",
            "case_id": args.trace_id,
            "candidate": args.candidate,
            "repetition": args.repetition,
            "mapping": asdict(result.mapping),
            "acoustic": asdict(result.acoustic),
            "private_bundle": {
                "bytes": result.private_pcm_bytes,
                "sha256": result.private_pcm_sha256,
            },
            "capture_owner_stopped": result.capture_owner_stopped,
            "events": sorted(events, key=lambda item: int(item["monotonic_ns"])),
        }
        print(json.dumps(value, sort_keys=True))
        return 0 if result.status == "PASS" else 2
    if args.command == "calibrate":
        if not args.operator_authorized:
            raise SystemExit("CALIBRATION_BLOCKED")
        profile = json.loads(PROFILE.read_text())
        acoustic = profile["acoustic_measurement"]
        result = run_duplex_calibration(
            capture_device=acoustic["capture_device"],
            playback_device=acoustic["playback_device"],
        )
        print(json.dumps({
            "status": "PASS" if result.uncertainty_within_limit else "INCONCLUSIVE",
            "capture_rate_hz": result.capture_rate_hz,
            "capture_channels": result.capture_channels,
            "capture_format": result.capture_format,
            "capture_period_frames": result.capture_period_frames,
            "baseline_rms": result.baseline_rms,
            "threshold_rms": result.threshold_rms,
            "onset_rms": result.onset_rms,
            "maximum_clock_residual_ns": result.maximum_clock_residual_ns,
            "detector_error_ns": result.detector_error_ns,
            "uncertainty_ns": result.uncertainty_ns,
            "capture_owner_stopped": result.capture_owner_stopped,
            "playback_owner_stopped": result.playback_owner_stopped,
        }, sort_keys=True))
        return 0 if result.uncertainty_within_limit else 2
    result = asyncio.run(run_controller_case(args.case_id))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
