"""M1-BOOT-001 and M1-LOG-004 bootstrap supervision checks."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from queue import Empty, Queue
import signal
import subprocess
import sys
from threading import Thread
import time

import pytest

from sbd.main import (
    EXIT_CONFIG_ERROR,
    EXIT_RUNTIME_FATAL,
    EXIT_STARTUP_ERROR,
    EXIT_SUCCESS,
    run_app,
)


SCENARIO_SCRIPT = r"""
import asyncio
import sys

from sbd.core.events import ErrorOccurred
from sbd.core.m1_composition import register_m1_resources
from sbd.core.resource_manager import ResourceSpec, StartPhase
from sbd.main import run_app


class Resource:
    def __init__(self, *, fail_start=False, fail_stop=False):
        self.fail_start = fail_start
        self.fail_stop = fail_stop

    async def start(self):
        if self.fail_start:
            raise RuntimeError("injected startup root")

    async def stop(self):
        if self.fail_stop:
            raise RuntimeError("injected rollback failure")


def startup_composition(rm, bus, config):
    register_m1_resources(rm, bus, config)
    rm.register(ResourceSpec(
        key="core.cleanup",
        phase=StartPhase.CORE,
        factory=lambda resolver: Resource(fail_stop=True),
    ))
    rm.register(ResourceSpec(
        key="core.failure",
        phase=StartPhase.CORE,
        factory=lambda resolver: Resource(fail_start=True),
        required=True,
    ))


def runtime_composition(rm, bus, config):
    register_m1_resources(rm, bus, config)

    async def broken_error_handler(event):
        raise RuntimeError("injected error observer failure")

    bus.subscribe(ErrorOccurred, broken_error_handler, name="injected_fatal")

    class Trigger(Resource):
        async def arm(self):
            loop = asyncio.get_running_loop()

            def publish_fatal():
                task = asyncio.create_task(
                    bus.publish(ErrorOccurred("test.runtime", "injected"))
                )
                task.add_done_callback(
                    lambda completed: None
                    if completed.cancelled()
                    else completed.exception()
                )

            loop.call_soon(publish_fatal)
        async def stop(self):
            sys.stderr.write("RUNTIME_STOP_CALLED\n")


    rm.register(ResourceSpec(
        key="input.runtime_trigger",
        phase=StartPhase.INPUT_PRODUCER,
        factory=lambda resolver: Trigger(),
        required=True,
    ))


scenario = sys.argv[1]
composition = (
    startup_composition if scenario == "startup" else runtime_composition
)
raise SystemExit(asyncio.run(run_app(composition=composition)))
"""


def subprocess_env() -> tuple[Path, dict[str, str]]:
    root = Path(__file__).resolve().parents[1]
    return root, {**os.environ, "PYTHONPATH": str(root / "src")}


def run_scenario(scenario: str) -> subprocess.CompletedProcess[str]:
    root, env = subprocess_env()
    return subprocess.run(
        [sys.executable, "-c", SCENARIO_SCRIPT, scenario],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )


def test_m1_boot_001_malformed_config_returns_exit_2(tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text("wake: [unterminated")
    assert asyncio.run(run_app(str(config))) == EXIT_CONFIG_ERROR


def test_m1_boot_001_malformed_default_config_subprocess_exits_2(
    tmp_path: Path,
) -> None:
    (tmp_path / "config.local.yaml").write_text("wake: [unterminated")
    root, env = subprocess_env()
    result = subprocess.run(
        [sys.executable, "-m", "sbd.main"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == EXIT_CONFIG_ERROR
    assert "Config fatal error" in result.stderr


def test_m1_boot_001_startup_and_rollback_failure_subprocess_exits_3() -> None:
    result = run_scenario("startup")
    assert result.returncode == EXIT_STARTUP_ERROR
    assert "injected startup root" in result.stderr
    assert "injected rollback failure" in result.stderr


def test_m1_boot_001_runtime_bus_fatal_subprocess_exits_4() -> None:
    result = run_scenario("runtime")
    assert result.returncode == EXIT_RUNTIME_FATAL
    assert "Runtime fatal error" in result.stderr
    assert result.stderr.count("CRITICAL") == 1
    assert "RUNTIME_STOP_CALLED" not in result.stderr


@pytest.mark.parametrize("shutdown_signal", [signal.SIGINT, signal.SIGTERM])
def test_m1_boot_001_signal_subprocess_exits_cleanly(
    tmp_path: Path,
    shutdown_signal: signal.Signals,
) -> None:
    """The process-level signal bridge publishes exactly normal shutdown."""
    root, env = subprocess_env()
    process = subprocess.Popen([sys.executable, "-m", "sbd.main"], cwd=tmp_path, env=env, stderr=subprocess.PIPE, text=True)
    assert process.stderr is not None

    q: Queue[str] = Queue()

    def _read_stderr(stream, queue):
        for line in iter(stream.readline, ""):
            queue.put(line)
        stream.close()

    reader_thread = Thread(target=_read_stderr, args=(process.stderr, q), daemon=True)
    reader_thread.start()

    try:
        deadline = time.monotonic() + 10
        is_ready = False
        stderr_captured = []
        while time.monotonic() < deadline:
            try:
                line = q.get(timeout=0.1)
                stderr_captured.append(line)
                if "M1 runtime ready" in line:
                    is_ready = True
                    break
            except Empty:
                if process.poll() is not None:
                    break

        assert is_ready, f"runtime did not become ready; captured stderr:\n{''.join(stderr_captured)}"
        process.send_signal(shutdown_signal)
        assert process.wait(timeout=5) == EXIT_SUCCESS
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
