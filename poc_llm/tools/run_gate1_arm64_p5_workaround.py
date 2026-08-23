#!/usr/bin/env python3
"""Run user-approved P5 timeout workaround without claiming contract P5."""
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
from poc_llm.tools.run_gate1_arm64_p5_workaround_child import (
    WORKAROUND_TIMEOUT_MS, config_digest, effective_config,
)
from poc_llm.tools.run_gate1_arm64_smoke import (
    PROTOCOL_VERSION, PROMPT, SHA_PATTERN, SmokeFailure, digest, git_head,
    locked_paths, network_isolated, protocol_validator, read_frame, send, stop,
)


def empty_report(execution_sha: str) -> dict[str, Any]:
    return {
        "packet_id": "G1-ARM64-P5-WORKAROUND-001",
        "execution_sha": execution_sha,
        "candidate_id": "UNBOUND", "platform": "ubuntu-aarch64",
        "result": "INCONCLUSIVE",
        "authority": "USER_APPROVED_WORKAROUND_CORE_APPROVAL_PENDING",
        "contract_p5_disposition": "INCONCLUSIVE",
        "identity": {}, "isolation": {},
        "workaround": {
            "base_generate_timeout_ms": 15000,
            "effective_generate_timeout_ms": WORKAROUND_TIMEOUT_MS,
            "only_config_delta": "generate_timeout_ms",
            "terminal": "UNAVAILABLE", "terminal_state": "UNAVAILABLE",
            "elapsed_ms": 0, "observation": "INCONCLUSIVE",
        },
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
        base_config = value["config"]
        paths = locked_paths(value["lock"])
        validator = protocol_validator(paths)
        report_validator = Draft202012Validator(json.loads(
            paths["p5_workaround_result_schema"].read_text(encoding="utf-8")))
        manifest_config = value["manifest"]["configs"]["ubuntu-aarch64"]
        config_path = ROOT / manifest_config["path"]
        effective = effective_config(base_config)
        differing = sorted(
            key for key in base_config if base_config[key] != effective[key]
        )
        if differing != ["generate_timeout_ms"]:
            raise SmokeFailure("workaround config delta is not isolated")
        report["candidate_id"] = base_config["candidate_id"]
        report["identity"] = {
            "lock_sha256": args.lock_sha256,
            "manifest_sha256": value["manifest_sha256"],
            "base_config_sha256": value["config_sha256"],
            "effective_config_sha256": config_digest(effective),
            "runtime_sha256": base_config["runtime_sha256"],
            "model_sha256": base_config["model_sha256"],
            "runner_sha256": digest(Path(__file__)),
            "workaround_child_sha256": digest(paths["p5_workaround_child"]),
            "canonical_adapter_sha256": digest(paths["adapter"]),
        }
        report["isolation"] = {
            "network_namespace": os.readlink("/proc/self/ns/net"),
            "ipv4_routes_present": False,
            "ipv6_non_loopback_routes_present": False,
        }
        term_timeout = base_config["term_timeout_ms"] / 1000
        kill_timeout = base_config["kill_timeout_ms"] / 1000
        args.raw_dir.mkdir(parents=True, exist_ok=False)
        stderr_path = args.raw_dir / "candidate.stderr"
        argv = [
            sys.executable, str(paths["p5_workaround_child"]),
            "--base-config", str(config_path),
            "--base-config-sha256", value["config_sha256"],
        ]
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr_stream, text=True, start_new_session=True)
            if process.stdout is None:
                raise SmokeFailure("candidate stdout unavailable")
            ready = read_frame(
                process.stdout, base_config["ready_timeout_ms"] / 1000,
                validator)
            expected = {
                "candidate_id": base_config["candidate_id"],
                "pairing_revision": base_config["pairing_revision"],
                "platform": "ubuntu-aarch64",
                "runtime_sha256": base_config["runtime_sha256"],
                "model_sha256": base_config["model_sha256"],
                "config_sha256": config_digest(effective),
            }
            if ready.get("type") != "READY" or ready.get("identity") != expected:
                raise SmokeFailure("READY workaround identity mismatch")
            report["lifecycle"]["ready"] = True
            started = time.monotonic()
            send(process, {
                "type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
                "request_id": "p5-workaround-timeout", "input": PROMPT,
            })
            terminal = read_frame(
                process.stdout, WORKAROUND_TIMEOUT_MS / 1000 + 5, validator)
            elapsed_ms = (time.monotonic() - started) * 1000
            report["workaround"].update({
                "terminal": terminal.get("type", "UNAVAILABLE"),
                "terminal_state": terminal.get("state", "UNAVAILABLE"),
                "elapsed_ms": round(elapsed_ms, 3),
            })
            valid_timeout = (
                terminal.get("type") == "ERROR"
                and terminal.get("request_id") == "p5-workaround-timeout"
                and terminal.get("code") == "TIMEOUT"
                and terminal.get("state") == "READY"
                and elapsed_ms >= WORKAROUND_TIMEOUT_MS
                and elapsed_ms <= WORKAROUND_TIMEOUT_MS + 5000
            )
            report["workaround"]["observation"] = (
                "PASS" if valid_timeout else "FAIL")
            if not valid_timeout:
                raise SmokeFailure("workaround did not return bounded TIMEOUT")
            send(process, {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
            shutdown = read_frame(process.stdout, term_timeout, validator)
            report["lifecycle"]["shutdown_ack"] = (
                shutdown.get("type") == "SHUTDOWN_ACK")
            if not report["lifecycle"]["shutdown_ack"]:
                raise SmokeFailure("shutdown acknowledgement missing")
            process.wait(timeout=term_timeout)

        report["cleanup"] = stop(process, term_timeout, kill_timeout)
        if (report["cleanup"]["exit_code"] != 0
                or report["cleanup"]["term_sent"]
                or report["cleanup"]["kill_sent"]
                or not report["cleanup"]["process_group_absent"]):
            raise SmokeFailure("clean lifecycle proof failed")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if "ADAPTER_DIAGNOSTIC " in stderr_text:
            raise SmokeFailure("adapter reported a backend diagnostic")
        report["stderr"] = {
            "bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        if list(report_validator.iter_errors(report)):
            raise SmokeFailure("P5 workaround report schema mismatch")
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
            report["stderr"] = {
                "bytes": stderr_path.stat().st_size,
                "sha256": digest(stderr_path)}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
