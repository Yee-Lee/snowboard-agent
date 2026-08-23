#!/usr/bin/env python3
"""Offline ARM64 P6 observation and P7 terminate/wait/rebuild proof."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
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


def cancel_disposition(
    frame: dict[str, Any] | None, request_id: str, elapsed_ms: float
) -> str:
    if frame is None:
        return "CONDITIONAL_ESCALATION"
    if (frame.get("type") == "CANCELLED"
            and frame.get("request_id") == request_id
            and elapsed_ms <= 500):
        return "PASS"
    raise SmokeFailure("P6 cancel returned an invalid or late terminal frame")


def ready_identity(config: dict[str, Any], config_sha256: str) -> dict[str, str]:
    return {
        "candidate_id": config["candidate_id"],
        "pairing_revision": config["pairing_revision"],
        "platform": "ubuntu-aarch64",
        "runtime_sha256": config["runtime_sha256"],
        "model_sha256": config["model_sha256"],
        "config_sha256": config_sha256,
    }


def launch(
    argv: list[str], stderr_path: Path
) -> tuple[subprocess.Popen[str], Any]:
    stderr_stream = stderr_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=stderr_stream, text=True, start_new_session=True)
    except Exception:
        stderr_stream.close()
        raise
    return process, stderr_stream


def empty_report(execution_sha: str) -> dict[str, Any]:
    cleanup = {
        "exit_code": None, "waited": False, "term_sent": False,
        "kill_sent": False, "process_group_absent": True,
    }
    return {
        "packet_id": "G1-ARM64-P7-RECOVERY-001",
        "execution_sha": execution_sha,
        "candidate_id": "UNBOUND",
        "platform": "ubuntu-aarch64",
        "result": "INCONCLUSIVE",
        "identity": {},
        "isolation": {},
        "p6": {"terminal": "UNAVAILABLE", "elapsed_ms": None,
               "disposition": "UNAVAILABLE"},
        "level2": {"simulated_unresponsive": False, "cleanup": dict(cleanup)},
        "rebuild": {
            "ready": False, "startup_ms": 0, "generate_terminal": "UNAVAILABLE",
            "shutdown_ack": False, "cleanup": dict(cleanup),
        },
        "stderr": {
            "original": {"bytes": 0, "sha256": "UNAVAILABLE"},
            "rebuild": {"bytes": 0, "sha256": "UNAVAILABLE"},
        },
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
    original: subprocess.Popen[str] | None = None
    rebuilt: subprocess.Popen[str] | None = None
    original_stream = None
    rebuild_stream = None
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
        report_validator = Draft202012Validator(json.loads(
            lock_paths["p7_result_schema"].read_text(encoding="utf-8")))
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
        term_timeout = config["term_timeout_ms"] / 1000
        kill_timeout = config["kill_timeout_ms"] / 1000
        args.raw_dir.mkdir(parents=True, exist_ok=False)
        original_stderr = args.raw_dir / "original.stderr"
        rebuild_stderr = args.raw_dir / "rebuild.stderr"
        argv = value["manifest"]["commands"]["ubuntu-aarch64"]["argv"]

        original, original_stream = launch(argv, original_stderr)
        if original.stdout is None:
            raise SmokeFailure("original candidate stdout unavailable")
        ready = read_frame(
            original.stdout, config["ready_timeout_ms"] / 1000, validator)
        if ready.get("type") != "READY" or ready.get("identity") != ready_identity(
                config, value["config_sha256"]):
            raise SmokeFailure("original READY identity mismatch")

        request_id = "p7-cancel-observation"
        send(original, {
            "type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id, "input": PROMPT,
        })
        time.sleep(0.2)
        cancelled_at = time.monotonic()
        send(original, {
            "type": "CANCEL", "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
        })
        cancel_frame = None
        try:
            cancel_frame = read_frame(
                original.stdout, config["cancel_timeout_ms"] / 1000, validator)
            cancel_ms = (time.monotonic() - cancelled_at) * 1000
        except SmokeFailure as error:
            if str(error) != "candidate frame timeout":
                raise
            cancel_ms = config["cancel_timeout_ms"]
        report["p6"] = {
            "terminal": cancel_frame.get("type") if cancel_frame else "TIMEOUT",
            "elapsed_ms": round(cancel_ms, 3),
            "disposition": cancel_disposition(cancel_frame, request_id, cancel_ms),
        }

        if report["p6"]["disposition"] == "PASS":
            os.killpg(original.pid, signal.SIGSTOP)
            report["level2"]["simulated_unresponsive"] = True
        report["level2"]["cleanup"] = stop(original, term_timeout, kill_timeout)
        original = None
        level2 = report["level2"]["cleanup"]
        if (not level2["waited"] or not level2["term_sent"]
                or not level2["process_group_absent"]):
            raise SmokeFailure("P7 Level 2 termination/wait proof failed")
        original_stream.close()
        original_stream = None

        rebuild_started = time.monotonic()
        rebuilt, rebuild_stream = launch(argv, rebuild_stderr)
        if rebuilt.stdout is None:
            raise SmokeFailure("rebuilt candidate stdout unavailable")
        rebuilt_ready = read_frame(
            rebuilt.stdout, config["rebuild_timeout_ms"] / 1000, validator)
        rebuild_ms = (time.monotonic() - rebuild_started) * 1000
        report["rebuild"]["startup_ms"] = round(rebuild_ms, 3)
        report["rebuild"]["ready"] = (
            rebuilt_ready.get("type") == "READY"
            and rebuilt_ready.get("identity") == ready_identity(
                config, value["config_sha256"])
            and rebuild_ms <= config["rebuild_timeout_ms"])
        if not report["rebuild"]["ready"]:
            raise SmokeFailure("P7 rebuild READY barrier failed")

        rebuild_request = "p7-rebuild-generate"
        send(rebuilt, {
            "type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
            "request_id": rebuild_request, "input": PROMPT,
        })
        terminal = read_frame(
            rebuilt.stdout, config["generate_timeout_ms"] / 1000 + 1, validator)
        report["rebuild"]["generate_terminal"] = terminal.get("type", "UNAVAILABLE")
        if terminal.get("type") != "RESULT" or terminal.get("request_id") != rebuild_request:
            raise SmokeFailure("P7 rebuilt candidate generation failed")
        send(rebuilt, {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
        shutdown = read_frame(rebuilt.stdout, term_timeout, validator)
        report["rebuild"]["shutdown_ack"] = shutdown.get("type") == "SHUTDOWN_ACK"
        if not report["rebuild"]["shutdown_ack"]:
            raise SmokeFailure("P7 rebuilt shutdown acknowledgement missing")
        rebuilt.wait(timeout=term_timeout)
        report["rebuild"]["cleanup"] = stop(rebuilt, term_timeout, kill_timeout)
        rebuilt = None
        rebuild_cleanup = report["rebuild"]["cleanup"]
        if (rebuild_cleanup["exit_code"] != 0 or rebuild_cleanup["term_sent"]
                or rebuild_cleanup["kill_sent"]
                or not rebuild_cleanup["process_group_absent"]):
            raise SmokeFailure("P7 rebuilt clean-exit proof failed")
        rebuild_stream.close()
        rebuild_stream = None

        for name, path in (("original", original_stderr), ("rebuild", rebuild_stderr)):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "ADAPTER_DIAGNOSTIC " in text:
                raise SmokeFailure(f"{name} adapter reported a backend diagnostic")
            report["stderr"][name] = {
                "bytes": path.stat().st_size, "sha256": digest(path)}
        report["result"] = "PASS"
        if list(report_validator.iter_errors(report)):
            raise SmokeFailure("P7 report schema mismatch")
        exit_code = 0
    except (SmokeFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        report["violations"].append(str(error))
        report["result"], exit_code = "FAIL", 1
    finally:
        for name, process in (("original", original), ("rebuild", rebuilt)):
            if process is not None:
                try:
                    cleanup = stop(process, term_timeout, kill_timeout)
                    if name == "original":
                        report["level2"]["cleanup"] = cleanup
                    else:
                        report["rebuild"]["cleanup"] = cleanup
                except SmokeFailure as error:
                    report["violations"].append(str(error))
                    report["result"], exit_code = "FAIL", 1
        for stream in (original_stream, rebuild_stream):
            if stream is not None:
                stream.close()
        if "original_stderr" in locals() and original_stderr.is_file():
            report["stderr"]["original"] = {
                "bytes": original_stderr.stat().st_size,
                "sha256": digest(original_stderr)}
        if "rebuild_stderr" in locals() and rebuild_stderr.is_file():
            report["stderr"]["rebuild"] = {
                "bytes": rebuild_stderr.stat().st_size,
                "sha256": digest(rebuild_stderr)}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
