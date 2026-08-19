#!/usr/bin/env python3
"""Validate frozen Gate 2A/2B case plans without executing hardware tests."""

from __future__ import annotations

import argparse
import json


CASE_SETS = {
    "2A": {"P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P10A", "P11", "P12"},
    "2B": {"P1", "P2", "P3", "P4-HOT", "P5", "P7", "P8", "P9", "P10B", "P11", "P12"},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", choices=("2A", "2B"), required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--source-packet-id")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-namespace")
    args = parser.parse_args()
    if (
        (args.source_packet_id and args.source_packet_id.startswith("G1-"))
        or (args.run_id and args.run_id.startswith("G1-"))
        or (args.evidence_namespace and "gate1" in args.evidence_namespace.lower())
    ):
        print(json.dumps({
            "gate": args.gate, "result": "FAIL", "reason": "Gate 1 evidence carry-over is forbidden",
        }, sort_keys=True))
        return 1
    cases = set(args.cases.split(","))
    unknown = sorted(cases - CASE_SETS[args.gate])
    missing = sorted(CASE_SETS[args.gate] - cases)
    if unknown or missing:
        print(json.dumps({"gate": args.gate, "result": "FAIL", "unknown": unknown, "missing": missing}, sort_keys=True))
        return 1
    if not args.plan_only:
        print(json.dumps({"gate": args.gate, "result": "Blocked", "reason": "hardware adapter and authorization are not bound"}))
        return 3
    print(json.dumps({"cases": sorted(cases), "execution_performed": False, "gate": args.gate, "result": "PLAN_VALID"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
