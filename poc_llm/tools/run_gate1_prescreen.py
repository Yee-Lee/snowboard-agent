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


PACKET_ID = "G1-UBUNTU-PRESCREEN-003"
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


def request(
    process: subprocess.Popen[str],
    frame: dict[str, Any],
    captured_stdout: list[str],
    timeout: float = REQUEST_TIMEOUT,
) -> dict[str, Any]:
    if process.stdin is None or process.stdout is None:
        raise CandidateFailure("candidate pipes unavailable")
    process.stdin.write(json.dumps(frame, separators=(",", ":")) + "\n")
    process.stdin.flush()
    value = read_frame(process.stdout, timeout)
    captured_stdout.append(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return value


def group_absent(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def wait_group_absent(group_id: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if group_absent(group_id):
            return True
        time.sleep(0.02)
    return group_absent(group_id)


def stop(process: subprocess.Popen[str] | None) -> dict[str, Any]:
    if process is None:
        return {
            "exit_code": None, "waited": False, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        }
    group_id = process.pid
    term_sent = False
    kill_sent = False
    process.poll()
    if not group_absent(group_id):
        try:
            os.killpg(group_id, signal.SIGTERM)
            term_sent = True
        except ProcessLookupError:
            pass
        if process.poll() is None:
            try:
                process.wait(timeout=TERM_GRACE)
            except subprocess.TimeoutExpired:
                pass
        if not wait_group_absent(group_id, TERM_GRACE):
            try:
                os.killpg(group_id, signal.SIGKILL)
                kill_sent = True
            except ProcessLookupError:
                pass
            if process.poll() is None:
                try:
                    process.wait(timeout=TERM_GRACE)
                except subprocess.TimeoutExpired:
                    pass
            wait_group_absent(group_id, TERM_GRACE)
    if process.poll() is None:
        try:
            process.wait(timeout=TERM_GRACE)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(group_id, signal.SIGKILL)
                kill_sent = True
            except ProcessLookupError:
                pass
            process.wait(timeout=TERM_GRACE)
    return {
        "exit_code": process.returncode,
        "waited": True,
        "term_sent": term_sent,
        "kill_sent": kill_sent,
        "process_group_absent": group_absent(group_id),
    }


def percentile95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)] if values else 0.0


def percentile50(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * 0.50) - 1)] if values else 0.0


def scan_log_hygiene(
    catalog: dict[str, Any], stderr_path: Path, captured_stdout: list[str],
) -> dict[str, Any]:
    rules = catalog["log_hygiene"]
    hits: set[str] = set()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    captured_text = "\n".join(captured_stdout)
    for item in rules["forbidden_patterns"]:
        needle = item["pattern"].casefold()
        if needle in stderr_text.casefold() or needle in captured_text.casefold():
            hits.add(item["id"])
    return {
        "scanner_version": rules["scanner_version"],
        "stderr_sha256": digest(stderr_path) if stderr_path.is_file() else "UNAVAILABLE",
        "stderr_bytes_scanned": stderr_path.stat().st_size if stderr_path.is_file() else 0,
        "stdout_frames_scanned": len(captured_stdout),
        "forbidden_sentinel_ids": sorted(hits),
        "candidate_claims_ignored": True,
    }


def metric_sample(frame: dict[str, Any], total_ms: float) -> tuple[float, int, float, int]:
    try:
        ttft_ms = float(frame["ttft_ms"])
        output_tokens = frame["output_tokens"]
        rss_bytes = frame["rss_bytes"]
    except (KeyError, TypeError, ValueError) as error:
        raise CandidateFailure("P4 measurement is missing, invalid, or inconsistent") from error
    if (
        frame.get("type") != "BENCH_RESULT"
        or not math.isfinite(total_ms)
        or not math.isfinite(ttft_ms)
        or ttft_ms < 0
        or ttft_ms > total_ms + 1.0
        or isinstance(output_tokens, bool)
        or not isinstance(output_tokens, int)
        or not 1 <= output_tokens <= BENCHMARK_ENVELOPE["max_output_tokens"]
        or isinstance(rss_bytes, bool)
        or not isinstance(rss_bytes, int)
        or rss_bytes < 0
    ):
        raise CandidateFailure("P4 measurement is missing, invalid, or inconsistent")
    rounded_total_ms = round(total_ms, 3)
    generation_ms = max(rounded_total_ms - ttft_ms, 0.001)
    tokens_per_second = round(output_tokens / (generation_ms / 1000), 3)
    return ttft_ms, output_tokens, tokens_per_second, rss_bytes


def empty_report(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "packet_id": PACKET_ID, "run_id": args.run_id, "candidate_id": "UNBOUND",
        "pairing_revision": "UNBOUND", "platform": args.platform, "result": "INCONCLUSIVE",
        "identity": {key: "UNAVAILABLE" for key in (
            "lock_sha256","manifest_sha256","command_sha256","runtime_sha256","model_sha256",
            "config_sha256","catalog_sha256","candidate_schema_sha256","validator_sha256",
            "runner_sha256","result_schema_sha256","selection_schema_sha256","selector_sha256")},
        "gates": {key: "Pending" for key in GATE_IDS}, "cases": [],
        "metrics": {
            "cold_total_ms":[], "cold_ttft_ms":[], "cold_output_tokens":[],
            "cold_tokens_per_second_samples":[], "hot_total_ms":[], "hot_ttft_ms":[],
            "hot_output_tokens":[], "hot_tokens_per_second_samples":[],
            "cold_total_ms_p50":0, "cold_total_ms_p95":0,
            "cold_ttft_ms_p50":0, "cold_ttft_ms_p95":0,
            "cold_tokens_per_second_p50":0, "cold_tokens_per_second_p95":0,
            "hot_total_ms_p50":0, "hot_total_ms_p95":0,
            "hot_ttft_ms_p50":0, "hot_ttft_ms_p95":0,
            "hot_tokens_per_second_p50":0, "hot_tokens_per_second_p95":0,
            "peak_rss_bytes":0, "disk_bytes":0,
        },
        "log_hygiene": {
            "scanner_version":"UNAVAILABLE", "stderr_sha256":"UNAVAILABLE",
            "stderr_bytes_scanned":0, "stdout_frames_scanned":0,
            "forbidden_sentinel_ids":[], "candidate_claims_ignored":True,
        },
        "cleanup": {
            "exit_code":None, "waited":False, "term_sent":False,
            "kill_sent":False, "process_group_absent":True,
        },
        "violations": [],
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
    captured_stdout: list[str] = []
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
            captured_stdout.append(json.dumps(ready, sort_keys=True, separators=(",", ":")))
        expected_ready = {
            "type":"READY", "candidate_id":manifest["candidate_id"],
            "runtime_sha256":artifact_hashes["runtime"], "model_sha256":artifact_hashes["model"],
            "config_sha256":artifact_hashes["config"],
        }
        if any(ready.get(key) != value for key, value in expected_ready.items()):
            raise CandidateFailure("P1 READY/identity handshake failed")
        pong = request(process, {"op":"PING"}, captured_stdout)
        if pong.get("type") != "PONG":
            raise CandidateFailure("P1 framing probe failed")
        report["gates"]["P1"] = "PASS"
        report["gates"]["P11"] = "PASS"

        catalog = load(paths["catalog"])
        for case in catalog["cases"]:
            for repetition in range(1, catalog["repetitions"] + 1):
                frame = request(
                    process,
                    {"op":"GENERATE","fixture_id":case["fixture_id"],"repetition":repetition},
                    captured_stdout,
                )
                if frame.get("type") != "RESULT":
                    raise CandidateFailure("P2/P3 candidate result frame missing")
                report["cases"].append({
                    "fixture_id":case["fixture_id"], "repetition":repetition,
                    "normalized":frame.get("normalized"), "log_forbidden_hits":[],
                })
        spec = importlib.util.spec_from_file_location("gate1_validator", paths["validator"])
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        validation_errors = validator.validate(catalog, {"runs":report["cases"]})
        if validation_errors:
            report["violations"].extend(validation_errors)
            raise CandidateFailure("P2/P3 validator failed")
        report["gates"]["P2"] = report["gates"]["P3"] = "PASS"
        report["log_hygiene"] = scan_log_hygiene(catalog, stderr_path, captured_stdout)
        if report["log_hygiene"]["forbidden_sentinel_ids"]:
            report["gates"]["P3"] = "FAIL"
            raise CandidateFailure("P3 runner-owned log hygiene detected forbidden content")

        for sequence in range(3):
            frame = request(
                process,
                {"op":"BENCH", "phase":"warmup", "sequence":sequence, **BENCHMARK_ENVELOPE},
                captured_stdout,
            )
            if frame.get("type") != "BENCH_RESULT":
                report["gates"]["P4"] = "FAIL"
                raise CandidateFailure("P4 warmup framing failed")
        rss = []
        for sequence in range(3):
            started = time.monotonic()
            frame = request(
                process,
                {"op":"BENCH", "phase":"cold", "sequence":sequence, **BENCHMARK_ENVELOPE},
                captured_stdout,
            )
            total_ms = (time.monotonic() - started) * 1000
            try:
                ttft_ms, output_tokens, tokens_per_second, rss_bytes = metric_sample(frame, total_ms)
            except CandidateFailure:
                report["gates"]["P4"] = "FAIL"
                raise
            report["metrics"]["cold_total_ms"].append(round(total_ms, 3))
            report["metrics"]["cold_ttft_ms"].append(ttft_ms)
            report["metrics"]["cold_output_tokens"].append(output_tokens)
            report["metrics"]["cold_tokens_per_second_samples"].append(tokens_per_second)
            rss.append(rss_bytes)
        for sequence in range(20):
            started = time.monotonic()
            frame = request(
                process,
                {"op":"BENCH", "phase":"hot", "sequence":sequence, **BENCHMARK_ENVELOPE},
                captured_stdout,
            )
            total_ms = (time.monotonic() - started) * 1000
            try:
                ttft_ms, output_tokens, tokens_per_second, rss_bytes = metric_sample(frame, total_ms)
            except CandidateFailure:
                report["gates"]["P4"] = "FAIL"
                raise
            report["metrics"]["hot_total_ms"].append(round(total_ms, 3))
            report["metrics"]["hot_ttft_ms"].append(ttft_ms)
            report["metrics"]["hot_output_tokens"].append(output_tokens)
            report["metrics"]["hot_tokens_per_second_samples"].append(tokens_per_second)
            rss.append(rss_bytes)
        report["metrics"]["cold_total_ms_p50"] = percentile50(report["metrics"]["cold_total_ms"])
        report["metrics"]["cold_total_ms_p95"] = percentile95(report["metrics"]["cold_total_ms"])
        report["metrics"]["cold_ttft_ms_p50"] = percentile50(report["metrics"]["cold_ttft_ms"])
        report["metrics"]["cold_ttft_ms_p95"] = percentile95(report["metrics"]["cold_ttft_ms"])
        report["metrics"]["cold_tokens_per_second_p50"] = percentile50(
            report["metrics"]["cold_tokens_per_second_samples"]
        )
        report["metrics"]["cold_tokens_per_second_p95"] = percentile95(
            report["metrics"]["cold_tokens_per_second_samples"]
        )
        report["metrics"]["hot_total_ms_p50"] = percentile50(report["metrics"]["hot_total_ms"])
        report["metrics"]["hot_total_ms_p95"] = percentile95(report["metrics"]["hot_total_ms"])
        report["metrics"]["hot_ttft_ms_p50"] = percentile50(report["metrics"]["hot_ttft_ms"])
        report["metrics"]["hot_ttft_ms_p95"] = percentile95(report["metrics"]["hot_ttft_ms"])
        report["metrics"]["hot_tokens_per_second_p50"] = percentile50(report["metrics"]["hot_tokens_per_second_samples"])
        report["metrics"]["hot_tokens_per_second_p95"] = percentile95(report["metrics"]["hot_tokens_per_second_samples"])
        report["metrics"]["peak_rss_bytes"] = max(rss)
        report["gates"]["P4"] = "PASS" if report["metrics"]["hot_ttft_ms_p95"] <= 2500 and report["metrics"]["hot_tokens_per_second_p50"] >= 4 else "Core threshold decision required"

        timeout_started = time.monotonic()
        timeout_frame = request(
            process, {"op":"TIMEOUT_PROBE", "timeout_ms":15000}, captured_stdout, 16.0,
        )
        timeout_elapsed_ms = (time.monotonic() - timeout_started) * 1000
        if (
            timeout_frame.get("type") != "ERROR"
            or timeout_frame.get("code") != "TIMEOUT"
            or timeout_frame.get("state") != "READY"
            or not 14500 <= timeout_elapsed_ms <= 16000
        ):
            raise CandidateFailure("P5 bounded timeout failed")
        if request(process, {"op":"PING"}, captured_stdout).get("type") != "PONG":
            raise CandidateFailure("P5 candidate did not recover READY")
        report["gates"]["P5"] = "PASS"
        cancel_start = request(
            process,
            {"op":"START_CANCEL_PROBE", "operation_id":"gate1-cancel", "work_ms":5000},
            captured_stdout,
        )
        if cancel_start.get("type") == "ERROR" and cancel_start.get("code") == "UNSUPPORTED_CANCEL":
            report["gates"]["P6"] = "Conditional escalation"
        elif cancel_start.get("type") != "GENERATING" or cancel_start.get("operation_id") != "gate1-cancel":
            raise CandidateFailure("P6 cancellable operation did not start")
        else:
            cancel_started = time.monotonic()
            cancel_frame = request(
                process, {"op":"CANCEL", "operation_id":"gate1-cancel"}, captured_stdout, 0.5,
            )
            cancel_elapsed_ms = (time.monotonic() - cancel_started) * 1000
            if cancel_frame.get("type") == "CANCELLED" and cancel_frame.get("operation_id") == "gate1-cancel" and cancel_frame.get("state") == "READY" and cancel_elapsed_ms <= 500:
                report["gates"]["P6"] = "PASS"
            else:
                raise CandidateFailure("P6 cancel result invalid")
        for sequence in range(5):
            marker = f"turn-{sequence}"
            frame = request(
                process,
                {"op":"HISTORY_PROBE","sequence":sequence,"current_marker":marker},
                captured_stdout,
            )
            if (
                frame.get("type") != "HISTORY_RESULT"
                or frame.get("output_marker") != marker
                or frame.get("previous_marker_present") is not False
                or frame.get("state") != "READY"
            ):
                raise CandidateFailure("P8 history isolation failed")
        report["gates"]["P8"] = "PASS"
        shutdown = request(process, {"op":"SHUTDOWN"}, captured_stdout)
        if shutdown.get("type") != "SHUTDOWN_ACK":
            raise CandidateFailure("P1 shutdown acknowledgement failed")
        process.wait(timeout=TERM_GRACE)
        report["cleanup"] = stop(process)
        if (
            process.returncode != 0
            or report["cleanup"]["term_sent"]
            or report["cleanup"]["kill_sent"]
            or not report["cleanup"]["process_group_absent"]
        ):
            report["gates"]["P1"] = "FAIL"
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
        elif not report["cleanup"]["process_group_absent"]:
            retry_cleanup = stop(process)
            report["cleanup"] = {
                "exit_code": retry_cleanup["exit_code"],
                "waited": report["cleanup"]["waited"] or retry_cleanup["waited"],
                "term_sent": report["cleanup"]["term_sent"] or retry_cleanup["term_sent"],
                "kill_sent": report["cleanup"]["kill_sent"] or retry_cleanup["kill_sent"],
                "process_group_absent": retry_cleanup["process_group_absent"],
            }
        if "catalog" in locals() and "stderr_path" in locals():
            report["log_hygiene"] = scan_log_hygiene(catalog, stderr_path, captured_stdout)
            if report["log_hygiene"]["forbidden_sentinel_ids"]:
                report["gates"]["P3"] = "FAIL"
                report["result"] = "FAIL"
                violation = "P3 runner-owned log hygiene detected forbidden content"
                if violation not in report["violations"]:
                    report["violations"].append(violation)
                exit_code = 1
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
