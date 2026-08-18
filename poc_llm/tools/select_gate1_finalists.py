#!/usr/bin/env python3
"""Aggregate both platforms and apply the frozen max-two finalist rule."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema


PACKET_ID = "G1-UBUNTU-PRESCREEN-002"
ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = {"ubuntu-x86_64", "ubuntu-aarch64"}
HARD_GATES = ("P1", "P2", "P3", "P5", "P8", "P11")
STABLE_IDENTITIES = (
    "lock_sha256", "manifest_sha256", "runtime_sha256", "model_sha256", "config_sha256",
    "catalog_sha256", "candidate_schema_sha256", "validator_sha256", "runner_sha256",
    "result_schema_sha256", "selection_schema_sha256", "selector_sha256",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locked_schemas(lock_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    lock = load(lock_path)
    paths: dict[str, Path] = {}
    for key, item in lock["artifacts"].items():
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != item["sha256"]:
            raise ValueError(f"locked artifact mismatch: {key}")
        paths[key] = path
    return load(paths["result_schema"]), load(paths["selection_schema"])


def eligibility(group: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    if set(group) != PLATFORMS:
        return False, "both x86_64 and aarch64 evidence are required"
    values = list(group.values())
    baseline = values[0]["identity"]
    for value in values[1:]:
        if any(value["identity"][key] != baseline[key] for key in STABLE_IDENTITIES):
            return False, "cross-platform immutable identity mismatch"
    for value in values:
        if value["result"] not in {"PASS", "Core threshold decision required"}:
            return False, f'{value["platform"]} result is {value["result"]}'
        if any(value["gates"][gate] != "PASS" for gate in HARD_GATES):
            return False, f'{value["platform"]} mandatory portable gate is incomplete'
        if value["gates"]["P6"] not in {"PASS", "Conditional escalation"}:
            return False, f'{value["platform"]} P6 is not eligible'
        if len(value["cases"]) != 60:
            return False, f'{value["platform"]} does not contain the exact 60-case matrix'
        metrics = value["metrics"]
        if len(metrics["cold_total_ms"]) != 3 or any(
            len(metrics[key]) != 20
            for key in ("hot_total_ms", "ttft_ms", "output_tokens", "hot_tokens_per_second_samples")
        ):
            return False, f'{value["platform"]} P4 sample matrix is incomplete'
        if value["violations"]:
            return False, f'{value["platform"]} contains violations'
        cleanup = value["cleanup"]
        if cleanup != {"exit_code": 0, "waited": True, "process_group_absent": True}:
            return False, f'{value["platform"]} exit/cleanup proof is incomplete'
    return True, "eligible"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    try:
        result_schema, selection_schema = locked_schemas(args.lock)
        grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        duplicates: set[tuple[str, str]] = set()
        for path in args.results:
            value = load(path)
            jsonschema.validate(value, result_schema)
            key = (value["candidate_id"], value["pairing_revision"])
            if value["platform"] in grouped.setdefault(key, {}):
                duplicates.add(key)
            grouped[key][value["platform"]] = value

        ranked: list[tuple[int, float, float, str, str, str]] = []
        rejected = []
        for key, group in grouped.items():
            eligible, reason = eligibility(group)
            if key in duplicates:
                eligible, reason = False, "duplicate evidence for the same platform"
            if not eligible:
                rejected.append({"candidate_id": key[0], "pairing_revision": key[1], "reason": reason})
                continue
            values = list(group.values())
            disposition = (
                "Core threshold decision required"
                if any(value["gates"]["P4"] != "PASS" for value in values)
                else "PASS"
            )
            ranked.append((
                max(value["metrics"]["peak_rss_bytes"] for value in values),
                -min(value["metrics"]["hot_tokens_per_second_p50"] for value in values),
                max(value["metrics"]["hot_ttft_ms_p95"] for value in values),
                key[0], key[1], disposition,
            ))
        ranked.sort()
        selected = [
            {"candidate_id": item[3], "pairing_revision": item[4], "disposition": item[5]}
            for item in ranked[:2]
        ]
        aggregate_result = (
            "Core threshold decision required"
            if selected and any(item["disposition"] == "Core threshold decision required" for item in selected)
            else ("PASS" if selected else "FAIL")
        )
        output = {
            "packet_id": PACKET_ID,
            "result": aggregate_result,
            "proposed_finalists": selected,
            "rejected_pairings": sorted(rejected, key=lambda item: (item["candidate_id"], item["pairing_revision"])),
            "candidate_evidence_count": len(args.results),
            "max_two_enforced": len(selected) <= 2,
            "violations": [],
        }
        jsonschema.validate(output, selection_schema)
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0 if selected else 1
    except (json.JSONDecodeError, jsonschema.ValidationError, OSError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({
            "packet_id": PACKET_ID, "result": "INCONCLUSIVE", "proposed_finalists": [],
            "rejected_pairings": [], "candidate_evidence_count": len(args.results),
            "max_two_enforced": True, "violations": [str(error)],
        }, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
