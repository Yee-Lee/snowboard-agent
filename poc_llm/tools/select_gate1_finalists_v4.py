#!/usr/bin/env python3
"""Fail-closed x86 preselection followed by a non-backfilling Pi eligibility filter."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import jsonschema


PACKET_ID = "G1-X86-PI-COMPAT-004"
ROOT = Path(__file__).resolve().parents[2]
HARD_GATES = ("P1", "P2", "P3", "P5", "P8", "P11")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_digest(argv: list[str]) -> str:
    value = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def resolve_artifact(item: dict[str, Any], label: str) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != item["sha256"]:
        raise ValueError(f"{label} artifact identity mismatch")
    return path


def locked_context(lock_path: Path) -> dict[str, Any]:
    lock = load(lock_path)
    paths = {key: resolve_artifact(item, f"locked {key}") for key, item in lock["artifacts"].items()}
    validator_spec = importlib.util.spec_from_file_location("gate1_validator_v4", paths["validator"])
    if validator_spec is None or validator_spec.loader is None:
        raise ValueError("locked validator cannot be loaded")
    validator = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator)
    return {
        "lock":lock, "paths":paths, "lock_sha256":digest(lock_path),
        "catalog":load(paths["catalog"]), "candidate_schema":load(paths["candidate_schema"]),
        "acquisition_schema":load(paths["acquisition_schema"]),
        "x86_schema":load(paths["x86_result_schema"]), "pi_schema":load(paths["pi_result_schema"]),
        "selection_schema":load(paths["selection_schema"]), "validator":validator,
    }


def load_manifests(
    manifest_paths: list[Path], context: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for path in manifest_paths:
        manifest = load(path)
        jsonschema.validate(manifest, context["candidate_schema"])
        acquisition_path = resolve_artifact(manifest["acquisition_manifest"], "acquisition manifest")
        acquisition = load(acquisition_path)
        jsonschema.validate(acquisition, context["acquisition_schema"])
        key = (manifest["candidate_id"], manifest["pairing_revision"])
        if key in records:
            raise ValueError(f"duplicate candidate manifest: {key}")
        if (
            acquisition["candidate_id"] != key[0]
            or acquisition["pairing_revision"] != key[1]
            or acquisition["logical_runtime"] != manifest["logical_runtime"]
        ):
            raise ValueError("candidate/acquisition logical identity mismatch")
        resolve_artifact(manifest["model"], "model")
        resolve_artifact(manifest["config"], "config")
        for platform_id, native in acquisition["platforms"].items():
            resolve_artifact(native["runtime_artifact"], f"{platform_id} runtime")
            resolve_artifact(native["dependency_bundle"], f"{platform_id} dependency bundle")
            if command_digest(native["install_argv"]) != native["install_argv_sha256"]:
                raise ValueError(f"{platform_id} install command identity mismatch")
        for command in manifest["commands"].values():
            if command_digest(command["argv"]) != command["sha256"]:
                raise ValueError("candidate command identity mismatch")
        if manifest["runtime"]["path"] != acquisition["platforms"]["ubuntu-x86_64"]["runtime_artifact"]["path"]:
            raise ValueError("candidate x86 runtime path mismatch")
        records[key] = {
            "manifest":manifest, "manifest_sha256":digest(path),
            "acquisition":acquisition, "acquisition_sha256":digest(acquisition_path),
        }
    return records


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=0.001)


def metrics_consistent(metrics: dict[str, Any]) -> tuple[bool, str]:
    for phase, count in (("cold", 3), ("hot", 20)):
        totals, ttfts = metrics[f"{phase}_total_ms"], metrics[f"{phase}_ttft_ms"]
        outputs, throughputs = metrics[f"{phase}_output_tokens"], metrics[f"{phase}_tokens_per_second_samples"]
        if any(len(values) != count for values in (totals, ttfts, outputs, throughputs)):
            return False, f"{phase} P4 sample count is incomplete"
        expected = []
        for total, ttft, output in zip(totals, ttfts, outputs):
            if not math.isfinite(total) or not math.isfinite(ttft) or ttft > total + 1.0:
                return False, f"{phase} P4 timing is invalid"
            expected.append(round(output / (max(total - ttft, 0.001) / 1000), 3))
        if any(not close(actual, wanted) for actual, wanted in zip(throughputs, expected)):
            return False, f"{phase} P4 throughput is inconsistent"
        for suffix, values in (("total_ms", totals), ("ttft_ms", ttfts), ("tokens_per_second", throughputs)):
            if not close(metrics[f"{phase}_{suffix}_p50"], percentile(values, 0.50)):
                return False, f"{phase} P4 p50 is inconsistent"
            if not close(metrics[f"{phase}_{suffix}_p95"], percentile(values, 0.95)):
                return False, f"{phase} P4 p95 is inconsistent"
    return True, "eligible"


def x86_eligibility(
    value: dict[str, Any], context: dict[str, Any], record: dict[str, Any] | None,
) -> tuple[bool, str]:
    if record is None:
        return False, "matching candidate manifest is required"
    manifest, acquisition = record["manifest"], record["acquisition"]
    identity = value["identity"]
    if any(item == "UNAVAILABLE" for item in identity.values()):
        return False, "eligible x86 evidence cannot contain unavailable identity"
    fixed = {
        "lock_sha256":context["lock_sha256"], "manifest_sha256":record["manifest_sha256"],
        "acquisition_manifest_sha256":record["acquisition_sha256"],
        "command_sha256":manifest["commands"]["ubuntu-x86_64"]["sha256"],
        "logical_runtime_source_sha256":manifest["logical_runtime"]["source_sha256"],
        "runtime_sha256":acquisition["platforms"]["ubuntu-x86_64"]["runtime_artifact"]["sha256"],
        "dependency_bundle_sha256":acquisition["platforms"]["ubuntu-x86_64"]["dependency_bundle"]["sha256"],
        "model_sha256":manifest["model"]["sha256"], "config_sha256":manifest["config"]["sha256"],
        "catalog_sha256":context["lock"]["artifacts"]["catalog"]["sha256"],
        "candidate_schema_sha256":context["lock"]["artifacts"]["candidate_schema"]["sha256"],
        "acquisition_schema_sha256":context["lock"]["artifacts"]["acquisition_schema"]["sha256"],
        "validator_sha256":context["lock"]["artifacts"]["validator"]["sha256"],
        "runner_sha256":context["lock"]["artifacts"]["runner"]["sha256"],
        "runner_core_sha256":context["lock"]["artifacts"]["runner_core"]["sha256"],
        "result_schema_sha256":context["lock"]["artifacts"]["result_schema"]["sha256"],
        "x86_result_schema_sha256":context["lock"]["artifacts"]["x86_result_schema"]["sha256"],
        "pi_result_schema_sha256":context["lock"]["artifacts"]["pi_result_schema"]["sha256"],
        "selection_schema_sha256":context["lock"]["artifacts"]["selection_schema"]["sha256"],
        "selector_sha256":context["lock"]["artifacts"]["selector"]["sha256"],
    }
    for key, expected in fixed.items():
        if identity.get(key) != expected:
            return False, f"x86 {key} identity mismatch"
    if value["result"] not in {"PASS", "Core threshold decision required"}:
        return False, f"x86 result is {value['result']}"
    if any(value["gates"].get(gate) != "PASS" for gate in HARD_GATES):
        return False, "x86 mandatory portable gate is incomplete"
    if value["gates"].get("P6") not in {"PASS", "Conditional escalation"}:
        return False, "x86 P6 is not eligible"
    expected_cases = {
        (case["fixture_id"], repetition)
        for case in context["catalog"]["cases"]
        for repetition in range(1, context["catalog"]["repetitions"] + 1)
    }
    observed = {(case["fixture_id"], case["repetition"]) for case in value["cases"]}
    if len(value["cases"]) != len(observed) or observed != expected_cases:
        return False, "x86 fixture/repetition matrix mismatch"
    if context["validator"].validate(context["catalog"], {"runs":value["cases"]}):
        return False, "x86 fixture results fail validator"
    hygiene = value["log_hygiene"]
    if (
        hygiene.get("scanner_version") != context["catalog"]["log_hygiene"]["scanner_version"]
        or hygiene.get("stderr_sha256") in {None, "UNAVAILABLE"}
        or hygiene.get("forbidden_sentinel_ids") or hygiene.get("candidate_claims_ignored") is not True
    ):
        return False, "x86 log hygiene proof is invalid"
    consistent, reason = metrics_consistent(value["metrics"])
    if not consistent:
        return False, reason
    threshold_missed = (
        value["metrics"]["hot_ttft_ms_p95"] > 2500
        or value["metrics"]["hot_tokens_per_second_p50"] < 4
    )
    disposition = "Core threshold decision required" if threshold_missed else "PASS"
    if value["gates"].get("P4") != disposition or value["result"] != disposition:
        return False, "x86 P4/result disposition is inconsistent"
    if value["violations"] or value["cleanup"] != {
        "exit_code":0, "waited":True, "term_sent":False, "kill_sent":False,
        "process_group_absent":True,
    }:
        return False, "x86 violations or cleanup failure"
    return True, disposition


def rank_x86(
    results: list[Path], context: dict[str, Any], records: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    seen: set[tuple[str, str]] = set()
    ranked: list[tuple[int, float, float, str, str, str]] = []
    rejected: list[dict[str, str]] = []
    for path in results:
        value = load(path)
        jsonschema.validate(value, context["x86_schema"])
        key = (value["candidate_id"], value["pairing_revision"])
        if key in seen:
            raise ValueError(f"duplicate x86 evidence: {key}")
        seen.add(key)
        eligible, reason = x86_eligibility(value, context, records.get(key))
        if not eligible:
            rejected.append({"candidate_id":key[0], "pairing_revision":key[1], "reason":reason})
            continue
        ranked.append((
            value["metrics"]["peak_rss_bytes"],
            -value["metrics"]["hot_tokens_per_second_p50"],
            value["metrics"]["hot_ttft_ms_p95"], key[0], key[1], reason,
        ))
    for key in records.keys() - seen:
        rejected.append({"candidate_id":key[0], "pairing_revision":key[1], "reason":"missing x86 evidence"})
    ranked.sort()
    selected = [
        {"candidate_id":item[3], "pairing_revision":item[4], "disposition":item[5]}
        for item in ranked[:2]
    ]
    return selected, rejected


def base_output(args: argparse.Namespace, selected: list[dict[str, Any]], rejected: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "packet_id":PACKET_ID, "selection_cycle_id":args.selection_cycle_id,
        "stage":"PRESELECTION" if args.stage == "preselect" else "FINAL",
        "result":"PRESELECTED", "preselected_candidates":selected, "proposed_finalists":[],
        "rejected_pairings":sorted(rejected, key=lambda item:(item["candidate_id"], item["pairing_revision"])),
        "x86_evidence_count":len(args.x86_results), "pi_evidence_count":len(args.pi_results or []),
        "max_two_enforced":True, "backfill_forbidden":True, "gate2_credit":False, "violations":[],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("preselect", "final"), required=True)
    parser.add_argument("--selection-cycle-id", required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--candidate-manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--x86-results", type=Path, nargs="+", required=True)
    parser.add_argument("--preselection", type=Path)
    parser.add_argument("--pi-results", type=Path, nargs="*")
    args = parser.parse_args()
    try:
        context = locked_context(args.lock)
        records = load_manifests(args.candidate_manifests, context)
        selected, rejected = rank_x86(args.x86_results, context, records)
        output = base_output(args, selected, rejected)
        if args.stage == "preselect":
            if args.preselection or args.pi_results:
                raise ValueError("preselection stage cannot ingest Pi evidence")
            output["result"] = "PRESELECTED" if selected else "FAIL"
        else:
            if args.preselection is None:
                raise ValueError("final stage requires immutable preselection")
            frozen = load(args.preselection)
            jsonschema.validate(frozen, context["selection_schema"])
            if (
                frozen["stage"] != "PRESELECTION"
                or frozen["selection_cycle_id"] != args.selection_cycle_id
                or frozen["preselected_candidates"] != selected
            ):
                raise ValueError("preselection drift or selection-cycle mismatch")
            selected_keys = {(item["candidate_id"], item["pairing_revision"]) for item in selected}
            pi_by_key: dict[tuple[str, str], dict[str, Any]] = {}
            for path in args.pi_results or []:
                value = load(path)
                jsonschema.validate(value, context["pi_schema"])
                key = (value["candidate_id"], value["pairing_revision"])
                if key not in selected_keys:
                    raise ValueError("Pi evidence attempts third-candidate backfill or unapproved platform")
                if key in pi_by_key:
                    raise ValueError("duplicate Pi compatibility evidence")
                record = records[key]
                native = record["acquisition"]["platforms"]["pi-debian13-aarch64"]
                fixed = {
                    "lock_sha256":context["lock_sha256"], "manifest_sha256":record["manifest_sha256"],
                    "acquisition_manifest_sha256":record["acquisition_sha256"],
                    "preselection_sha256":digest(args.preselection),
                    "command_sha256":record["manifest"]["commands"]["pi-debian13-aarch64"]["sha256"],
                    "logical_runtime_source_sha256":record["manifest"]["logical_runtime"]["source_sha256"],
                    "runtime_sha256":native["runtime_artifact"]["sha256"],
                    "dependency_bundle_sha256":native["dependency_bundle"]["sha256"],
                    "model_sha256":record["manifest"]["model"]["sha256"],
                    "config_sha256":record["manifest"]["config"]["sha256"],
                    "pi_result_schema_sha256":context["lock"]["artifacts"]["pi_result_schema"]["sha256"],
                    "runner_sha256":context["lock"]["artifacts"]["pi_runner"]["sha256"],
                }
                if value["selection_cycle_id"] != args.selection_cycle_id:
                    raise ValueError("Pi selection-cycle mismatch")
                for identity, expected in fixed.items():
                    if value["identity"].get(identity) != expected:
                        raise ValueError(f"Pi {identity} identity mismatch")
                if value["cleanup"]["process_group_absent"] is not True or value["cleanup"]["isolated_environment_removed"] is not True:
                    raise ValueError("Pi cleanup/orphan proof is incomplete")
                pi_by_key[key] = value
            finalists = []
            inconclusive = False
            for item in selected:
                key = (item["candidate_id"], item["pairing_revision"])
                value = pi_by_key.get(key)
                if value is not None and value["result"] == "PASS":
                    finalists.append(item)
                else:
                    reason = "missing Pi compatibility evidence" if value is None else f"Pi compatibility {value['result']}"
                    rejected.append({"candidate_id":key[0], "pairing_revision":key[1], "reason":reason})
                    inconclusive = inconclusive or value is None or value["result"] == "INCONCLUSIVE"
            output["proposed_finalists"] = finalists
            output["rejected_pairings"] = sorted(rejected, key=lambda item:(item["candidate_id"], item["pairing_revision"]))
            output["result"] = (
                "Core threshold decision required"
                if finalists and any(item["disposition"] == "Core threshold decision required" for item in finalists)
                else ("PASS" if finalists else ("INCONCLUSIVE" if inconclusive else "FAIL"))
            )
        jsonschema.validate(output, context["selection_schema"])
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0 if output["result"] in {"PRESELECTED", "PASS", "Core threshold decision required"} else 1
    except (json.JSONDecodeError, jsonschema.ValidationError, OSError, KeyError, TypeError, ValueError) as error:
        output = {
            "packet_id":PACKET_ID, "selection_cycle_id":args.selection_cycle_id,
            "stage":"PRESELECTION" if args.stage == "preselect" else "FINAL", "result":"INCONCLUSIVE",
            "preselected_candidates":[], "proposed_finalists":[], "rejected_pairings":[],
            "x86_evidence_count":len(args.x86_results), "pi_evidence_count":len(args.pi_results or []),
            "max_two_enforced":True, "backfill_forbidden":True, "gate2_credit":False,
            "violations":[str(error)],
        }
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
