"""Workstation try-run for M4C-PI-S05 application shutdown."""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from sbd.core.display import DisplayArbiter
from sbd.core.display.lifecycle import DisplayLifecycle
from sbd.core.events import ShutdownRequested
from sbd.core.m3_composition import M3Composition
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase
from sbd.core.state_manager import StateManager
from sbd.main import EXIT_SUCCESS, run_app


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m4c_s05_oracle", ROOT / "scripts/m4c_s05_oracle.py"
)
assert SPEC is not None and SPEC.loader is not None
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def _valid_evidence() -> dict:
    return {
        "schema_version": 1,
        "variant": "APP_EXIT",
        "application_exit_code": 0,
        "shutdown_signal_count": 1,
        "wake_entry_count": 0,
        "shutdown_blank_seen": True,
        "blank_before_display_close": True,
        "stop_failure_count": 0,
        "surviving_native_child_count": 0,
    }


def test_s05_oracle_accepts_clean_application_exit() -> None:
    public = ORACLE.validate_s05_private_evidence(_valid_evidence())
    assert public == {
        "schema_version": 1,
        "scenario_code": "M4C-PI-S05/APP_EXIT",
        "status_code": "APPLICATION_EXITED",
        "application_exit_code": 0,
        "session_accepted": False,
        "shutdown_blank_before_display_close": True,
        "stop_failure_count": 0,
        "surviving_native_child_count": 0,
    }


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("application_exit_code", 4, "M4C_S05_EXIT_NONZERO"),
        ("shutdown_signal_count", 0, "M4C_S05_SHUTDOWN_SIGNAL_INVALID"),
        ("wake_entry_count", 1, "M4C_S05_SESSION_ACCEPTED"),
        ("shutdown_blank_seen", False, "M4C_S05_SHUTDOWN_BLANK_MISSING"),
        ("blank_before_display_close", False,
         "M4C_S05_DISPLAY_CLOSED_BEFORE_BLANK"),
        ("stop_failure_count", 1, "M4C_S05_RESOURCE_STOP_FAILED"),
        ("surviving_native_child_count", 1,
         "M4C_S05_NATIVE_CHILD_SURVIVED"),
    ],
)
def test_s05_oracle_rejects_direct_product_risk(
    field: str, value: object, code: str
) -> None:
    evidence = copy.deepcopy(_valid_evidence())
    evidence[field] = value
    with pytest.raises(ORACLE.S05OracleError, match=code):
        ORACLE.validate_s05_private_evidence(evidence)


class _LongPressTrigger:
    def __init__(self, bus, observation: dict[str, object]) -> None:
        self._bus = bus
        self._observation = observation

    async def start(self) -> None:
        pass

    async def arm(self) -> None:
        self._observation["shutdown_signal_count"] += 1
        await self._bus.publish(ShutdownRequested())

    async def stop(self) -> None:
        pass


class _TryRunComposition:
    def __init__(self, observation: dict[str, object]) -> None:
        self._product = M3Composition()
        self._observation = observation

    def __call__(self, rm, bus, config) -> None:
        self._product(rm, bus, config)
        rm.register(ResourceSpec(
            key="input.s05_long_press",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: _LongPressTrigger(bus, self._observation),
        ))


def test_s05_workstation_tryrun_uses_real_top_level_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = _valid_evidence()
    observation.update(
        application_exit_code=-1,
        shutdown_signal_count=0,
        shutdown_blank_seen=False,
        blank_before_display_close=False,
        stop_failure_count=-1,
    )

    original_shutdown = DisplayLifecycle.begin_shutdown
    original_display_stop = DisplayArbiter.stop
    original_stop_all = ResourceManager.stop_all
    original_enter_wake = StateManager._enter_wake

    def observed_shutdown(self: DisplayLifecycle) -> bool:
        accepted = original_shutdown(self)
        snapshot = self._arbiter.snapshot()
        observation["shutdown_blank_seen"] = bool(
            accepted
            and snapshot.fullscreen is not None
            and snapshot.fullscreen.template == "fullscreen.blank"
        )
        return accepted

    async def observed_display_stop(self: DisplayArbiter) -> None:
        snapshot = self.snapshot()
        observation["blank_before_display_close"] = bool(
            observation["shutdown_blank_seen"]
            and snapshot.fullscreen is not None
            and snapshot.fullscreen.template == "fullscreen.blank"
        )
        await original_display_stop(self)

    async def observed_stop_all(self: ResourceManager):
        report = await original_stop_all(self)
        observation["stop_failure_count"] = len(report.failures)
        return report

    async def observed_enter_wake(self: StateManager, *args, **kwargs) -> None:
        observation["wake_entry_count"] += 1
        await original_enter_wake(self, *args, **kwargs)

    monkeypatch.setattr(DisplayLifecycle, "begin_shutdown", observed_shutdown)
    monkeypatch.setattr(DisplayArbiter, "stop", observed_display_stop)
    monkeypatch.setattr(ResourceManager, "stop_all", observed_stop_all)
    monkeypatch.setattr(StateManager, "_enter_wake", observed_enter_wake)

    async def exercise() -> int:
        return await asyncio.wait_for(
            run_app(composition=_TryRunComposition(observation)), timeout=5
        )

    result = asyncio.run(exercise())
    observation["application_exit_code"] = result

    assert result == EXIT_SUCCESS
    ORACLE.validate_s05_private_evidence(observation)


def test_s05_application_child_records_result_after_top_level_exit(
    tmp_path: Path,
) -> None:
    observation_path = tmp_path / "application-observation.json"
    ready_path = tmp_path / "application-ready"
    process = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts/m4c_s05_app.py"),
            "--config", str(tmp_path / "default-config.yaml"),
            "--observation", str(observation_path),
            "--ready", str(ready_path),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "SBD_M4C_TEST_ID": "M4C-PI-S05",
            "SBD_M4C_VARIANT": "APP_EXIT",
            "SBD_M4C_CONFIG": "/private/coordinator-only.yaml",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 5
        while not ready_path.is_file() and process.poll() is None:
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert ready_path.is_file()
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert process.returncode == 0
    evidence = json.loads(observation_path.read_text(encoding="utf-8"))
    evidence["surviving_native_child_count"] = 0
    ORACLE.validate_s05_private_evidence(evidence)
