#!/usr/bin/env python3
"""Authenticate both-platform evidence and apply the frozen max-two finalist rule."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import jsonschema


PACKET_ID = "G1-UBUNTU-PRESCREEN-003"
ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = {"ubuntu-x86_64", "ubuntu-aarch64"}
HARD_GATES = ("P1", "P2", "P3", "P5", "P8", "P11")
STABLE_IDENTITIES = (
    "lock_sha256", "manifest_sha256", "runtime_sha256", "model_sha256", "config_sha256",
    "catalog_sha256", "candidate_schema_sha256", "validator_sha256", "runner_sha256",
    "result_schema_sha256", "selection_schema_sha256", "selector_sha256",
)
FIXED_IDENTITY_KEYS = {
    "catalog_sha256": "catalog", "candidate_schema_sha256": "candidate_schema",
    "validator_sha256": "validator", "runner_sha256": "runner",
    "result_schema_sha256": "result_schema", "selection_schema_sha256": "selection_schema",
    "selector_sha256": "selector",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_digest(argv: list[str]) -> str:
    encoded = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=0.001)


def locked_context(lock_path: Path) -> dict[str, Any]:
    lock = load(lock_path)
    paths: dict[str, Path] = {}
    for key, item in lock["artifacts"].items():
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != item["sha256"]:
            raise ValueError(f"locked artifact mismatch: {key}")
        paths[key] = path
    validator_spec = importlib.util.spec_from_file_location("gate1_selector_validator", paths["validator"])
    validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator)
    return {
        "lock": lock,
        "lock_sha256": digest(lock_path),
        "catalog": load(paths["catalog"]),
        "candidate_schema": load(paths["candidate_schema"]),
        "result_schema": load(paths["result_schema"]),
        "selection_schema": load(paths["selection_schema"]),
        "validator": validator,
    }


def load_manifests(paths: list[Path], schema: dict[str, Any]) -> dict[tuple[str, str], tuple[dict[str, Any], str]]:
    manifests: dict[tuple[str, str], tuple[dict[str, Any], str]] = {}
    for path in paths:
        manifest = load(path)
        jsonschema.validate(manifest, schema)
        for artifact_key in ("runtime", "model", "config"):
            artifact_path = (ROOT / manifest[artifact_key]["path"]).resolve()
            if (
                not artifact_path.is_relative_to(ROOT)
                or not artifact_path.is_file()
                or digest(artifact_path) != manifest[artifact_key]["sha256"]
            ):
                raise ValueError(f"candidate manifest {artifact_key} artifact mismatch")
        key = (manifest["candidate_id"], manifest["pairing_revision"])
        if key in manifests:
            raise ValueError(f"duplicate candidate manifest: {key}")
        manifests[key] = (manifest, digest(path))
    return manifests


def metrics_consistent(metrics: dict[str, Any]) -> tuple[bool, str]:
    for phase, expected_count in (("cold", 3), ("hot", 20)):
        totals = metrics[f"{phase}_total_ms"]
        ttfts = metrics[f"{phase}_ttft_ms"]
        outputs = metrics[f"{phase}_output_tokens"]
        throughputs = metrics[f"{phase}_tokens_per_second_samples"]
        if any(len(values) != expected_count for values in (totals, ttfts, outputs, throughputs)):
            return False, f"{phase} P4 sample count is incomplete"
        expected_throughputs = []
        for total_ms, ttft_ms, output_tokens in zip(totals, ttfts, outputs):
            if not all(math.isfinite(value) for value in (total_ms, ttft_ms)) or ttft_ms > total_ms + 1.0:
                return False, f"{phase} P4 timing is invalid or inconsistent"
            expected_throughputs.append(
                round(output_tokens / (max(total_ms - ttft_ms, 0.001) / 1000), 3)
            )
        if any(not close(actual, expected) for actual, expected in zip(throughputs, expected_throughputs)):
            return False, f"{phase} P4 throughput samples are inconsistent"
        summaries = {
            f"{phase}_total_ms_p50": percentile(totals, 0.50),
            f"{phase}_total_ms_p95": percentile(totals, 0.95),
            f"{phase}_ttft_ms_p50": percentile(ttfts, 0.50),
            f"{phase}_ttft_ms_p95": percentile(ttfts, 0.95),
            f"{phase}_tokens_per_second_p50": percentile(throughputs, 0.50),
            f"{phase}_tokens_per_second_p95": percentile(throughputs, 0.95),
        }
        if any(not close(metrics[key], value) for key, value in summaries.items()):
            return False, f"{phase} P4 P50/P95 aggregate is inconsistent"
    return True, "consistent"


def eligibility(
    group: dict[str, dict[str, Any]],
    context: dict[str, Any],
    manifest_record: tuple[dict[str, Any], str] | None,
) -> tuple[bool, str]:
    if set(group) != PLATFORMS:
        return False, "both x86_64 and aarch64 evidence are required"
    if manifest_record is None:
        return False, "matching candidate manifest is required"
    manifest, manifest_sha256 = manifest_record
    values = list(group.values())
    baseline = values[0]["identity"]
    if any(value == "UNAVAILABLE" for value in baseline.values()):
        return False, "eligible evidence cannot contain unavailable identity"
    for value in values[1:]:
        if any(value["identity"][key] != baseline[key] for key in STABLE_IDENTITIES):
            return False, "cross-platform immutable identity mismatch"
    if baseline["lock_sha256"] != context["lock_sha256"]:
        return False, "result lock identity does not match loaded lock"
    for identity_key, artifact_key in FIXED_IDENTITY_KEYS.items():
        if baseline[identity_key] != context["lock"]["artifacts"][artifact_key]["sha256"]:
            return False, f"result {identity_key} does not match loaded lock"
    if baseline["manifest_sha256"] != manifest_sha256:
        return False, "result manifest identity does not match supplied manifest"
    for artifact_key in ("runtime", "model", "config"):
        if baseline[f"{artifact_key}_sha256"] != manifest[artifact_key]["sha256"]:
            return False, f"result {artifact_key} identity does not match supplied manifest"

    expected_cases = {
        (case["fixture_id"], repetition)
        for case in context["catalog"]["cases"]
        for repetition in range(1, context["catalog"]["repetitions"] + 1)
    }
    for value in values:
        identity = value["identity"]
        command = manifest["commands"][value["platform"]]
        if command_digest(command["argv"]) != command["sha256"] or identity["command_sha256"] != command["sha256"]:
            return False, f'{value["platform"]} command identity does not match supplied manifest'
        if value["result"] not in {"PASS", "Core threshold decision required"}:
            return False, f'{value["platform"]} result is {value["result"]}'
        if any(value["gates"][gate] != "PASS" for gate in HARD_GATES):
            return False, f'{value["platform"]} mandatory portable gate is incomplete'
        if value["gates"]["P6"] not in {"PASS", "Conditional escalation"}:
            return False, f'{value["platform"]} P6 is not eligible'
        observed_cases = {(case["fixture_id"], case["repetition"]) for case in value["cases"]}
        if len(value["cases"]) != len(observed_cases) or observed_cases != expected_cases:
            return False, f'{value["platform"]} fixture/repetition matrix does not match locked catalog'
        if context["validator"].validate(context["catalog"], {"runs": value["cases"]}):
            return False, f'{value["platform"]} fixture results fail the locked validator'
        if any(case["log_forbidden_hits"] for case in value["cases"]):
            return False, f'{value["platform"]} contains a case-level log hygiene violation'
        hygiene = value["log_hygiene"]
        if (
            hygiene["scanner_version"] != context["catalog"]["log_hygiene"]["scanner_version"]
            or hygiene["stderr_sha256"] == "UNAVAILABLE"
            or hygiene["forbidden_sentinel_ids"]
            or hygiene["candidate_claims_ignored"] is not True
        ):
            return False, f'{value["platform"]} runner-owned log hygiene proof is invalid'
        consistent, reason = metrics_consistent(value["metrics"])
        if not consistent:
            return False, f'{value["platform"]} {reason}'
        threshold_missed = (
            value["metrics"]["hot_ttft_ms_p95"] > 2500
            or value["metrics"]["hot_tokens_per_second_p50"] < 4
        )
        expected_p4 = "Core threshold decision required" if threshold_missed else "PASS"
        if value["gates"]["P4"] != expected_p4 or value["result"] != expected_p4:
            return False, f'{value["platform"]} P4/result disposition is inconsistent'
        if value["violations"]:
            return False, f'{value["platform"]} contains violations'
        if value["cleanup"] != {
            "exit_code": 0, "waited": True, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        }:
            return False, f'{value["platform"]} exit/cleanup proof is incomplete'
    return True, "eligible"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--candidate-manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    try:
        context = locked_context(args.lock)
        manifests = load_manifests(args.candidate_manifests, context["candidate_schema"])
        grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        duplicates: set[tuple[str, str]] = set()
        for path in args.results:
            value = load(path)
            jsonschema.validate(value, context["result_schema"])
            key = (value["candidate_id"], value["pairing_revision"])
            if value["platform"] in grouped.setdefault(key, {}):
                duplicates.add(key)
            grouped[key][value["platform"]] = value

        ranked: list[tuple[int, float, float, str, str, str]] = []
        rejected = []
        for key, group in grouped.items():
            eligible, reason = eligibility(group, context, manifests.get(key))
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
            "packet_id": PACKET_ID, "result": aggregate_result, "proposed_finalists": selected,
            "rejected_pairings": sorted(rejected, key=lambda item: (item["candidate_id"], item["pairing_revision"])),
            "candidate_evidence_count": len(args.results), "max_two_enforced": len(selected) <= 2,
            "violations": [],
        }
        jsonschema.validate(output, context["selection_schema"])
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
