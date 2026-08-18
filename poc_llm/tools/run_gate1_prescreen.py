#!/usr/bin/env python3
"""Fail-closed portable Gate 1 runner for one immutable candidate/platform/run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import sys
import time
from typing import Any, TextIO

import jsonschema


PACKET_ID = "G1-UBUNTU-PRESCREEN-002"
ROOT = Path(__file__).resolve().parents[2]
ARCH = {"ubuntu-x86_64": "x86_64", "ubuntu-aarch64": "aarch64"}
READY_TIMEOUT = 10.0
REQUEST_TIMEOUT = 2.0
TERM_GRACE = 2.0
GATE_IDS = ("P1", "P2", "P3", "P4", "P5", "P6", "P8", "P11")
BENCHMARK_ENVELOPE = {
    "input_ref": "public.synthetic.benchmark.fixed-v1",
    "input_tokens": 128,
    "max_output_tokens": 16,
    "temperature": 0,
}


class CandidateFailure(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_digest(argv: list[str]) -> str:
    encoded = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def locked_paths(lock: dict[str, Any]) -> dict[str, Path]:
    paths = {}
    for key, item in lock["artifacts"].items():
        path = ROOT / item["path"]
        if not path.is_file() or digest(path) != item["sha256"]:
            raise CandidateFailure(f"locked artifact mismatch: {key}")
        paths[key] = path
    return paths


def read_frame(stream: TextIO, timeout: float) -> dict[str, Any]:
    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise CandidateFailure(f"candidate frame timeout after {timeout}s")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise CandidateFailure("candidate stdout closed")
    try:
        value = json.loads(line)
    except json.JSONDecodeError as error:
        raise CandidateFailure("candidate emitted invalid JSONL") from error
    if not isinstance(value, dict):
        raise CandidateFailure("candidate frame must be an object")
    return value


def request(process: subprocess.Popen[str], frame: dict[str, Any], timeout: float = REQUEST_TIMEOUT) -> dict[str, Any]:
    if process.stdin is None or process.stdout is None:
        raise CandidateFailure("candidate pipes unavailable")
    process.stdin.write(json.dumps(frame, separators=(",", ":")) + "\n")
    process.stdin.flush()
    return read_frame(process.stdout, timeout)


def group_absent(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def stop(process: subprocess.Popen[str] | None) -> dict[str, Any]:
    if process is None:
        return {"exit_code": None, "waited": False, "process_group_absent": True}
    group_id = process.pid
    if process.poll() is None:
        try:
            os.killpg(group_id, signal.SIGTERM)
            process.wait(timeout=TERM_GRACE)
        except subprocess.TimeoutExpired:
            os.killpg(group_id, signal.SIGKILL)
            process.wait(timeout=TERM_GRACE)
        except ProcessLookupError:
            pass
    return {"exit_code": process.returncode, "waited": True, "process_group_absent": group_absent(group_id)}


def percentile95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)] if values else 0.0


def percentile50(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * 0.50) - 1)] if values else 0.0


def empty_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "packet_id": PACKET_ID, "run_id": args.run_id, "candidate_id": "UNBOUND",
        "pairing_revision": "UNBOUND", "platform": args.platform, "result": "INCONCLUSIVE",
        "identity": {key: "UNAVAILABLE" for key in (
            "lock_sha256","manifest_sha256","command_sha256","runtime_sha256","model_sha256",
            "config_sha256","catalog_sha256","candidate_schema_sha256","validator_sha256",
            "runner_sha256","result_schema_sha256","selection_schema_sha256","selector_sha256")},
        "gates": {key: "Pending" for key in GATE_IDS}, "cases": [],
        "metrics": {"cold_total_ms":[],"hot_total_ms":[],"ttft_ms":[],"output_tokens":[],
                    "hot_tokens_per_second_samples":[],"cold_total_ms_p50":0,"cold_total_ms_p95":0,
                    "hot_total_ms_p50":0,"hot_total_ms_p95":0,"hot_ttft_ms_p50":0,
                    "hot_ttft_ms_p95":0,"hot_tokens_per_second_p50":0,
                    "hot_tokens_per_second_p95":0,"peak_rss_bytes":0,"disk_bytes":0},
        "cleanup": {"exit_code":None,"waited":False,"process_group_absent":True}, "violations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=tuple(ARCH), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    report = empty_report(args)
    process: subprocess.Popen[str] | None = None
    exit_code = 2
    try:
        lock = load(args.lock)
        paths = locked_paths(lock)
        manifest = load(args.candidate_manifest)
        jsonschema.validate(manifest, load(paths["candidate_schema"]))
        report["candidate_id"] = manifest["candidate_id"]
        report["pairing_revision"] = manifest["pairing_revision"]
        if platform.machine() != ARCH[args.platform]:
            report["result"] = "INCONCLUSIVE"
            raise CandidateFailure(f"platform mismatch: expected {ARCH[args.platform]}, got {platform.machine()}")
        command = manifest["commands"][args.platform]
        argv = command["argv"]
        actual_command_sha = command_digest(argv)
        if actual_command_sha != command["sha256"]:
            raise CandidateFailure("immutable command checksum mismatch")
        artifact_hashes = {}
        disk_bytes = 0
        for key in ("runtime", "model", "config"):
            artifact_path = (ROOT / manifest[key]["path"]).resolve()
            if not artifact_path.is_relative_to(ROOT):
                raise CandidateFailure(f"{key} artifact escapes repository root")
            if not artifact_path.is_file() or digest(artifact_path) != manifest[key]["sha256"]:
                raise CandidateFailure(f"{key} artifact identity mismatch")
            artifact_hashes[key] = manifest[key]["sha256"]
            disk_bytes += artifact_path.stat().st_size
        if manifest["runtime"]["path"] not in argv:
            raise CandidateFailure("candidate command is not bound to runtime path")
        report["identity"] = {
            "lock_sha256": digest(args.lock), "manifest_sha256": digest(args.candidate_manifest),
            "command_sha256": actual_command_sha,
            "runtime_sha256": artifact_hashes["runtime"], "model_sha256": artifact_hashes["model"],
            "config_sha256": artifact_hashes["config"], "catalog_sha256": digest(paths["catalog"]),
            "candidate_schema_sha256": digest(paths["candidate_schema"]),
            "validator_sha256": digest(paths["validator"]), "runner_sha256": digest(paths["runner"]),
            "result_schema_sha256": digest(paths["result_schema"]),
            "selection_schema_sha256": digest(paths["selection_schema"]),
            "selector_sha256": digest(paths["selector"]),
        }
        report["metrics"]["disk_bytes"] = disk_bytes
        args.raw_dir.mkdir(parents=True, exist_ok=False)
        stderr_path = args.raw_dir / "candidate.stderr"
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_stream,
                text=True, start_new_session=True, cwd=ROOT,
            )
            ready = read_frame(process.stdout, READY_TIMEOUT) if process.stdout else {}
        expected_ready = {
            "type":"READY", "candidate_id":manifest["candidate_id"],
            "runtime_sha256":artifact_hashes["runtime"], "model_sha256":artifact_hashes["model"],
            "config_sha256":artifact_hashes["config"],
        }
        if any(ready.get(key) != value for key, value in expected_ready.items()):
            raise CandidateFailure("P1 READY/identity handshake failed")
        pong = request(process, {"op":"PING"})
        if pong.get("type") != "PONG":
            raise CandidateFailure("P1 framing probe failed")
        report["gates"]["P1"] = "PASS"
        report["gates"]["P11"] = "PASS"

        catalog = load(paths["catalog"])
        for case in catalog["cases"]:
            for repetition in range(1, catalog["repetitions"] + 1):
                frame = request(process, {"op":"GENERATE","fixture_id":case["fixture_id"],"repetition":repetition})
                if frame.get("type") != "RESULT":
                    raise CandidateFailure("P2/P3 candidate result frame missing")
                report["cases"].append({
                    "fixture_id":case["fixture_id"], "repetition":repetition,
                    "normalized":frame.get("normalized"), "log_forbidden_hits":frame.get("log_forbidden_hits"),
                })
        spec = importlib.util.spec_from_file_location("gate1_validator", paths["validator"])
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        validation_errors = validator.validate(catalog, {"runs":report["cases"]})
        if validation_errors:
            report["violations"].extend(validation_errors)
            raise CandidateFailure("P2/P3 validator failed")
        report["gates"]["P2"] = report["gates"]["P3"] = "PASS"

        for sequence in range(3):
            frame = request(process, {
                "op":"BENCH", "phase":"warmup", "sequence":sequence, **BENCHMARK_ENVELOPE,
            })
            if frame.get("type") != "BENCH_RESULT":
                raise CandidateFailure("P4 warmup framing failed")
        for sequence in range(3):
            started = time.monotonic()
            frame = request(process, {
                "op":"BENCH", "phase":"cold", "sequence":sequence, **BENCHMARK_ENVELOPE,
            })
            report["metrics"]["cold_total_ms"].append(round((time.monotonic()-started)*1000, 3))
            if frame.get("type") != "BENCH_RESULT":
                raise CandidateFailure("P4 cold framing failed")
        rss = []
        for sequence in range(20):
            started = time.monotonic()
            frame = request(process, {
                "op":"BENCH", "phase":"hot", "sequence":sequence, **BENCHMARK_ENVELOPE,
            })
            total_ms = (time.monotonic()-started)*1000
            if (
                frame.get("type") != "BENCH_RESULT"
                or frame.get("output_tokens", 0) <= 0
                or frame.get("output_tokens", 0) > BENCHMARK_ENVELOPE["max_output_tokens"]
            ):
                raise CandidateFailure("P4 hot measurement invalid")
            report["metrics"]["hot_total_ms"].append(round(total_ms, 3))
            report["metrics"]["ttft_ms"].append(float(frame["ttft_ms"]))
            report["metrics"]["output_tokens"].append(int(frame["output_tokens"]))
            rss.append(int(frame["rss_bytes"]))
        report["metrics"]["hot_ttft_ms_p95"] = percentile95(report["metrics"]["ttft_ms"])
        report["metrics"]["cold_total_ms_p50"] = percentile50(report["metrics"]["cold_total_ms"])
        report["metrics"]["cold_total_ms_p95"] = percentile95(report["metrics"]["cold_total_ms"])
        report["metrics"]["hot_total_ms_p50"] = percentile50(report["metrics"]["hot_total_ms"])
        report["metrics"]["hot_total_ms_p95"] = percentile95(report["metrics"]["hot_total_ms"])
        report["metrics"]["hot_ttft_ms_p50"] = percentile50(report["metrics"]["ttft_ms"])
        report["metrics"]["hot_tokens_per_second_samples"] = [
            round(tokens / (max(elapsed_ms, 0.001) / 1000), 3)
            for tokens, elapsed_ms in zip(report["metrics"]["output_tokens"], report["metrics"]["hot_total_ms"])
        ]
        report["metrics"]["hot_tokens_per_second_p50"] = percentile50(report["metrics"]["hot_tokens_per_second_samples"])
        report["metrics"]["hot_tokens_per_second_p95"] = percentile95(report["metrics"]["hot_tokens_per_second_samples"])
        report["metrics"]["peak_rss_bytes"] = max(rss)
        report["gates"]["P4"] = "PASS" if report["metrics"]["hot_ttft_ms_p95"] <= 2500 and report["metrics"]["hot_tokens_per_second_p50"] >= 4 else "Core threshold decision required"

        timeout_started = time.monotonic()
        timeout_frame = request(process, {"op":"TIMEOUT_PROBE", "timeout_ms":15000}, 16.0)
        timeout_elapsed_ms = (time.monotonic() - timeout_started) * 1000
        if (
            timeout_frame.get("type") != "ERROR"
            or timeout_frame.get("code") != "TIMEOUT"
            or timeout_frame.get("state") != "READY"
            or not 14500 <= timeout_elapsed_ms <= 16000
        ):
            raise CandidateFailure("P5 bounded timeout failed")
        if request(process, {"op":"PING"}).get("type") != "PONG":
            raise CandidateFailure("P5 candidate did not recover READY")
        report["gates"]["P5"] = "PASS"
        cancel_start = request(process, {"op":"START_CANCEL_PROBE", "operation_id":"gate1-cancel", "work_ms":5000})
        if cancel_start.get("type") == "ERROR" and cancel_start.get("code") == "UNSUPPORTED_CANCEL":
            report["gates"]["P6"] = "Conditional escalation"
        elif cancel_start.get("type") != "GENERATING" or cancel_start.get("operation_id") != "gate1-cancel":
            raise CandidateFailure("P6 cancellable operation did not start")
        else:
            cancel_started = time.monotonic()
            cancel_frame = request(process, {"op":"CANCEL", "operation_id":"gate1-cancel"}, 0.5)
            cancel_elapsed_ms = (time.monotonic() - cancel_started) * 1000
            if cancel_frame.get("type") == "CANCELLED" and cancel_frame.get("operation_id") == "gate1-cancel" and cancel_frame.get("state") == "READY" and cancel_elapsed_ms <= 500:
                report["gates"]["P6"] = "PASS"
            else:
                raise CandidateFailure("P6 cancel result invalid")
        for sequence in range(5):
            marker = f"turn-{sequence}"
            frame = request(process, {"op":"HISTORY_PROBE","sequence":sequence,"current_marker":marker})
            if (
                frame.get("type") != "HISTORY_RESULT"
                or frame.get("output_marker") != marker
                or frame.get("previous_marker_present") is not False
                or frame.get("state") != "READY"
            ):
                raise CandidateFailure("P8 history isolation failed")
        report["gates"]["P8"] = "PASS"
        shutdown = request(process, {"op":"SHUTDOWN"})
        if shutdown.get("type") != "SHUTDOWN_ACK":
            raise CandidateFailure("P1 shutdown acknowledgement failed")
        process.wait(timeout=TERM_GRACE)
        report["cleanup"] = stop(process)
        if process.returncode != 0 or not report["cleanup"]["process_group_absent"]:
            raise CandidateFailure("successful-run cleanup proof failed")
        hard = ("P1","P2","P3","P5","P8","P11")
        if not all(report["gates"][key] == "PASS" for key in hard):
            raise CandidateFailure("mandatory portable gate incomplete")
        report["result"] = "Core threshold decision required" if report["gates"]["P4"] != "PASS" else "PASS"
        exit_code = 0
    except (
        CandidateFailure, jsonschema.ValidationError, OSError, subprocess.SubprocessError,
        TypeError, ValueError, KeyError,
    ) as error:
        report["violations"].append(str(error))
        if not str(error).startswith("platform mismatch:"):
            report["result"] = "FAIL"
        exit_code = 1 if report["result"] == "FAIL" else 2
    finally:
        if not report["cleanup"]["waited"]:
            report["cleanup"] = stop(process)
        try:
            if "paths" in locals():
                jsonschema.validate(report, load(paths["result_schema"]))
        except jsonschema.ValidationError as error:
            report["result"] = "INCONCLUSIVE"
            report["violations"].append(f"sanitized result schema failure: {error.message}")
            exit_code = 2
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
