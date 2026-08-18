"""Fake-only M4a lifecycle protocol and reusable conformance harness."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .models import CleanupProof, TerminalStatus


Domain = Literal["asr", "tts"]


@dataclass(frozen=True, slots=True)
class ConformanceScenario:
    name: str
    domain: Domain
    worker_mode: str
    timeout_seconds: float
    cancel_after_seconds: float | None = None
    terminate_grace_seconds: float = 0.15


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    schema_version: str
    run_id: str
    source_sha: str
    candidate_id: str
    domain: Domain
    scenario: str
    protocol_version: int
    events: tuple[str, ...]
    started_at_utc: str
    duration_ms: float
    terminal_status: TerminalStatus
    worker_exit_code: int | None
    error_code: str | None
    force_abort_used: bool
    cleanup: CleanupProof

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["terminal_status"] = self.terminal_status.value
        result["events"] = list(self.events)
        result["cleanup"]["clean"] = self.cleanup.clean
        return result


class M4aFakeConformanceHarness:
    """Runs fake protocol scenarios without importing any candidate runtime."""

    def __init__(self, source_sha: str) -> None:
        self._source_sha = source_sha
        self._worker_path = Path(__file__).with_name("m4a_fake_worker.py")

    async def run(self, scenario: ConformanceScenario) -> ConformanceResult:
        started_at = datetime.now(UTC).isoformat()
        started = time.monotonic()
        session_id = f"M4A-{scenario.domain}-{scenario.name}"
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(self._worker_path),
            "--mode",
            scenario.worker_mode,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        events: list[str] = []
        status = TerminalStatus.ERROR
        error_code: str | None = None
        force_abort_used = False
        try:
            ready = await self._read(process, 3.0)
            self._expect(ready, "ready")
            events.append("ready")
            await self._send(process, {"command": "start", "session_id": session_id})
            started_message = await self._read(process, 3.0)
            self._expect(started_message, "started")
            events.append("started")
            await self._send(process, {"command": "run", "session_id": session_id})
            if scenario.cancel_after_seconds is not None:
                await asyncio.sleep(scenario.cancel_after_seconds)
                await self._send(process, {"command": "cancel", "session_id": session_id})
            try:
                terminal = await self._read(process, scenario.timeout_seconds)
            except TimeoutError:
                force_abort_used = await self._terminate(process, scenario)
                status = TerminalStatus.FORCE_ABORTED if force_abort_used else TerminalStatus.TIMEOUT
                error_code = "FORCE_ABORT_TIMEOUT" if force_abort_used else "TIMEOUT"
                events.append(status.value)
            else:
                event = str(terminal.get("event"))
                events.append(event)
                if event == "result":
                    status = TerminalStatus.SUCCESS
                elif event == "error":
                    status = TerminalStatus.ERROR
                    error_code = str(terminal.get("code", "DECLARED_ERROR"))
                elif event == "cancelled":
                    status = TerminalStatus.CANCELLED
                    error_code = "CANCELLED"
                else:
                    status = TerminalStatus.ERROR
                    error_code = "TERMINAL_PROTOCOL_ERROR"
                await self._wait_or_terminate(process, scenario)
        finally:
            if process.returncode is None:
                force_abort_used = await self._terminate(process, scenario)
                if force_abort_used:
                    status = TerminalStatus.FORCE_ABORTED
                    error_code = "FORCE_ABORTED"
                    events.append(status.value)
            await process.stdout.read()
            await process.stderr.read()
        cleanup = CleanupProof(
            child_processes=int(self._pid_alive(process.pid)),
            threads=0,
            iterators=0,
            streams=0,
            device_owners=0,
        )
        return ConformanceResult(
            schema_version="1.0",
            run_id=f"M4A-FAKE-{scenario.domain}-{scenario.name}",
            source_sha=self._source_sha,
            candidate_id="m4a-protocol-fake-v1",
            domain=scenario.domain,
            scenario=scenario.name,
            protocol_version=1,
            events=tuple(events),
            started_at_utc=started_at,
            duration_ms=round((time.monotonic() - started) * 1000, 3),
            terminal_status=status,
            worker_exit_code=process.returncode,
            error_code=error_code,
            force_abort_used=force_abort_used,
            cleanup=cleanup,
        )

    async def _read(self, process: asyncio.subprocess.Process, timeout: float) -> dict[str, Any]:
        assert process.stdout is not None
        line = await asyncio.wait_for(process.stdout.readline(), timeout)
        if not line:
            raise RuntimeError("worker closed stdout without a protocol event")
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict) or message.get("protocol") != 1:
            raise RuntimeError("invalid M4a worker protocol message")
        return message

    @staticmethod
    async def _send(process: asyncio.subprocess.Process, message: dict[str, str]) -> None:
        assert process.stdin is not None
        process.stdin.write((json.dumps(message, sort_keys=True) + "\n").encode("utf-8"))
        await process.stdin.drain()

    @staticmethod
    def _expect(message: dict[str, Any], event: str) -> None:
        if message.get("event") != event:
            raise RuntimeError(f"expected {event} event")

    async def _wait_or_terminate(self, process: asyncio.subprocess.Process, scenario: ConformanceScenario) -> None:
        try:
            await asyncio.wait_for(process.wait(), scenario.terminate_grace_seconds)
        except TimeoutError:
            await self._terminate(process, scenario)

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process, scenario: ConformanceScenario) -> bool:
        if process.returncode is not None:
            return False
        process.terminate()
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
