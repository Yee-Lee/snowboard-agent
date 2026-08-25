"""Locked P9 surrogate client used by the M4 formal reservation runner."""

from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .m3_packet import sha256_file
from .m4_packet import P9_PATHS, P9_PROFILE, P9_SHA256


class P9ProtocolError(RuntimeError):
    pass


class P9Client:
    """One process-group client for the immutable production P9 artifact."""

    def __init__(self, executable: Path, schema: Path, lock: Path, *, self_test: bool = False) -> None:
        self.executable = executable
        self.schema = schema
        self.lock = lock
        self.self_test = self_test
        self.process: subprocess.Popen[str] | None = None
        self.ready: dict[str, Any] | None = None
        self.worker_pids: set[int] = set()
        self._active_infer: tuple[str, list[int]] | None = None

    def verify_artifacts(self) -> None:
        paths = {"runner": self.executable, "schema": self.schema, "lock": self.lock}
        for name, path in paths.items():
            if not path.is_file() or sha256_file(path) != P9_SHA256[name]:
                raise ValueError(f"M4 P9 {name} checksum mismatch")

    def start(self, timeout: float) -> dict[str, Any]:
        if self.process is not None:
            raise RuntimeError("M4 P9 client is already started")
        self.verify_artifacts()
        command = [sys.executable, str(self.executable)]
        if self.self_test:
            command.append("--self-test")
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True, bufsize=1,
        )
        ready = self._read(timeout)
        if ready.get("event") != "READY":
            raise P9ProtocolError("M4 P9 did not become READY")
        if not self.self_test:
            expected = {
                "profile": "production", "reserve_mib": P9_PROFILE["reserve_mib"],
                "cpu_workers": P9_PROFILE["cpu_workers"], "evidence_eligible": True,
            }
            if any(ready.get(name) != value for name, value in expected.items()):
                raise P9ProtocolError("M4 P9 READY profile differs from the locked production profile")
        self.ready = ready
        return ready

    def infer_with_workload(
        self,
        request_id: str,
        workload: Callable[[], Any],
        timeout: float,
    ) -> dict[str, Any]:
        started = self.begin_infer(request_id, timeout)
        workers = started["worker_pids"]
        workload_started = time.monotonic()
        workload_result = workload()
        workload_elapsed_s = time.monotonic() - workload_started
        complete = self.complete_infer(request_id, workers, timeout)
        return {
            "request_id": request_id,
            "worker_pids": workers,
            "workload_elapsed_ms": round(workload_elapsed_s * 1000, 3),
            "workload_result": workload_result,
            "inference_elapsed_s": complete.get("elapsed_s"),
        }

    def begin_infer(self, request_id: str, timeout: float) -> dict[str, Any]:
        """Start one P9 compute interval and prove the worker group is alive."""

        if self.process is None or self.ready is None:
            raise RuntimeError("M4 P9 client is not ready")
        self._send({"op": "INFER", "request_id": request_id})
        started = self._read(timeout)
        if started.get("event") != "INFERENCE_STARTED" or started.get("request_id") != request_id:
            raise P9ProtocolError("M4 P9 INFERENCE_STARTED mismatch")
        workers = started.get("worker_pids")
        expected_worker_count = 2 if self.self_test else P9_PROFILE["cpu_workers"]
        if (
            not isinstance(workers, list) or len(workers) != expected_worker_count
            or not all(isinstance(pid, int) and _pid_alive(pid) for pid in workers)
        ):
            raise P9ProtocolError("M4 P9 worker overlap proof is unavailable")
        self.worker_pids.update(workers)
        self._active_infer = (request_id, workers)
        return {"request_id": request_id, "worker_pids": workers}

    def complete_infer(self, request_id: str, workers: list[int], timeout: float) -> dict[str, Any]:
        """Require the workload to finish before the P9 workers and collect completion."""

        if not all(_pid_alive(pid) for pid in workers):
            raise P9ProtocolError("M4 Audio workload did not complete while P9 workers were alive")
        complete = self._read(timeout)
        if complete.get("event") != "INFERENCE_COMPLETE" or complete.get("request_id") != request_id:
            raise P9ProtocolError("M4 P9 INFERENCE_COMPLETE mismatch")
        if any(_pid_alive(pid) for pid in workers):
            raise P9ProtocolError("M4 P9 worker remained alive after INFERENCE_COMPLETE")
        self._active_infer = None
        return complete

    def shutdown(self, timeout: float) -> dict[str, Any]:
        if self.process is None:
            return {"shutdown": "not_started", "residual_workers": 0}
        process = self.process
        ack: dict[str, Any] = {"event": "NO_SHUTDOWN_ACK"}
        try:
            if process.poll() is None:
                if self._active_infer is not None:
                    request_id, _workers = self._active_infer
                    terminal = self._read(timeout)
                    if terminal.get("event") != "INFERENCE_COMPLETE" or terminal.get("request_id") != request_id:
                        raise P9ProtocolError("M4 P9 could not drain an interrupted INFER")
                    self._active_infer = None
                self._send({"op": "SHUTDOWN"})
                ack = self._read(timeout)
                if ack.get("event") != "SHUTDOWN_ACK" or ack.get("residual_workers") != 0:
                    raise P9ProtocolError("M4 P9 shutdown acknowledgment is invalid")
                process.wait(timeout=timeout)
            else:
                ack = {"event": "PROCESS_ALREADY_EXITED"}
        finally:
            self._terminate_process_group(timeout)
            self._close_streams(process)
            self.process = None
        if process.returncode not in {0, None}:
            raise P9ProtocolError(f"M4 P9 exited with {process.returncode}")
        if any(_pid_alive(pid) for pid in self.worker_pids):
            raise P9ProtocolError("M4 P9 worker residue remains after shutdown")
        return {"shutdown": ack.get("event"), "residual_workers": 0}

    def _send(self, command: dict[str, str]) -> None:
        if self.process is None or self.process.stdin is None:
            raise P9ProtocolError("M4 P9 stdin is unavailable")
        self.process.stdin.write(json.dumps(command, sort_keys=True) + "\n")
        self.process.stdin.flush()

    def _read(self, timeout: float) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None:
            raise P9ProtocolError("M4 P9 stdout is unavailable")
        readable, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not readable:
            raise P9ProtocolError("M4 P9 protocol timed out")
        line = self.process.stdout.readline()
        if not line:
            raise P9ProtocolError(f"M4 P9 closed stdout: {self.process.poll()}")
        event = json.loads(line)
        if not isinstance(event, dict) or event.get("artifact_id") != "M4B-P9-RESIDENCY-SURROGATE-001":
            raise P9ProtocolError("M4 P9 event identity is invalid")
        return event

    def _terminate_process_group(self, timeout: float) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=timeout)
        except ProcessLookupError:
            pass

    @staticmethod
    def _close_streams(process: subprocess.Popen[str]) -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def locked_p9_paths(repo_root: Path) -> dict[str, Path]:
    return {name: repo_root / relative for name, relative in P9_PATHS.items()}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
