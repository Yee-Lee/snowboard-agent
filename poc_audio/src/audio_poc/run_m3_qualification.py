"""Validate the M3 packet and run artifact-independent local lifecycle checks."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .m3_authorization import load_signoff, validate_formal_authorization
from .m3_packet import load_packet, validate_repo_inputs
from .m4a_conformance import ConformanceScenario, M4aFakeConformanceHarness
from .models import TerminalStatus
from .validation import GIT_SHA_RE, validate_m4a_conformance_result


FAKE_SCENARIOS = (
    (ConformanceScenario("start-stop", "asr", "success", 0.3), TerminalStatus.SUCCESS),
    *(tuple(
        (ConformanceScenario(f"reopen-{index}", "tts", "success", 0.3), TerminalStatus.SUCCESS)
        for index in range(1, 6)
    )),
    (ConformanceScenario("invalid-input", "asr", "error", 0.3), TerminalStatus.ERROR),
    (ConformanceScenario("invalid-output", "tts", "error", 0.3), TerminalStatus.ERROR),
    (ConformanceScenario("cancel-asr", "asr", "cancelable", 0.3, 0.02), TerminalStatus.CANCELLED),
    (ConformanceScenario("cancel-tts", "tts", "cancelable", 0.3, 0.02), TerminalStatus.CANCELLED),
    (ConformanceScenario("force-abort", "asr", "stubborn", 0.05), TerminalStatus.FORCE_ABORTED),
)


async def run_fake_lifecycle(source_sha: str) -> list[dict[str, Any]]:
    harness = M4aFakeConformanceHarness(source_sha)
    results: list[dict[str, Any]] = []
    for scenario, expected in FAKE_SCENARIOS:
        result = (await harness.run(scenario)).to_dict()
        validate_m4a_conformance_result(result)
        if result["terminal_status"] != expected.value:
            raise RuntimeError(f"unexpected terminal status for {scenario.name}")
        if not result["cleanup"]["clean"]:
            raise RuntimeError(f"cleanup failed for {scenario.name}")
        results.append(result)
    return results


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("mode", choices=("validate", "authorize", "fake-lifecycle"))
    root.add_argument("--packet", type=Path, required=True)
    root.add_argument("--repo-root", type=Path, required=True)
    root.add_argument("--source-sha")
    root.add_argument("--output", type=Path)
    root.add_argument("--signoff", type=Path)
    root.add_argument("--core-root", type=Path)
    return root


def main() -> int:
    args = parser().parse_args()
    packet = load_packet(args.packet)
    validate_repo_inputs(packet, args.repo_root)
    if args.mode == "validate":
        print(json.dumps({
            "packet_id": packet["packet_id"],
            "status": packet["status"],
            "formal_execution_authorized": False,
            "validation": "PASS",
        }, sort_keys=True))
        return 0
    if args.mode == "authorize":
        if args.signoff is None or args.core_root is None:
            raise ValueError("authorize requires --signoff and --core-root")
        signoff = load_signoff(args.signoff)
        validate_formal_authorization(
            signoff,
            args.packet,
            args.repo_root,
            args.core_root,
        )
        print(json.dumps({
            "packet_id": packet["packet_id"],
            "poc_execution_sha": signoff["poc_execution_sha"],
            "core_execution_sha": signoff["core_execution_sha"],
            "authorization": "PASS",
        }, sort_keys=True))
        return 0
    if not args.source_sha or not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("fake-lifecycle requires a full --source-sha")
    if args.output is None or args.output.exists():
        raise ValueError("fake-lifecycle --output must be a new path")
    results = asyncio.run(run_fake_lifecycle(args.source_sha))
    document = {
        "schema_version": "1.0",
        "report_id": "M3-LOCAL-FAKE-LIFECYCLE-001",
        "packet_id": packet["packet_id"],
        "source_sha": args.source_sha,
        "scope": "LOCAL_FAKE_ONLY_NOT_HARDWARE_EVIDENCE",
        "formal_execution_authorized": False,
        "result_count": len(results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result_count": len(results), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
