#!/usr/bin/env python3
"""Run deterministic local lifecycle checks for M0-PACKET-001."""

from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from typing import Any, TextIO


PACKET_ID = "M0-PACKET-001"
READY_TIMEOUT_SECONDS = 2.0
EXIT_TIMEOUT_SECONDS = 1.0
TERM_GRACE_SECONDS = 0.25
ROOT = Path(__file__).resolve().parents[1]
CHILD = ROOT / "src" / "llm_poc_m0" / "dummy_child.py"


def read_line(stream: TextIO, timeout_seconds: float) -> dict[str, Any]:
    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    try:
        if not selector.select(timeout_seconds):
            raise TimeoutError(f"no child output within {timeout_seconds:.2f}s")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise RuntimeError("child stdout closed before a frame was received")
    return json.loads(line)


def start_child(mode: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(CHILD), "--mode", mode],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def require_pipe(pipe: TextIO | None, name: str) -> TextIO:
    if pipe is None:
        raise RuntimeError(f"missing child {name} pipe")
    return pipe


def group_is_gone(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def stop_if_needed(child: subprocess.Popen[str]) -> None:
    if child.poll() is None:
        try:
            os.killpg(os.getpgid(child.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=EXIT_TIMEOUT_SECONDS)


def graceful_case() -> dict[str, Any]:
    child = start_child("cooperative")
    try:
        stdout = require_pipe(child.stdout, "stdout")
        stdin = require_pipe(child.stdin, "stdin")
        ready = read_line(stdout, READY_TIMEOUT_SECONDS)
        stdin.write('{"op":"ping","request_id":"graceful-ping"}\n')
        stdin.flush()
        ping = read_line(stdout, READY_TIMEOUT_SECONDS)
        stdin.write('{"op":"shutdown","request_id":"graceful-stop"}\n')
        stdin.flush()
        shutdown = read_line(stdout, READY_TIMEOUT_SECONDS)
        return_code = child.wait(timeout=EXIT_TIMEOUT_SECONDS)
        orphan_zero = group_is_gone(child.pid)
        passed = (
            ready.get("type") == "READY"
            and ping.get("value") == "pong"
            and shutdown.get("value") == "shutdown"
            and return_code == 0
            and orphan_zero
        )
        return {
            "case_id": "M0-DUMMY-GRACEFUL",
            "exit_code": return_code,
            "orphan_zero": orphan_zero,
            "result": "PASS" if passed else "FAIL",
        }
    finally:
        stop_if_needed(child)


def terminate_case() -> dict[str, Any]:
    child = start_child("cooperative")
    process_group_id = child.pid
    try:
        stdout = require_pipe(child.stdout, "stdout")
        ready = read_line(stdout, READY_TIMEOUT_SECONDS)
        os.killpg(process_group_id, signal.SIGTERM)
        return_code = child.wait(timeout=EXIT_TIMEOUT_SECONDS)
        orphan_zero = group_is_gone(process_group_id)
        passed = ready.get("type") == "READY" and return_code == -signal.SIGTERM and orphan_zero
        return {
            "case_id": "M0-DUMMY-TERMINATE",
            "exit_code": return_code,
            "orphan_zero": orphan_zero,
            "result": "PASS" if passed else "FAIL",
        }
    finally:
        stop_if_needed(child)


def force_kill_case() -> dict[str, Any]:
    child = start_child("ignore-term")
    process_group_id = child.pid
    escalation_observed = False
    try:
        stdout = require_pipe(child.stdout, "stdout")
        ready = read_line(stdout, READY_TIMEOUT_SECONDS)
        os.killpg(process_group_id, signal.SIGTERM)
        try:
            child.wait(timeout=TERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            escalation_observed = True
            os.killpg(process_group_id, signal.SIGKILL)
        return_code = child.wait(timeout=EXIT_TIMEOUT_SECONDS)
        orphan_zero = group_is_gone(process_group_id)
        passed = (
            ready.get("type") == "READY"
            and escalation_observed
            and return_code == -signal.SIGKILL
            and orphan_zero
        )
        return {
            "case_id": "M0-DUMMY-FORCE-KILL",
            "escalation_observed": escalation_observed,
            "exit_code": return_code,
            "orphan_zero": orphan_zero,
            "result": "PASS" if passed else "FAIL",
        }
    finally:
        stop_if_needed(child)


def main() -> int:
    if sys.version_info < (3, 11):
        print("M0-PACKET-001 requires Python 3.11+", file=sys.stderr)
        return 2
    if os.name != "posix":
        print("M0-PACKET-001 requires POSIX process-group semantics", file=sys.stderr)
        return 2

    started_at = time.time()
    cases = [graceful_case(), terminate_case(), force_kill_case()]
    result = "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL"
    report = {
        "duration_ms": round((time.time() - started_at) * 1000),
        "packet_id": PACKET_ID,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "result": result,
        "schema_version": "1.0",
        "tests": cases,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
