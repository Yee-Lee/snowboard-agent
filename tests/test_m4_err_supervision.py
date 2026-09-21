"""M4-ERR WP6 process supervision and exit-code regressions."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys

import pytest

from sbd.core.events import ErrorOccurred, ShutdownRequested, StateChanged
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


def _assert_single_fatal_cycle(
    events: list[object], states: list[str], public_roots: list[str]
) -> None:
    assert len(events) == 1
    assert states.count("ERROR") == 1
    assert len(public_roots) == 1


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
async def test_m4_err_pi_004_recovery_failure_is_single_root_exit_4(caplog) -> None:
    key = "core.m4_err_recovery"
    fault = ComponentSystemFault.create(
        where="core.recovery",
        code="GPIO_EVENT_READ_FAILED",
        backend=BackendDisposition.UNPROVEN,
        recovery_keys=(key,),
    )
    events: list[ErrorOccurred] = []
    states: list[str] = []

    class Hook:
        async def rebuild(self, bus, config) -> None:
            raise RuntimeError("PRIVATE_RECOVERY_ROOT")

    def composition(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        async def record_error(event: ErrorOccurred) -> None:
            events.append(event)

        async def record_state(event: StateChanged) -> None:
            states.append(event.new)

        bus.subscribe(ErrorOccurred, record_error, name="m4_err.error_probe")
        bus.subscribe(StateChanged, record_state, name="m4_err.state_probe")
        rm.register(ResourceSpec(
            key=key,
            phase=StartPhase.CORE,
            factory=lambda resolver: _Resource(),
            recoverable=True,
            recovery_hook=Hook(),
        ))

        class Trigger(_Resource):
            async def arm(self) -> None:
                asyncio.create_task(bus.publish(fault.to_event()))

        rm.register(ResourceSpec(
            key="input.m4_err_recovery_trigger",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(),
        ))

    with caplog.at_level("CRITICAL", logger="sbd.main"):
        result = await asyncio.wait_for(run_app(composition=composition), 5)
    assert result == EXIT_RUNTIME_FATAL
    roots = [line for line in caplog.text.splitlines() if "Runtime fatal error" in line]
    _assert_single_fatal_cycle(events, states, roots)
    assert "PRIVATE_RECOVERY_ROOT" not in caplog.text


@pytest.mark.parametrize(
    ("events", "states", "roots"),
    (([1, 2], ["ERROR"], ["root"]), ([1], ["ERROR", "ERROR"], ["root"]),
     ([1], ["ERROR"], ["root", "root"])),
    ids=("second-event", "second-error-cycle", "second-public-root"),
)
def test_m4_err_fatal_double_cycle_negative_control(events, states, roots) -> None:
    with pytest.raises(AssertionError):
        _assert_single_fatal_cycle(events, states, roots)


@pytest.mark.asyncio
async def test_m4_err_pi_008_gpio_startup_acquisition_failure_exits_3() -> None:
    def composition(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        class FailedGPIO(_Resource):
            async def start(self) -> None:
                raise RuntimeError("PRIVATE_GPIO_ACQUISITION")

        rm.register(ResourceSpec(
            key="input.button_gpio_acquisition",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: FailedGPIO(),
            required=True,
        ))

    assert await run_app(composition=composition) == EXIT_STARTUP_ERROR


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    ("config-invalid", "startup-failure", "normal-stop-failure"),
    ids=("config-exit-2", "startup-exit-3", "normal-stop-continues-exit-0"),
)
async def test_m4_err_pu_008_exit_rows(case: str, tmp_path: Path) -> None:
    if case == "config-invalid":
        invalid = tmp_path / "invalid.yaml"
        invalid.write_text("wake: [unterminated", encoding="utf-8")
        assert await run_app(str(invalid)) == EXIT_CONFIG_ERROR
        return

    if case == "startup-failure":
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
        return

    stopped: list[str] = []

    def normal(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)

        class StopFailure(_Resource):
            async def stop(self) -> None:
                stopped.append("failed")
                raise RuntimeError("PRIVATE_STOP_FAILURE")

        class StopAfterFailure(_Resource):
            async def stop(self) -> None:
                stopped.append("continued")

        class Trigger(_Resource):
            async def arm(self) -> None:
                asyncio.create_task(bus.publish(ShutdownRequested()))

        rm.register(ResourceSpec(
            key="core.stop_after_failure",
            phase=StartPhase.CORE,
            factory=lambda resolver: StopAfterFailure(),
        ))
        rm.register(ResourceSpec(
            key="core.stop_failure",
            phase=StartPhase.CORE,
            factory=lambda resolver: StopFailure(),
        ))
        rm.register(ResourceSpec(
            key="input.normal_shutdown",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(),
        ))

    assert await asyncio.wait_for(run_app(composition=normal), 5) == EXIT_SUCCESS
    assert stopped == ["failed", "continued"]


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
