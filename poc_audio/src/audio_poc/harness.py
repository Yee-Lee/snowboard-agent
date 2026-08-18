"""Async subprocess harness with explicit terminal and cleanup semantics."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import CleanupProof, RunResult, TerminalStatus


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    worker_mode: str
    timeout_seconds: float
    cancel_after_seconds: float | None = None
    # A normal SIGTERM must not become a false force-abort on a busy Pi host.
    terminate_grace_seconds: float = 1.0


class FakeProcessHarness:
    def __init__(self, source_sha: str) -> None:
        self._source_sha = source_sha
        self._worker_path = Path(__file__).with_name("fake_worker.py")

    async def run(self, scenario: Scenario) -> RunResult:
        started_at = datetime.now(UTC).isoformat()
        started_monotonic = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(self._worker_path),
            "--mode",
            scenario.worker_mode,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdout is not None
        assert process.stderr is not None

        status = TerminalStatus.ERROR
        error_code: str | None = None
        force_abort_used = False

        try:
            ready = await self._read_message(process, timeout_seconds=3.0)
            if ready.get("event") != "ready":
                error_code = "FAKE_READY_PROTOCOL_ERROR"
                force_abort_used = await self._terminate(process, scenario)
            elif scenario.cancel_after_seconds is not None:
                terminal_task = asyncio.create_task(
                    self._read_message(process, timeout_seconds=scenario.timeout_seconds)
                )
                await asyncio.sleep(scenario.cancel_after_seconds)
                terminal_task.cancel()
                try:
                    await terminal_task
                except asyncio.CancelledError:
                    pass
                force_abort_used = await self._terminate(process, scenario)
                status = (
                    TerminalStatus.FORCE_ABORTED
                    if force_abort_used
                    else TerminalStatus.CANCELLED
                )
                error_code = "FAKE_CANCELLED"
            else:
                try:
                    terminal = await self._read_message(
                        process, timeout_seconds=scenario.timeout_seconds
                    )
                except TimeoutError:
                    force_abort_used = await self._terminate(process, scenario)
                    status = (
                        TerminalStatus.FORCE_ABORTED
                        if force_abort_used
                        else TerminalStatus.TIMEOUT
                    )
                    error_code = (
                        "FAKE_FORCE_ABORTED" if force_abort_used else "FAKE_TIMEOUT"
                    )
                else:
                    event = terminal.get("event")
                    if event == "result":
                        status = TerminalStatus.SUCCESS
                    elif event == "error":
                        status = TerminalStatus.ERROR
                        error_code = str(terminal.get("code", "FAKE_ERROR"))
                    else:
                        status = TerminalStatus.ERROR
                        error_code = "FAKE_TERMINAL_PROTOCOL_ERROR"
                    await self._wait_or_terminate(process, scenario)
        finally:
            if process.returncode is None:
                force_abort_used = await self._terminate(process, scenario)
                if force_abort_used:
                    status = TerminalStatus.FORCE_ABORTED
                    error_code = "FAKE_FORCE_ABORTED"
            await process.stdout.read()
            await process.stderr.read()

        cleanup = CleanupProof(
            child_processes=int(self._pid_alive(process.pid)),
            threads=0,
            iterators=0,
            streams=0,
            device_owners=0,
        )
        return RunResult(
            schema_version="1.0",
            run_id=f"M1-FAKE-{scenario.name}",
            source_sha=self._source_sha,
            candidate_id="deterministic-fake-v1",
            candidate_kind="fake",
            scenario=scenario.name,
            started_at_utc=started_at,
            duration_ms=round((time.monotonic() - started_monotonic) * 1000, 3),
            terminal_status=status,
            worker_exit_code=process.returncode,
            error_code=error_code,
            force_abort_used=force_abort_used,
            cleanup=cleanup,
        )

    async def _read_message(
        self,
        process: asyncio.subprocess.Process,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        assert process.stdout is not None
        line = await asyncio.wait_for(process.stdout.readline(), timeout_seconds)
        if not line:
            raise RuntimeError("fake worker closed stdout without a message")
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict):
            raise RuntimeError("fake worker message is not an object")
        return message

    async def _wait_or_terminate(
        self,
        process: asyncio.subprocess.Process,
        scenario: Scenario,
    ) -> None:
        try:
            await asyncio.wait_for(process.wait(), scenario.terminate_grace_seconds)
        except TimeoutError:
            await self._terminate(process, scenario)

    async def _terminate(
        self,
        process: asyncio.subprocess.Process,
        scenario: Scenario,
    ) -> bool:
        if process.returncode is not None:
            return False
        try:
            process.terminate()
        except ProcessLookupError:
            await process.wait()
            return False
        try:
            await asyncio.wait_for(process.wait(), scenario.terminate_grace_seconds)
            return False
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                await process.wait()
                return False
            await process.wait()
            return True

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
