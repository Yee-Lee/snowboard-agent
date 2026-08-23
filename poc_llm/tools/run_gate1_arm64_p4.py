#!/usr/bin/env python3
"""Formal offline ARM64 P4 workstation pre-screen runner."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate1_arm64_projection import projection
from poc_llm.tools.run_gate1_arm64_measurement import (
    RssSampler, checked_metrics, percentile,
)
from poc_llm.tools.run_gate1_arm64_smoke import (
    PROTOCOL_VERSION, PROMPT, SHA_PATTERN, SmokeFailure, digest, git_head,
    locked_paths, network_isolated, protocol_validator, read_frame, send, stop,
)

WARMUP_COUNT = 3
COLD_COUNT = 3
HOT_COUNT = 20


def aggregate(samples: list[dict[str, Any]]) -> dict[str, float]:
    def values(field: str) -> list[float]:
        if field == "wall_ms":
            return [item[field] for item in samples]
        return [item["metrics"][field] for item in samples]

    return {
        "wall_ms_p50": round(percentile(values("wall_ms"), 50), 3),
        "wall_ms_p95": round(percentile(values("wall_ms"), 95), 3),
        "ttft_ms_p50": round(percentile(values("ttft_ms"), 50), 3),
        "ttft_ms_p95": round(percentile(values("ttft_ms"), 95), 3),
        "prefill_tps_p50": round(
            percentile(values("prefill_tokens_per_second"), 50), 3),
        "prefill_tps_p95": round(
            percentile(values("prefill_tokens_per_second"), 95), 3),
        "decode_tps_p50": round(
            percentile(values("decode_tokens_per_second"), 50), 3),
        "decode_tps_p95": round(
            percentile(values("decode_tokens_per_second"), 95), 3),
    }


def generate_sample(
    process: subprocess.Popen[str],
    stdout: Any,
    validator: Draft202012Validator,
    timeout_s: float,
    phase: str,
    sequence: int,
) -> dict[str, Any]:
    request_id = f"p4-{phase}-{sequence}"
    started = time.monotonic()
    send(process, {
        "type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id, "input": PROMPT,
    })
    terminal = read_frame(stdout, timeout_s, validator)
    wall_ms = (time.monotonic() - started) * 1000
    if terminal.get("type") != "RESULT" or terminal.get("request_id") != request_id:
        raise SmokeFailure(f"P4 {phase} generation did not return RESULT")
    return {
        "sequence": sequence,
        "wall_ms": round(wall_ms, 3),
        "metrics": checked_metrics(terminal),
    }


def empty_report(execution_sha: str) -> dict[str, Any]:
    return {
        "packet_id": "G1-ARM64-P4-001",
        "execution_sha": execution_sha,
        "candidate_id": "UNBOUND",
        "platform": "ubuntu-aarch64",
        "result": "INCONCLUSIVE",
        "identity": {}, "isolation": {},
        "method": {
            "input_tokens": 128, "max_output_tokens": 16,
            "temperature": 0, "warmup_count": WARMUP_COUNT,
            "cold_count": COLD_COUNT, "hot_count": HOT_COUNT,
        },
        "warmups_completed": 0,
        "cold_samples": [], "hot_samples": [],
        "summary": {"cold": {}, "hot": {}},
        "resources": {
            "peak_rss_kib": 0, "model_bytes": 0,
            "runtime_bytes": 0, "combined_artifact_bytes": 0,
        },
        "p4_disposition": "INCONCLUSIVE",
        "lifecycle": {"ready": False, "shutdown_ack": False},
        "cleanup": {
            "exit_code": None, "waited": False, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        },
        "stderr": {"bytes": 0, "sha256": "UNAVAILABLE"},
        "violations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-sha256", required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()

    report = empty_report(args.execution_sha)
    process: subprocess.Popen[str] | None = None
    term_timeout, kill_timeout, exit_code = 2.0, 1.0, 2
    try:
        if not SHA_PATTERN.fullmatch(args.execution_sha) or git_head() != args.execution_sha:
            raise SmokeFailure("execution SHA is not the checked-out commit")
        if digest(args.lock) != args.lock_sha256:
            raise SmokeFailure("ARM64 lock checksum mismatch")
        if platform.machine() != "aarch64":
            raise SmokeFailure("platform mismatch: ARM64 runner requires aarch64")
        if not network_isolated():
            raise SmokeFailure("offline network namespace proof failed")
        if args.raw_dir.exists():
            raise SmokeFailure("raw evidence directory is dirty")

        value = projection(args.candidate_manifest, args.lock)
        config = value["config"]
        lock_paths = locked_paths(value["lock"])
        validator = protocol_validator(lock_paths)
        result_validator = Draft202012Validator(json.loads(
            lock_paths["p4_result_schema"].read_text(encoding="utf-8")))
        report["candidate_id"] = config["candidate_id"]
        report["identity"] = {
            "lock_sha256": args.lock_sha256,
            "manifest_sha256": value["manifest_sha256"],
            "config_sha256": value["config_sha256"],
            "runtime_sha256": config["runtime_sha256"],
            "model_sha256": config["model_sha256"],
            "runner_sha256": digest(Path(__file__)),
            "adapter_sha256": digest(lock_paths["adapter"]),
        }
        report["isolation"] = {
            "network_namespace": os.readlink("/proc/self/ns/net"),
            "ipv4_routes_present": False,
            "ipv6_non_loopback_routes_present": False,
        }
        model_bytes = Path(config["model_path"]).stat().st_size
        runtime_bytes = Path(config["runtime_path"]).stat().st_size
        report["resources"].update({
            "model_bytes": model_bytes,
            "runtime_bytes": runtime_bytes,
            "combined_artifact_bytes": model_bytes + runtime_bytes,
        })
        term_timeout = config["term_timeout_ms"] / 1000
        kill_timeout = config["kill_timeout_ms"] / 1000
        timeout_s = config["generate_timeout_ms"] / 1000 + 1
        args.raw_dir.mkdir(parents=True, exist_ok=False)
        stderr_path = args.raw_dir / "candidate.stderr"
        argv = value["manifest"]["commands"]["ubuntu-aarch64"]["argv"]
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr_stream, text=True, start_new_session=True)
            if process.stdout is None:
                raise SmokeFailure("candidate stdout unavailable")
            ready = read_frame(
                process.stdout, config["ready_timeout_ms"] / 1000, validator)
            expected_identity = {
                "candidate_id": config["candidate_id"],
                "pairing_revision": config["pairing_revision"],
                "platform": "ubuntu-aarch64",
                "runtime_sha256": config["runtime_sha256"],
                "model_sha256": config["model_sha256"],
                "config_sha256": value["config_sha256"],
            }
            if ready.get("type") != "READY" or ready.get("identity") != expected_identity:
                raise SmokeFailure("READY identity mismatch")
            report["lifecycle"]["ready"] = True

            with RssSampler(process.pid) as rss:
                for sequence in range(1, WARMUP_COUNT + 1):
                    generate_sample(
                        process, process.stdout, validator, timeout_s,
                        "warmup", sequence)
                    report["warmups_completed"] = sequence
                for sequence in range(1, COLD_COUNT + 1):
                    report["cold_samples"].append(generate_sample(
                        process, process.stdout, validator, timeout_s,
                        "cold", sequence))
                for sequence in range(1, HOT_COUNT + 1):
                    report["hot_samples"].append(generate_sample(
                        process, process.stdout, validator, timeout_s,
                        "hot", sequence))
            report["resources"]["peak_rss_kib"] = rss.peak_kib

            send(process, {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
            shutdown = read_frame(process.stdout, term_timeout, validator)
            report["lifecycle"]["shutdown_ack"] = (
                shutdown.get("type") == "SHUTDOWN_ACK")
            if not report["lifecycle"]["shutdown_ack"]:
                raise SmokeFailure("shutdown acknowledgement missing")
            process.wait(timeout=term_timeout)

        report["cleanup"] = stop(process, term_timeout, kill_timeout)
        if (report["cleanup"]["exit_code"] != 0 or report["cleanup"]["term_sent"]
                or report["cleanup"]["kill_sent"]
                or not report["cleanup"]["process_group_absent"]):
            raise SmokeFailure("P4 clean lifecycle proof failed")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if "ADAPTER_DIAGNOSTIC " in stderr_text:
            raise SmokeFailure("adapter reported a backend diagnostic")
        report["stderr"] = {
            "bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        report["summary"] = {
            "cold": aggregate(report["cold_samples"]),
            "hot": aggregate(report["hot_samples"]),
        }
        hot = report["summary"]["hot"]
        report["p4_disposition"] = (
            "PASS" if hot["ttft_ms_p95"] <= 2500
            and hot["decode_tps_p50"] >= 4
            else "Core threshold decision required")
        report["result"] = report["p4_disposition"]
        if list(result_validator.iter_errors(report)):
            raise SmokeFailure("P4 report schema mismatch")
        exit_code = 0
    except (SmokeFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        report["violations"].append(str(error))
        report["result"], report["p4_disposition"], exit_code = "FAIL", "FAIL", 1
    finally:
        if "rss" in locals():
            report["resources"]["peak_rss_kib"] = rss.peak_kib
        if not report["cleanup"]["waited"]:
            try:
                report["cleanup"] = stop(process, term_timeout, kill_timeout)
            except SmokeFailure as error:
                report["violations"].append(str(error))
                report["result"], report["p4_disposition"], exit_code = "FAIL", "FAIL", 1
        if "stderr_path" in locals() and stderr_path.is_file():
            report["stderr"] = {
                "bytes": stderr_path.stat().st_size,
                "sha256": digest(stderr_path)}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
