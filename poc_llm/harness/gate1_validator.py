#!/usr/bin/env python3
"""Frozen P2/P3 catalog validator for the M4b Gate 1 packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


VERSION = "1.0.0"
EXACT_KEYS = {"action_kind", "action_payload", "next_perceptions"}
ALLOWED_ACTIONS = {"speak", "tool", "rest"}
ALLOWED_PERCEPTIONS = {"listen", "read", "look"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_response(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != EXACT_KEYS:
        return ["normalized response keys must exactly match the product contract"]
    kind = value["action_kind"]
    payload = value["action_payload"]
    next_perceptions = value["next_perceptions"]
    if kind not in ALLOWED_ACTIONS:
        errors.append("unknown action_kind")
    if not isinstance(next_perceptions, list):
        errors.append("next_perceptions must be a list")
        return errors
    if len(next_perceptions) != len(set(next_perceptions)):
        errors.append("next_perceptions must be deduplicated")
    if any(item not in ALLOWED_PERCEPTIONS for item in next_perceptions):
        errors.append("next_perceptions contains an unavailable capability")
    if kind == "speak":
        if (
            not isinstance(payload, dict)
            or set(payload) != {"text"}
            or not isinstance(payload.get("text"), str)
            or not payload["text"]
        ):
            errors.append("speak payload must be exactly a non-empty text")
        if not next_perceptions:
            errors.append("speak requires at least one next perception")
    elif kind == "tool":
        if not isinstance(payload, dict) or set(payload) != {"name", "arguments"}:
            errors.append("tool payload keys are invalid")
        elif not isinstance(payload["name"], str) or "." not in payload["name"]:
            errors.append("tool name must be a registered dotted name")
        elif not isinstance(payload["arguments"], dict):
            errors.append("tool arguments must be an object")
        if not next_perceptions:
            errors.append("tool requires at least one next perception")
    elif kind == "rest" and (payload != {} or next_perceptions != []):
        errors.append("rest requires empty payload and no next perceptions")
    return errors


def expected_response(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    if expected["mode"] == "fallback":
        return {
            "action_kind": "speak",
            "action_payload": {"text": "Sorry, please try again."},
            "next_perceptions": ["listen"],
        }
    kind = expected["action_kind"]
    if kind == "speak":
        payload = {"text": "Synthetic response."}
    elif kind == "tool":
        payload = {"name": expected["tool_name"], "arguments": {}}
    else:
        payload = {}
    return {
        "action_kind": kind,
        "action_payload": payload,
        "next_perceptions": expected["next_perceptions"],
    }


def self_test_input(catalog: dict[str, Any]) -> dict[str, Any]:
    runs = []
    for case in catalog["cases"]:
        for repetition in range(1, catalog["repetitions"] + 1):
            runs.append(
                {
                    "fixture_id": case["fixture_id"],
                    "repetition": repetition,
                    "normalized": expected_response(case),
                    "log_forbidden_hits": [],
                }
            )
    return {"runs": runs}


def validate(catalog: dict[str, Any], results: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = {case["fixture_id"]: case for case in catalog["cases"]}
    expected_pairs = {
        (fixture_id, repetition)
        for fixture_id in cases
        for repetition in range(1, catalog["repetitions"] + 1)
    }
    observed: set[tuple[str, int]] = set()
    for run in results.get("runs", []):
        pair = (run.get("fixture_id"), run.get("repetition"))
        if pair in observed:
            errors.append(f"duplicate run {pair}")
            continue
        observed.add(pair)
        case = cases.get(pair[0])
        if case is None:
            errors.append(f"unknown fixture {pair[0]}")
            continue
        response_errors = validate_response(run.get("normalized"))
        errors.extend(f"{pair}: {error}" for error in response_errors)
        if run.get("log_forbidden_hits") != []:
            errors.append(f"{pair}: forbidden log content detected")
        expected = case["expected"]
        normalized = run.get("normalized", {})
        if expected["mode"] == "valid":
            if normalized.get("action_kind") != expected["action_kind"]:
                errors.append(f"{pair}: action kind differs from expected result")
            if normalized.get("next_perceptions") != expected["next_perceptions"]:
                errors.append(f"{pair}: next perceptions differ from expected result")
            if expected["action_kind"] == "tool":
                if normalized.get("action_payload", {}).get("name") != expected["tool_name"]:
                    errors.append(f"{pair}: tool name differs from expected result")
        elif normalized.get("action_kind") not in {"speak", "rest"}:
            errors.append(f"{pair}: failure case did not normalize to P5 fallback")
    if observed != expected_pairs:
        errors.append("catalog coverage must be exactly 20 cases x 3 repetitions")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test == (args.results is not None):
        parser.error("choose exactly one of --self-test or --results")
    catalog = load(args.catalog)
    if catalog.get("validator_version") != VERSION:
        raise SystemExit("catalog validator version mismatch")
    results = self_test_input(catalog) if args.self_test else load(args.results)
    errors = validate(catalog, results)
    report = {
        "catalog_id": catalog["catalog_id"],
        "catalog_revision": catalog["revision"],
        "catalog_sha256": sha256(args.catalog),
        "result": "PASS" if not errors else "FAIL",
        "validator_version": VERSION,
        "violations": errors,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
