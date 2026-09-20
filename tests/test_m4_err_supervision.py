"""M4-ERR WP6 process supervision and exit-code regressions."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys

import pytest

from sbd.core.events import ShutdownRequested
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.lifecycle import TerminationProofError
from sbd.core.m1_composition import register_m1_resources
from sbd.core.resource_manager import ResourceSpec, StartPhase
from sbd.main import (
    EXIT_CONFIG_ERROR,
    EXIT_RUNTIME_FATAL,
    EXIT_STARTUP_ERROR,
    EXIT_SUCCESS,
    run_app,
)


class _Resource:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class _UnprovenTermination(_Resource):
    async def stop(self) -> None:
        raise TerminationProofError("termination proof missing")


@pytest.mark.asyncio
async def test_m4_err_pu_008_shutdown_termination_proof_failure_exits_4() -> None:
    def composition(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)
        rm.register(ResourceSpec(
            key="core.unproven_termination",
            phase=StartPhase.CORE,
            factory=lambda resolver: _UnprovenTermination(),
        ))

        class Trigger(_Resource):
            async def arm(self) -> None:
                asyncio.create_task(bus.publish(ShutdownRequested()))

        rm.register(ResourceSpec(
            key="input.shutdown_trigger",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(),
            required=True,
        ))

    assert await asyncio.wait_for(run_app(composition=composition), 5) == EXIT_RUNTIME_FATAL


@pytest.mark.asyncio
async def test_m4_err_pi_004_unproven_event_without_recovery_hook_exits_4() -> None:
    fault = ComponentSystemFault.create(
        where="core.gpio",
        code="GPIO_EVENT_READ_FAILED",
        backend=BackendDisposition.UNPROVEN,
        recovery_keys=("core.gpio",),
    )

    def composition(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        class Trigger(_Resource):
            async def arm(self) -> None:
                asyncio.create_task(bus.publish(fault.to_event()))

        rm.register(ResourceSpec(
            key="input.unproven_fault",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(),
        ))

    assert await asyncio.wait_for(run_app(composition=composition), 5) == EXIT_RUNTIME_FATAL


@pytest.mark.asyncio
async def test_m4_err_pu_008_config_startup_and_normal_exit_codes(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("wake: [unterminated", encoding="utf-8")
    assert await run_app(str(invalid)) == EXIT_CONFIG_ERROR

    def startup_failure(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        class Failed(_Resource):
            async def start(self) -> None:
                raise RuntimeError("PRIVATE_STARTUP_ROOT")

        rm.register(ResourceSpec(
            key="core.failed",
            phase=StartPhase.CORE,
            factory=lambda resolver: Failed(),
        ))

    assert await run_app(composition=startup_failure) == EXIT_STARTUP_ERROR

    def normal(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        class Trigger(_Resource):
            async def arm(self) -> None:
                asyncio.create_task(bus.publish(ShutdownRequested()))

        rm.register(ResourceSpec(
            key="input.normal_shutdown",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(),
        ))

    assert await asyncio.wait_for(run_app(composition=normal), 5) == EXIT_SUCCESS


def test_m4_err_ps_001_startup_rollback_subprocess_is_reverse_and_single_root() -> None:
    root = Path(__file__).resolve().parents[1]
    script = r'''
import asyncio
import sys
from sbd.core.events import ErrorOccurred
from sbd.core.m1_composition import register_m1_resources
from sbd.core.resource_manager import ResourceSpec, StartPhase
from sbd.main import run_app

class Resource:
    def __init__(self, name, fail=False): self.name, self.fail = name, fail
    async def start(self):
        if self.fail: raise RuntimeError("M4_ERR_STARTUP_ROOT")
    async def stop(self): sys.stderr.write("ROLLBACK_" + self.name + "\n")

def composition(rm, bus, config):
    register_m1_resources(rm, bus, config)
    async def unexpected(event): sys.stderr.write("ERROR_EVENT\n")
    bus.subscribe(ErrorOccurred, unexpected, name="startup_error_probe")
    for key, fail in (("core.rollback_a", False), ("core.rollback_b", False),
                      ("core.rollback_failure", True)):
        rm.register(ResourceSpec(key=key, phase=StartPhase.CORE,
            factory=lambda resolver, key=key, fail=fail: Resource(key, fail)))

raise SystemExit(asyncio.run(run_app(composition=composition)))
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == EXIT_STARTUP_ERROR
    assert result.stderr.index("ROLLBACK_core.rollback_b") < result.stderr.index(
        "ROLLBACK_core.rollback_a"
    )
    assert result.stderr.count("M4_ERR_STARTUP_ROOT") == 1
    assert "ERROR_EVENT" not in result.stderr
