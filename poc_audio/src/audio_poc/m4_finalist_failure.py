"""Finalist lifecycle adapters for the formal M4 failure catalog.

The adapter creates a new persistent finalist for every case, observes one
injected terminal state, then reopens the same finalist for a controlled probe.
It never serializes raw audio, PCM, or transcripts.
"""

from __future__ import annotations

import asyncio
import os
import select
import signal
import subprocess
import sys
from collections.abc import Callable
from typing import Any, Protocol

from .m3_formal_hal import cleanup_delta, runtime_snapshot
from .m4_failure import FORCE_ABORT_SOURCE


class ActualFailureDomain(Protocol):
    async def start(self) -> None: ...
    async def run(self, session: dict[str, Any]) -> dict[str, Any]: ...
    async def stop(self) -> None: ...
    async def inject_error(self) -> None: ...
    async def abort_active(self) -> None: ...


class FinalistFailureAdapter:
    """Execute actual-finalist error/timeout/cancel plus controlled abort proof."""

    def __init__(self, domain: str, factory: Callable[[], ActualFailureDomain],
                 operation_start_grace_s: float, abort_grace_s: float) -> None:
        if domain not in {"vad", "asr", "tts"}:
            raise ValueError("M4 failure adapter domain is invalid")
        if operation_start_grace_s <= 0 or abort_grace_s <= 0:
            raise ValueError("M4 failure adapter timeouts must be positive")
        self.domain = domain
        self.factory = factory
        self.operation_start_grace_s = operation_start_grace_s
        self.abort_grace_s = abort_grace_s

    async def inject(self, scenario: str, probe: dict[str, Any]) -> dict[str, Any]:
        if scenario == "force_abort":
            # The double is deliberately bounded and short. Keeping it on this
            # controller thread avoids forking a Python worker from an executor
            # thread, which is unsafe on the target runtime.
            return _controlled_force_abort(self.domain, self.abort_grace_s)
        if scenario not in {"error", "timeout", "cancel"}:
            raise ValueError(f"M4 unsupported failure scenario: {scenario}")
        before = runtime_snapshot()
        instance = self.factory()
        try:
            await instance.start()
            if scenario == "error":
                await instance.inject_error()
                terminal = "ERROR"
            else:
                operation_probe = probe.get("_failure_probe", probe)
                if not isinstance(operation_probe, dict):
                    raise ValueError("M4 failure operation probe is invalid")
                operation = asyncio.create_task(instance.run(operation_probe), name=f"m4-{self.domain}-{scenario}")
                await asyncio.sleep(self.operation_start_grace_s)
                if operation.done():
                    await operation
                    raise RuntimeError(f"M4 {self.domain} completed before {scenario} injection")
                await instance.abort_active()
                try:
                    await asyncio.wait_for(operation, self.abort_grace_s)
                except (asyncio.CancelledError, Exception):
                    pass
                if not operation.done():
                    operation.cancel()
                    await asyncio.gather(operation, return_exceptions=True)
                    raise RuntimeError(f"M4 {self.domain} operation survived {scenario} abort")
                terminal = "TIMEOUT" if scenario == "timeout" else "CANCELLED"
        finally:
            try:
                await instance.stop()
            except Exception:
                # abort_active is permitted to have already consumed the worker.
                pass
        return {
            "terminal_status": terminal, "injection_source": "ACTUAL_FINALIST",
            "injection_observed": True, "force_abort_used": False,
            "cleanup": cleanup_delta(before, runtime_snapshot()),
        }

    async def recover(self, probe: dict[str, Any]) -> dict[str, Any]:
        before = runtime_snapshot()
        instance = self.factory()
        try:
            await instance.start()
            result = await instance.run(probe)
            if result.get("terminal") != "SUCCESS":
                raise RuntimeError(f"M4 {self.domain} recovery terminal is invalid")
        finally:
            await instance.stop()
        return {
            "terminal_status": "SUCCESS", "same_finalist": True,
            "cleanup": cleanup_delta(before, runtime_snapshot()),
        }


def _controlled_force_abort(domain: str, grace_s: float) -> dict[str, Any]:
    before = runtime_snapshot()
    process = subprocess.Popen(
        [sys.executable, "-m", "audio_poc.m4_force_abort_double", "--domain", domain],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True,
    )
    if process.stdout is None:
        raise RuntimeError("M4 controlled force-abort double stdout is unavailable")
    ready, _, _ = select.select([process.stdout], [], [], grace_s)
    if not ready or process.stdout.readline().strip() != f"READY\t{FORCE_ABORT_SOURCE}\t{domain}":
        _kill_group(process)
        raise RuntimeError("M4 controlled force-abort double did not become READY")
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=grace_s)
        raise RuntimeError("M4 controlled force-abort double unexpectedly honored SIGTERM")
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=grace_s)
    finally:
        process.stdout.close()
    return {
        "terminal_status": "FORCE_ABORTED", "injection_source": FORCE_ABORT_SOURCE,
        "injection_observed": True, "force_abort_used": True,
        "cleanup": cleanup_delta(before, runtime_snapshot()),
    }


def _kill_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2.0)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
