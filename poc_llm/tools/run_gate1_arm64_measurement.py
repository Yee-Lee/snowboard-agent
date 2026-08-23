#!/usr/bin/env python3
"""Offline ARM64 model measurement runner with sanitized evidence only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate1_arm64_projection import projection
from poc_llm.tools.run_gate1_arm64_smoke import (
    PROTOCOL_VERSION, PROMPT, SHA_PATTERN, SmokeFailure, digest, git_head,
    locked_paths, network_isolated, protocol_validator, read_frame, send, stop,
)

SESSION_COUNT = 10
CANCEL_BOUND_MS = 500.0


def percentile(values: list[float], percentile_value: float) -> float:
    """Return the nearest-rank percentile."""
    if not values:
        raise ValueError("percentile requires observations")
    ordered = sorted(values)
    rank = max(1, int((percentile_value * len(ordered) + 99.999999) // 100))
    return ordered[min(rank, len(ordered)) - 1]


def checked_metrics(frame: dict[str, Any]) -> dict[str, int | float]:
    metrics = frame.get("metrics")
    required = {
        "init_ms", "ttft_ms", "prefill_tokens", "prefill_tokens_per_second",
        "decode_tokens", "decode_tokens_per_second", "kv_tokens",
    }
    if not isinstance(metrics, dict) or set(metrics) != required:
        raise SmokeFailure("RESULT benchmark metrics are incomplete")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           for value in metrics.values()):
        raise SmokeFailure("RESULT benchmark metrics are non-numeric")
    if metrics["init_ms"] < 0 or metrics["ttft_ms"] < 0:
        raise SmokeFailure("RESULT timing metric is negative")
    if metrics["prefill_tokens"] < 1 or metrics["prefill_tokens_per_second"] <= 0:
        raise SmokeFailure("RESULT prefill metric is invalid")
    if not 1 <= metrics["decode_tokens"] <= 16 or metrics["decode_tokens_per_second"] <= 0:
        raise SmokeFailure("RESULT decode metric is invalid")
    if metrics["kv_tokens"] < metrics["decode_tokens"]:
        raise SmokeFailure("RESULT KV token metric is invalid")
    return metrics


def read_rss_kib(pid: int) -> int:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError, ValueError):
        return 0
    return 0


class RssSampler:
    def __init__(self, pid: int):
        self.pid = pid
        self.peak_kib = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="rss-sampler", daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(0.02):
            self.peak_kib = max(self.peak_kib, read_rss_kib(self.pid))

    def __enter__(self) -> "RssSampler":
        self.peak_kib = read_rss_kib(self.pid)
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self.peak_kib = max(self.peak_kib, read_rss_kib(self.pid))


def measurement_summary(sessions: list[dict[str, Any]]) -> dict[str, float]:
    hot = sessions[1:]
    return {
        "hot_ttft_ms_p50": round(percentile([x["metrics"]["ttft_ms"] for x in hot], 50), 3),
        "hot_ttft_ms_p95": round(percentile([x["metrics"]["ttft_ms"] for x in hot], 95), 3),
        "hot_wall_ms_p50": round(percentile([x["wall_ms"] for x in hot], 50), 3),
        "hot_wall_ms_p95": round(percentile([x["wall_ms"] for x in hot], 95), 3),
        "hot_prefill_tps_p50": round(percentile(
            [x["metrics"]["prefill_tokens_per_second"] for x in hot], 50), 3),
        "hot_decode_tps_p50": round(percentile(
            [x["metrics"]["decode_tokens_per_second"] for x in hot], 50), 3),
        "hot_decode_tokens_mean": round(statistics.fmean(
            x["metrics"]["decode_tokens"] for x in hot), 3),
    }


def empty_report(execution_sha: str) -> dict[str, Any]:
    return {
        "packet_id": "G1-ARM64-MODEL-MEASUREMENT-001",
        "execution_sha": execution_sha, "candidate_id": "UNBOUND",
        "platform": "ubuntu-aarch64", "result": "INCONCLUSIVE",
        "identity": {}, "isolation": {}, "sessions": [], "summary": {},
        "probes": {"busy": False, "cancelled": False, "cancel_ms": None},
        "resources": {"peak_rss_kib": 0},
        "cleanup": {"exit_code": None, "waited": False, "term_sent": False,
                    "kill_sent": False, "process_group_absent": True},
        "stderr": {"bytes": 0, "sha256": "UNAVAILABLE"}, "violations": [],
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
            lock_paths["measurement_schema"].read_text(encoding="utf-8")))
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
            "ipv4_routes_present": False, "ipv6_non_loopback_routes_present": False,
        }
        term_timeout = config["term_timeout_ms"] / 1000
        kill_timeout = config["kill_timeout_ms"] / 1000
        args.raw_dir.mkdir(parents=True, exist_ok=False)
        stderr_path = args.raw_dir / "candidate.stderr"
        argv = value["manifest"]["commands"]["ubuntu-aarch64"]["argv"]
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr_stream, text=True, start_new_session=True)
            if process.stdout is None:
                raise SmokeFailure("candidate stdout unavailable")
            ready = read_frame(process.stdout, config["ready_timeout_ms"] / 1000, validator)
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

            with RssSampler(process.pid) as rss:
                for index in range(SESSION_COUNT):
                    request_id = f"measure-{index + 1}"
                    started = time.monotonic()
                    send(process, {"type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
                                   "request_id": request_id, "input": PROMPT})
                    terminal = read_frame(
                        process.stdout, config["generate_timeout_ms"] / 1000 + 1, validator)
                    wall_ms = (time.monotonic() - started) * 1000
                    if terminal.get("type") != "RESULT" or terminal.get("request_id") != request_id:
                        raise SmokeFailure("measurement generation did not return RESULT")
                    report["sessions"].append({
                        "index": index + 1,
                        "temperature": "cold" if index == 0 else "hot",
                        "wall_ms": round(wall_ms, 3),
                        "metrics": checked_metrics(terminal),
                    })

                active_id, busy_id = "probe-busy-active", "probe-busy-rejected"
                send(process, {"type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
                               "request_id": active_id, "input": PROMPT})
                send(process, {"type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
                               "request_id": busy_id, "input": PROMPT})
                first = read_frame(
                    process.stdout, config["generate_timeout_ms"] / 1000 + 1, validator)
                second = read_frame(
                    process.stdout, config["generate_timeout_ms"] / 1000 + 1, validator)
                frames = {first.get("request_id"): first, second.get("request_id"): second}
                report["probes"]["busy"] = (
                    frames.get(busy_id, {}).get("type") == "ERROR"
                    and frames[busy_id].get("code") == "BUSY"
                    and frames.get(active_id, {}).get("type") == "RESULT")
                if not report["probes"]["busy"]:
                    raise SmokeFailure("model-backed BUSY probe failed")
                checked_metrics(frames[active_id])

                cancel_id = "probe-cancel"
                send(process, {"type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
                               "request_id": cancel_id, "input": PROMPT})
                time.sleep(0.2)
                cancelled_at = time.monotonic()
                send(process, {"type": "CANCEL", "protocol_version": PROTOCOL_VERSION,
                               "request_id": cancel_id})
                cancelled = read_frame(process.stdout, CANCEL_BOUND_MS / 1000, validator)
                cancel_ms = (time.monotonic() - cancelled_at) * 1000
                report["probes"]["cancel_ms"] = round(cancel_ms, 3)
                report["probes"]["cancelled"] = (
                    cancelled.get("type") == "CANCELLED"
                    and cancelled.get("request_id") == cancel_id
                    and cancel_ms <= CANCEL_BOUND_MS)
                if not report["probes"]["cancelled"]:
                    raise SmokeFailure("model-backed cancellation bound failed")
            report["resources"]["peak_rss_kib"] = rss.peak_kib

            send(process, {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
            shutdown = read_frame(process.stdout, term_timeout, validator)
            if shutdown.get("type") != "SHUTDOWN_ACK":
                raise SmokeFailure("shutdown acknowledgement missing")
            process.wait(timeout=term_timeout)

        report["cleanup"] = stop(process, term_timeout, kill_timeout)
        if (report["cleanup"]["exit_code"] != 0 or report["cleanup"]["term_sent"]
                or report["cleanup"]["kill_sent"]
                or not report["cleanup"]["process_group_absent"]):
            raise SmokeFailure("successful lifecycle cleanup proof failed")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if "ADAPTER_DIAGNOSTIC " in stderr_text:
            raise SmokeFailure("adapter reported a backend diagnostic")
        report["stderr"] = {"bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        report["summary"] = measurement_summary(report["sessions"])
        report["result"] = "PASS"
        if list(result_validator.iter_errors(report)):
            raise SmokeFailure("measurement report schema mismatch")
        exit_code = 0
    except (SmokeFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        report["violations"].append(str(error))
        report["result"], exit_code = "FAIL", 1
    finally:
        if not report["cleanup"]["waited"]:
            try:
                report["cleanup"] = stop(process, term_timeout, kill_timeout)
            except SmokeFailure as error:
                report["violations"].append(str(error))
                report["result"], exit_code = "FAIL", 1
        if "stderr_path" in locals() and stderr_path.is_file():
            report["stderr"] = {"bytes": stderr_path.stat().st_size,
                                "sha256": digest(stderr_path)}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
