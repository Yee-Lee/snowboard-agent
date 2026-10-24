from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "poc_llm/tools/run_p9_residency_surrogate.py"
SCHEMA = ROOT / "poc_llm/schemas/p9_residency_surrogate_protocol.schema.json"
LOCK = ROOT / "poc_llm/harness/p9-residency-surrogate-lock-v1.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("p9_surrogate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_event(process: subprocess.Popen[str], timeout_s: float = 4.0) -> dict:
    assert process.stdout is not None
    deadline = time.monotonic() + timeout_s
    fd = process.stdout.fileno()
    while time.monotonic() < deadline:
        import select

        readable, _, _ = select.select([fd], [], [], min(0.1, deadline - time.monotonic()))
        if readable:
            line = process.stdout.readline()
            if line:
                return json.loads(line)
    raise AssertionError("timed out waiting for surrogate event")


class P9ResidencySurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processes: list[subprocess.Popen[str]] = []

    def tearDown(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()

    def _start(self) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "--self-test"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.processes.append(process)
        return process

    @staticmethod
    def _send(process: subprocess.Popen[str], command: dict) -> None:
        assert process.stdin is not None
        process.stdin.write(json.dumps(command) + "\n")
        process.stdin.flush()

    def test_production_profile_is_exact_and_not_cli_tunable(self) -> None:
        module = _load_module()
        profile = module.PRODUCTION_PROFILE
        self.assertEqual(profile.reserve_mib, 2304)
        self.assertEqual(profile.cpu_workers, 4)
        self.assertEqual(profile.startup_delay_s, 6.0)
        self.assertEqual(profile.inference_duration_s, 6.0)
        self.assertEqual(profile.ready_timeout_s, 10.0)
        rejected = subprocess.run(
            [sys.executable, str(SCRIPT), "--reserve-mib", "1"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)

    def test_protocol_schema_locks_commands_and_events(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$defs"]["command"]["oneOf"][1]["properties"]["op"]["const"], "INFER")
        events = schema["$defs"]["event"]["properties"]["event"]["enum"]
        self.assertEqual(
            events,
            ["READY", "PONG", "INFERENCE_STARTED", "INFERENCE_COMPLETE", "ERROR", "SHUTDOWN_ACK"],
        )

    def test_lock_authenticates_executable_schema_and_profile(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        module = _load_module()
        self.assertEqual(lock["artifact_id"], module.ARTIFACT_ID)
        self.assertEqual(lock["profile"], {
            "cpu_workers": 4,
            "inference_duration_s": 6.0,
            "ready_timeout_s": 10.0,
            "reserve_mib": 2304,
            "shutdown_timeout_s": 5.0,
            "startup_delay_s": 6.0,
        })
        for relative_path, expected in lock["sha256"].items():
            observed = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(observed, expected, relative_path)

    def test_self_test_protocol_runs_workers_and_cleans_up(self) -> None:
        process = self._start()
        ready = _read_event(process)
        self.assertEqual(ready["event"], "READY")
        self.assertFalse(ready["evidence_eligible"])
        self.assertEqual(ready["cpu_workers"], 2)

        self._send(process, {"op": "PING"})
        self.assertEqual(_read_event(process)["event"], "PONG")

        self._send(process, {"op": "INFER", "request_id": "test-turn-1"})
        started = _read_event(process)
        self.assertEqual(started["event"], "INFERENCE_STARTED")
        self.assertEqual(len(started["worker_pids"]), 2)
        for worker_pid in started["worker_pids"]:
            self.assertTrue(Path(f"/proc/{worker_pid}").exists())
            self.assertEqual(os.getpgid(worker_pid), ready["pgid"])
        complete = _read_event(process)
        self.assertEqual(complete["event"], "INFERENCE_COMPLETE")
        self.assertGreaterEqual(complete["elapsed_s"], 0.75)
        for worker_pid in started["worker_pids"]:
            self.assertFalse(Path(f"/proc/{worker_pid}").exists())

        self._send(process, {"op": "SHUTDOWN"})
        shutdown = _read_event(process)
        self.assertEqual(shutdown["event"], "SHUTDOWN_ACK")
        self.assertEqual(shutdown["residual_workers"], 0)
        self.assertEqual(process.wait(timeout=2), 0)

    def test_invalid_command_is_bounded_and_process_remains_ready(self) -> None:
        process = self._start()
        self.assertEqual(_read_event(process)["event"], "READY")
        self._send(process, {"op": "UNKNOWN"})
        error = _read_event(process)
        self.assertEqual(error["event"], "ERROR")
        self.assertEqual(error["code"], "UNKNOWN_COMMAND")
        self._send(process, {"op": "PING"})
        self.assertEqual(_read_event(process)["event"], "PONG")
        self._send(process, {"op": "SHUTDOWN"})
        self.assertEqual(_read_event(process)["event"], "SHUTDOWN_ACK")
        self.assertEqual(process.wait(timeout=2), 0)

    def test_production_host_preflight_fails_closed_off_target(self) -> None:
        if sys.platform == "linux" and os.uname().machine.lower() in {"aarch64", "arm64"}:
            self.skipTest("target host requires its real swap preflight")
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            text=True,
            capture_output=True,
            check=False,
        )
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(result.returncode, 3)
        self.assertEqual([event["event"] for event in events], ["ERROR", "SHUTDOWN_ACK"])
        self.assertEqual(events[0]["code"], "HOST_PREFLIGHT_FAILED")


if __name__ == "__main__":
    unittest.main()
