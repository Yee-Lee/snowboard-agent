#!/usr/bin/env python3
"""Offline ARM64 long-prompt and five-turn history-isolation pre-screen."""
from __future__ import annotations

import argparse
import hashlib
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
from poc_llm.tools.run_gate1_arm64_measurement import checked_metrics
from poc_llm.tools.run_gate1_arm64_smoke import (
    PROTOCOL_VERSION, PROMPT, SHA_PATTERN, SmokeFailure, digest, git_head,
    locked_paths, network_isolated, protocol_validator, read_frame, send, stop,
)

LONG_PROMPT = {
    "perceptions": [{
        "kind": "read", "status": "ok",
        "text": (
            "Choose the rest action. Context markers: alpha bravo charlie delta "
            "echo foxtrot golf hotel india juliet kilo lima mike november oscar papa."
        ),
    }],
    "pending_message_count": 0,
    "capabilities": {
        "perceptions": ["read"], "actions": ["rest"], "tools": [],
    },
}
HISTORY_COUNT = 5


def response_hash(frame: dict[str, Any]) -> str:
    response = frame.get("response")
    if not isinstance(response, dict):
        raise SmokeFailure("RESULT response is unavailable")
    encoded = json.dumps(
        response, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def generate(
    process: subprocess.Popen[str],
    stdout: Any,
    validator: Draft202012Validator,
    timeout_s: float,
    request_id: str,
    prompt: dict[str, Any],
) -> dict[str, Any]:
    started = time.monotonic()
    send(process, {
        "type": "GENERATE", "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id, "input": prompt,
    })
    terminal = read_frame(stdout, timeout_s, validator)
    wall_ms = (time.monotonic() - started) * 1000
    if terminal.get("type") != "RESULT" or terminal.get("request_id") != request_id:
        raise SmokeFailure("model-backed generation did not return RESULT")
    return {
        "wall_ms": round(wall_ms, 3),
        "metrics": checked_metrics(terminal),
        "response_sha256": response_hash(terminal),
    }


def empty_report(execution_sha: str) -> dict[str, Any]:
    return {
        "packet_id": "G1-ARM64-LONG-P8-001",
        "execution_sha": execution_sha,
        "candidate_id": "UNBOUND", "platform": "ubuntu-aarch64",
        "result": "INCONCLUSIVE", "identity": {}, "isolation": {},
        "long_prompt": {
            "baseline": {}, "long": {}, "prefill_increased": False,
            "within_input_envelope": False, "result": "INCONCLUSIVE",
        },
        "p5": {
            "disposition": "INCONCLUSIVE",
            "reason": "FIXED_16_OUTPUT_ENVELOPE_DID_NOT_TRIGGER_15S_TIMEOUT",
            "generate_timeout_ms": 15000, "maximum_observed_wall_ms": 0,
        },
        "p8": {
            "turns": [], "response_hash_stable": False,
            "prefill_tokens_stable": False, "decode_tokens_stable": False,
            "kv_tokens_stable": False, "result": "INCONCLUSIVE",
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
        config = value["config"]
        paths = locked_paths(value["lock"])
        validator = protocol_validator(paths)
        result_validator = Draft202012Validator(json.loads(
            paths["long_p8_result_schema"].read_text(encoding="utf-8")))
        report["candidate_id"] = config["candidate_id"]
        report["identity"] = {
            "lock_sha256": args.lock_sha256,
            "manifest_sha256": value["manifest_sha256"],
            "config_sha256": value["config_sha256"],
            "runtime_sha256": config["runtime_sha256"],
            "model_sha256": config["model_sha256"],
            "runner_sha256": digest(Path(__file__)),
            "adapter_sha256": digest(paths["adapter"]),
        }
        report["isolation"] = {
            "network_namespace": os.readlink("/proc/self/ns/net"),
            "ipv4_routes_present": False,
            "ipv6_non_loopback_routes_present": False,
        }
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
            expected = {
                "candidate_id": config["candidate_id"],
                "pairing_revision": config["pairing_revision"],
                "platform": "ubuntu-aarch64",
                "runtime_sha256": config["runtime_sha256"],
                "model_sha256": config["model_sha256"],
                "config_sha256": value["config_sha256"],
            }
            if ready.get("type") != "READY" or ready.get("identity") != expected:
                raise SmokeFailure("READY identity mismatch")
            report["lifecycle"]["ready"] = True

            baseline = generate(
                process, process.stdout, validator, timeout_s,
                "long-baseline", PROMPT)
            long_sample = generate(
                process, process.stdout, validator, timeout_s,
                "long-fixed", LONG_PROMPT)
            prefill_increased = (
                long_sample["metrics"]["prefill_tokens"]
                > baseline["metrics"]["prefill_tokens"])
            within_envelope = (
                long_sample["metrics"]["prefill_tokens"]
                <= config["max_input_tokens"])
            report["long_prompt"] = {
                "baseline": baseline, "long": long_sample,
                "prefill_increased": prefill_increased,
                "within_input_envelope": within_envelope,
                "result": "PASS" if prefill_increased and within_envelope else "FAIL",
            }
            if report["long_prompt"]["result"] != "PASS":
                raise SmokeFailure("long prompt did not prove bounded extra prefill")

            for sequence in range(1, HISTORY_COUNT + 1):
                sample = generate(
                    process, process.stdout, validator, timeout_s,
                    f"p8-turn-{sequence}", LONG_PROMPT)
                report["p8"]["turns"].append({"sequence": sequence, **sample})
            turns = report["p8"]["turns"]
            for key, source in (
                ("response_hash_stable", "response_sha256"),
                ("prefill_tokens_stable", "prefill_tokens"),
                ("decode_tokens_stable", "decode_tokens"),
                ("kv_tokens_stable", "kv_tokens"),
            ):
                values = [
                    item[source] if source == "response_sha256"
                    else item["metrics"][source]
                    for item in turns
                ]
                report["p8"][key] = len(set(values)) == 1
            report["p8"]["result"] = (
                "PASS" if all(report["p8"][key] for key in (
                    "response_hash_stable", "prefill_tokens_stable",
                    "decode_tokens_stable", "kv_tokens_stable"))
                else "FAIL")
            if report["p8"]["result"] != "PASS":
                raise SmokeFailure("P8 history-isolation invariants failed")

            observed = [baseline["wall_ms"], long_sample["wall_ms"]]
            observed.extend(item["wall_ms"] for item in turns)
            report["p5"]["maximum_observed_wall_ms"] = max(observed)
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
            raise SmokeFailure("clean lifecycle proof failed")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if "ADAPTER_DIAGNOSTIC " in stderr_text:
            raise SmokeFailure("adapter reported a backend diagnostic")
        report["stderr"] = {
            "bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        report["result"] = "INCONCLUSIVE"
        if list(result_validator.iter_errors(report)):
            raise SmokeFailure("long/P8 report schema mismatch")
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
