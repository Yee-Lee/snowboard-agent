"""Workstation entrypoint for the M4C-SS plan and deterministic cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from poc_llm.m4c_ss.deterministic import run_controller_case
from poc_llm.m4c_ss.plan import CONTROLLER_CASES, build_plan, case_key
from poc_llm.m4c_ss.preflight import preflight_environment
from poc_llm.m4c_ss.surface import build_manifest, surface_digest, verify_manifest


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "poc_llm/contracts/m4c_ss/m4c-ss-profile-001.json"
LOCK = ROOT / "poc_llm/m4c_ss/m4c-ss-surface-lock-v1.json"


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
    result = asyncio.run(run_controller_case(args.case_id))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
