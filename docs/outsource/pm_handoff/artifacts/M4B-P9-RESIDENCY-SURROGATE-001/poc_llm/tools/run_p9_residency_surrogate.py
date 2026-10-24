#!/usr/bin/env python3
"""Versioned M4b residency surrogate for Audio M4A-P9.

The production profile is intentionally not operator-tunable.  ``--self-test``
uses a small, clearly labelled profile for deterministic protocol regression;
its output is never hardware evidence.
"""

from __future__ import annotations

import argparse
import json
import mmap
import os
import platform
import select
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, TextIO


ARTIFACT_ID = "M4B-P9-RESIDENCY-SURROGATE-001"
PROTOCOL_VERSION = "1.0"
PAGE_SIZE = mmap.PAGESIZE
WORKER_TOKEN = "m4b-p9-worker-v1"


@dataclass(frozen=True)
class Profile:
    name: str
    reserve_mib: int
    cpu_workers: int
    startup_delay_s: float
    inference_duration_s: float
    ready_timeout_s: float
    shutdown_timeout_s: float


PRODUCTION_PROFILE = Profile(
    name="production",
    reserve_mib=2304,
    cpu_workers=4,
    startup_delay_s=6.0,
    inference_duration_s=6.0,
    ready_timeout_s=10.0,
    shutdown_timeout_s=5.0,
)

SELF_TEST_PROFILE = Profile(
    name="self-test-non-evidence",
    reserve_mib=16,
    cpu_workers=2,
    startup_delay_s=0.1,
    inference_duration_s=0.8,
    ready_timeout_s=3.0,
    shutdown_timeout_s=2.0,
)


class SurrogateError(RuntimeError):
    """A bounded surrogate execution failure."""


def _emit(stream: TextIO, event: str, **fields: Any) -> None:
    record = {
        "artifact_id": ARTIFACT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "event": event,
        "monotonic_s": round(time.monotonic(), 6),
        **fields,
    }
    stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush()


def _read_swap_total_kib() -> int:
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("SwapTotal:"):
                return int(line.split()[1])
    raise SurrogateError("SwapTotal is absent from /proc/meminfo")


def _validate_production_host() -> None:
    if sys.platform != "linux":
        raise SurrogateError("production profile requires Linux")
    machine = platform.machine().lower()
    if machine not in {"aarch64", "arm64"}:
        raise SurrogateError(f"production profile requires aarch64, observed {machine}")
    swap_total_kib = _read_swap_total_kib()
    if swap_total_kib != 0:
        raise SurrogateError(
            f"production profile requires swap=0, observed SwapTotal={swap_total_kib} KiB"
        )


def _become_process_group_leader() -> None:
    if os.getpgrp() != os.getpid():
        os.setsid()


def _allocate_and_touch(reserve_mib: int) -> mmap.mmap:
    total_bytes = reserve_mib * 1024 * 1024
    allocation = mmap.mmap(
        -1,
        total_bytes,
        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    )
    for offset in range(0, total_bytes, PAGE_SIZE):
        allocation[offset] = 1
    allocation[total_bytes - 1] = 1
    return allocation


def _cpu_worker(duration_s: float) -> int:
    deadline = time.monotonic() + duration_s
    value = 0x5A17
    while time.monotonic() < deadline:
        value = ((value * 1103515245) + 12345) & 0x7FFFFFFF
    return 0 if value >= 0 else 1


class ResidencySurrogate:
    def __init__(self, profile: Profile, stdout: TextIO) -> None:
        self.profile = profile
        self.stdout = stdout
        self.running = True
        self.allocation: mmap.mmap | None = None
        self.workers: list[subprocess.Popen[bytes]] = []
        self.exit_code = 0

    def request_stop(self, _signum: int, _frame: Any) -> None:
        self.running = False

    def _start_workers(self) -> None:
        command = [
            sys.executable,
            os.path.abspath(__file__),
            "--_cpu-worker",
            str(self.profile.inference_duration_s),
            "--_worker-token",
            WORKER_TOKEN,
        ]
        self.workers = [
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            for _ in range(self.profile.cpu_workers)
        ]

    def _stop_workers(self) -> None:
        deadline = time.monotonic() + self.profile.shutdown_timeout_s
        for worker in self.workers:
            if worker.poll() is None:
                worker.terminate()
        for worker in self.workers:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                worker.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
        self.workers.clear()

    def _run_inference(self, request_id: str) -> None:
        started = time.monotonic()
        self._start_workers()
        _emit(
            self.stdout,
            "INFERENCE_STARTED",
            request_id=request_id,
            worker_pids=[worker.pid for worker in self.workers],
            cpu_workers=self.profile.cpu_workers,
            duration_s=self.profile.inference_duration_s,
        )
        while self.running and any(worker.poll() is None for worker in self.workers):
            time.sleep(0.02)
        if not self.running:
            self._stop_workers()
            return
        return_codes = [worker.wait() for worker in self.workers]
        self.workers.clear()
        if any(code != 0 for code in return_codes):
            raise SurrogateError(f"CPU worker failure: {return_codes}")
        _emit(
            self.stdout,
            "INFERENCE_COMPLETE",
            request_id=request_id,
            elapsed_s=round(time.monotonic() - started, 6),
        )

    def _handle_command(self, line: str) -> None:
        try:
            command = json.loads(line)
        except json.JSONDecodeError as exc:
            _emit(self.stdout, "ERROR", code="INVALID_JSON", detail=str(exc))
            return
        if not isinstance(command, dict) or set(command) - {"op", "request_id"}:
            _emit(self.stdout, "ERROR", code="INVALID_COMMAND", detail="unexpected command shape")
            return
        operation = command.get("op")
        if operation == "PING" and set(command) == {"op"}:
            _emit(self.stdout, "PONG")
        elif operation == "INFER" and set(command) == {"op", "request_id"}:
            request_id = command["request_id"]
            if not isinstance(request_id, str) or not request_id:
                _emit(self.stdout, "ERROR", code="INVALID_REQUEST_ID", detail="non-empty string required")
                return
            self._run_inference(request_id)
        elif operation == "SHUTDOWN" and set(command) == {"op"}:
            self.running = False
        else:
            _emit(self.stdout, "ERROR", code="UNKNOWN_COMMAND", detail="expected PING, INFER, or SHUTDOWN")

    def run(self) -> int:
        started = time.monotonic()
        try:
            _become_process_group_leader()
            self.allocation = _allocate_and_touch(self.profile.reserve_mib)
            delay_remaining = self.profile.startup_delay_s - (time.monotonic() - started)
            if delay_remaining > 0:
                time.sleep(delay_remaining)
            ready_elapsed = time.monotonic() - started
            if ready_elapsed > self.profile.ready_timeout_s:
                raise SurrogateError(
                    f"READY exceeded {self.profile.ready_timeout_s}s: {ready_elapsed:.3f}s"
                )
            _emit(
                self.stdout,
                "READY",
                pid=os.getpid(),
                pgid=os.getpgrp(),
                profile=self.profile.name,
                reserve_mib=self.profile.reserve_mib,
                cpu_workers=self.profile.cpu_workers,
                startup_delay_s=self.profile.startup_delay_s,
                inference_duration_s=self.profile.inference_duration_s,
                evidence_eligible=self.profile.name == "production",
            )
            while self.running:
                readable, _, _ = select.select([sys.stdin], [], [], 0.2)
                if not readable:
                    continue
                line = sys.stdin.readline()
                if line == "":
                    raise SurrogateError("stdin closed before SHUTDOWN")
                self._handle_command(line)
        except (OSError, ValueError, SurrogateError) as exc:
            self.exit_code = 3
            _emit(self.stdout, "ERROR", code="SURROGATE_FAILURE", detail=str(exc))
        finally:
            self._stop_workers()
            if self.allocation is not None:
                self.allocation.close()
                self.allocation = None
            _emit(self.stdout, "SHUTDOWN_ACK", exit_code=self.exit_code, residual_workers=0)
        return self.exit_code


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="use the small non-evidence protocol regression profile",
    )
    parser.add_argument("--_cpu-worker", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--_worker-token", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args._cpu_worker is not None:
        if args._worker_token != WORKER_TOKEN or args._cpu_worker <= 0:
            return 2
        return _cpu_worker(args._cpu_worker)
    profile = SELF_TEST_PROFILE if args.self_test else PRODUCTION_PROFILE
    if profile is PRODUCTION_PROFILE:
        try:
            _validate_production_host()
        except (OSError, ValueError, SurrogateError) as exc:
            _emit(sys.stdout, "ERROR", code="HOST_PREFLIGHT_FAILED", detail=str(exc))
            _emit(sys.stdout, "SHUTDOWN_ACK", exit_code=3, residual_workers=0)
            return 3
    surrogate = ResidencySurrogate(profile, sys.stdout)
    signal.signal(signal.SIGTERM, surrogate.request_stop)
    signal.signal(signal.SIGINT, surrogate.request_stop)
    return surrogate.run()


if __name__ == "__main__":
    raise SystemExit(main())
