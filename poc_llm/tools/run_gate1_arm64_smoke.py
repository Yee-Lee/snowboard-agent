#!/usr/bin/env python3
"""Bounded model-backed ARM64 smoke runner.

The runner authenticates the append-only ARM64 projection, requires an offline
network namespace, owns the candidate process group, and emits only sanitized
lifecycle evidence. Model text is never copied into the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import subprocess
import sys
import time
from typing import Any, TextIO

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate1_arm64_projection import projection

PROTOCOL_VERSION = "snowboard.llm/1"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PROMPT = {
    "perceptions": [{"kind": "read", "status": "ok", "text": "Choose the rest action."}],
    "pending_message_count": 0,
    "capabilities": {"perceptions": ["read"], "actions": ["rest"], "tools": []},
}


class SmokeFailure(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def network_isolated(route4: Path = Path("/proc/net/route"), route6: Path = Path("/proc/net/ipv6_route")) -> bool:
    ipv4_lines = [line for line in route4.read_text(encoding="ascii").splitlines()[1:] if line.strip()]
    ipv6_lines = [line for line in route6.read_text(encoding="ascii").splitlines() if line.strip()]
    return not ipv4_lines and all(line.split()[-1] == "lo" for line in ipv6_lines)


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


def stop(process: subprocess.Popen[str] | None, term_timeout: float, kill_timeout: float) -> dict[str, Any]:
    if process is None:
        return {
            "exit_code": None,
            "waited": False,
            "term_sent": False,
            "kill_sent": False,
            "process_group_absent": True,
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
        try:
            process.wait(timeout=term_timeout)
        except subprocess.TimeoutExpired:
            pass
        if not wait_group_absent(group_id, term_timeout):
            try:
                os.killpg(group_id, signal.SIGKILL)
                kill_sent = True
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=kill_timeout)
            except subprocess.TimeoutExpired:
                pass
            wait_group_absent(group_id, kill_timeout)
    if process.poll() is None:
        try:
            process.wait(timeout=kill_timeout)
        except subprocess.TimeoutExpired as error:
            raise SmokeFailure("candidate leader could not be reaped") from error
    return {
        "exit_code": process.returncode,
        "waited": True,
        "term_sent": term_sent,
        "kill_sent": kill_sent,
        "process_group_absent": group_absent(group_id),
    }


def protocol_validator(paths: dict[str, Path]) -> Draft202012Validator:
    protocol = json.loads(paths["protocol_schema"].read_text(encoding="utf-8"))
    prompt = json.loads(paths["prompt_schema"].read_text(encoding="utf-8"))
    response = json.loads(paths["response_schema"].read_text(encoding="utf-8"))
    store = {item["$id"]: item for item in (protocol, prompt, response)}
    return Draft202012Validator(protocol, resolver=RefResolver.from_schema(protocol, store=store))


def read_frame(stream: TextIO, timeout: float, validator: Draft202012Validator) -> dict[str, Any]:
    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise SmokeFailure("candidate frame timeout")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise SmokeFailure("candidate stdout closed")
    try:
        frame = json.loads(line)
    except json.JSONDecodeError as error:
        raise SmokeFailure("candidate emitted invalid JSONL") from error
    if not isinstance(frame, dict) or not validator.is_valid(frame):
        raise SmokeFailure("candidate emitted a protocol-invalid frame")
    return frame


def send(process: subprocess.Popen[str], frame: dict[str, Any]) -> None:
    if process.stdin is None:
        raise SmokeFailure("candidate stdin unavailable")
    process.stdin.write(json.dumps(frame, separators=(",", ":")) + "\n")
    process.stdin.flush()


def locked_paths(lock: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, item in lock["artifacts"].items():
        path = (ROOT / item["path"]).resolve()
        if not path.is_file() or digest(path) != item["sha256"]:
            raise SmokeFailure(f"locked artifact mismatch: {name}")
        paths[name] = path
    return paths


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def empty_report(execution_sha: str) -> dict[str, Any]:
    return {
        "packet_id": "G1-ARM64-MODEL-SMOKE-001",
        "execution_sha": execution_sha,
        "candidate_id": "UNBOUND",
        "platform": "ubuntu-aarch64",
        "result": "INCONCLUSIVE",
        "identity": {},
        "isolation": {},
        "lifecycle": {
            "ready": False,
            "generate_terminal": "UNAVAILABLE",
            "shutdown_ack": False,
            "startup_ms": 0,
            "generate_ms": 0,
        },
        "cleanup": {
            "exit_code": None,
            "waited": False,
            "term_sent": False,
            "kill_sent": False,
            "process_group_absent": True,
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
    term_timeout = 2.0
    kill_timeout = 1.0
    exit_code = 2
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
        stderr_path = args.raw_dir / "candidate.stderr"
        argv = value["manifest"]["commands"]["ubuntu-aarch64"]["argv"]
        started = time.monotonic()
        with stderr_path.open("w", encoding="utf-8") as stderr_stream:
            process = subprocess.Popen(
                argv,
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_stream,
                text=True,
                start_new_session=True,
            )
            if process.stdout is None:
                raise SmokeFailure("candidate stdout unavailable")
            ready = read_frame(process.stdout, config["ready_timeout_ms"] / 1000, validator)
            report["lifecycle"]["startup_ms"] = round((time.monotonic() - started) * 1000, 3)
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

            request_id = "arm64-smoke-1"
            send(process, {
                "type": "GENERATE",
                "protocol_version": PROTOCOL_VERSION,
                "request_id": request_id,
                "input": PROMPT,
            })
            generated = time.monotonic()
            terminal = read_frame(
                process.stdout, config["generate_timeout_ms"] / 1000 + 1.0, validator
            )
            report["lifecycle"]["generate_ms"] = round((time.monotonic() - generated) * 1000, 3)
            report["lifecycle"]["generate_terminal"] = terminal.get("type", "UNAVAILABLE")
            if terminal.get("type") != "RESULT" or terminal.get("request_id") != request_id:
                raise SmokeFailure("model-backed generation did not return RESULT")

            send(process, {"type": "SHUTDOWN", "protocol_version": PROTOCOL_VERSION})
            shutdown = read_frame(process.stdout, term_timeout, validator)
            if shutdown.get("type") != "SHUTDOWN_ACK":
                raise SmokeFailure("shutdown acknowledgement missing")
            report["lifecycle"]["shutdown_ack"] = True
            process.wait(timeout=term_timeout)

        report["cleanup"] = stop(process, term_timeout, kill_timeout)
        if (
            report["cleanup"]["exit_code"] != 0
            or report["cleanup"]["term_sent"]
            or report["cleanup"]["kill_sent"]
            or not report["cleanup"]["process_group_absent"]
        ):
            raise SmokeFailure("successful lifecycle cleanup proof failed")
        report["stderr"] = {"bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        report["result"] = "PASS"
        exit_code = 0
    except (SmokeFailure, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        report["violations"].append(str(error))
        report["result"] = "FAIL"
        exit_code = 1
    finally:
        if not report["cleanup"]["waited"]:
            try:
                report["cleanup"] = stop(process, term_timeout, kill_timeout)
            except SmokeFailure as error:
                report["violations"].append(str(error))
                report["result"] = "FAIL"
                exit_code = 1
        if "stderr_path" in locals() and stderr_path.is_file():
            report["stderr"] = {"bytes": stderr_path.stat().st_size, "sha256": digest(stderr_path)}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
