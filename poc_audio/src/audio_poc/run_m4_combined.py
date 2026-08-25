"""Validate the M4 packet or run its local-only deterministic fake suite."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from .m4_packet import (
    FAILURE_ROWS,
    PACKET_ID,
    PUBLICATION_STATUS,
    SESSION_ROWS,
    load_packet,
    validate_fake_result,
    validate_repo_inputs,
)
from .m4_fixture_lock import build_fixture_lock
from .validation import GIT_SHA_RE


ZERO_CLEANUP = {
    "child_processes": 0, "threads": 0, "file_descriptors": 0,
    "iterators": 0, "streams": 0, "device_owners": 0, "clean": True,
}


class PersistentFakeDomain:
    def __init__(self, domain: str) -> None:
        self.domain = domain
        self.process: asyncio.subprocess.Process | None = None
        self.worker_path = Path(__file__).with_name("m4_combined_fake_worker.py")

    async def start(self) -> None:
        if self.process is not None:
            raise RuntimeError(f"M4 fake {self.domain} worker already started")
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, str(self.worker_path), "--domain", self.domain,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        message = await self._read(2.0)
        if message != {"protocol": 1, "event": "ready", "domain": self.domain}:
            raise RuntimeError(f"M4 fake {self.domain} READY mismatch")

    async def run(self, session_id: str) -> None:
        await self._send({"command": "run", "session_id": session_id})
        message = await self._read(2.0)
        if message != {
            "protocol": 1, "event": "result", "domain": self.domain,
            "session_id": session_id,
        }:
            raise RuntimeError(f"M4 fake {self.domain} session result mismatch")

    async def shutdown(self) -> None:
        if self.process is None:
            return
        process = self.process
        if process.returncode is None:
            await self._send({"command": "shutdown"})
            message = await self._read(2.0)
            if message != {"protocol": 1, "event": "shutdown_ack", "domain": self.domain}:
                raise RuntimeError(f"M4 fake {self.domain} shutdown ACK mismatch")
            await asyncio.wait_for(process.wait(), 2.0)
        if process.stdin is not None:
            process.stdin.close()
            await process.stdin.wait_closed()
        if process.stdout is not None:
            await process.stdout.read()
        if process.stderr is not None:
            await process.stderr.read()
        if process.returncode != 0 or _pid_alive(process.pid):
            raise RuntimeError(f"M4 fake {self.domain} worker cleanup failed")
        self.process = None

    async def abort(self) -> None:
        if self.process is None:
            return
        process = self.process
        if process.returncode is None:
            process.kill()
            await process.wait()
        if process.stdin is not None:
            process.stdin.close()
            try:
                await process.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass
        if process.stdout is not None:
            await process.stdout.read()
        if process.stderr is not None:
            await process.stderr.read()
        self.process = None

    async def _read(self, timeout: float) -> dict[str, Any]:
        assert self.process is not None and self.process.stdout is not None
        line = await asyncio.wait_for(self.process.stdout.readline(), timeout)
        if not line:
            raise RuntimeError(f"M4 fake {self.domain} worker closed without an event")
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict):
            raise RuntimeError(f"M4 fake {self.domain} emitted a non-object event")
        return message

    async def _send(self, command: dict[str, str]) -> None:
        assert self.process is not None and self.process.stdin is not None
        self.process.stdin.write((json.dumps(command, sort_keys=True) + "\n").encode("utf-8"))
        await self.process.stdin.drain()


async def _combined_success() -> list[dict[str, Any]]:
    workers = {domain: PersistentFakeDomain(domain) for domain in ("vad", "asr", "tts")}
    sessions: list[dict[str, Any]] = []
    try:
        for worker in workers.values():
            await worker.start()
        for session_id, _category, asr_fixture_id, tts_fixture_id in SESSION_ROWS:
            await workers["vad"].run(session_id)
            await workers["asr"].run(session_id)
            await workers["tts"].run(session_id)
            sessions.append({
                "session_id": session_id,
                "asr_fixture_id": asr_fixture_id,
                "tts_fixture_id": tts_fixture_id,
                "stage_events": [
                    "vad:success", "asr:success", "reasoner:success",
                    "tts:success", "audio_output_completion:fake_success",
                ],
            })
        for worker in workers.values():
            await worker.shutdown()
    finally:
        for worker in workers.values():
            await worker.abort()
    return sessions


async def _failure_case(test_id: str, domain: str, scenario: str) -> dict[str, Any]:
    worker_path = Path(__file__).with_name("m4a_fake_worker.py")
    mode = {
        "error": "error", "timeout": "hang", "cancel": "cancelable",
        "force_abort": "stubborn",
    }[scenario]
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(worker_path), "--mode", mode,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None

    async def read(timeout: float) -> dict[str, Any]:
        line = await asyncio.wait_for(process.stdout.readline(), timeout)
        if not line:
            raise RuntimeError(f"{test_id} worker closed without an event")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"{test_id} emitted a non-object event")
        return value

    async def send(command: dict[str, str]) -> None:
        process.stdin.write((json.dumps(command, sort_keys=True) + "\n").encode("utf-8"))
        await process.stdin.drain()

    terminal = "error"
    force_abort_used = False
    try:
        if (await read(2.0)).get("event") != "ready":
            raise RuntimeError(f"{test_id} missing READY")
        await send({"command": "start", "session_id": test_id})
        if (await read(2.0)).get("event") != "started":
            raise RuntimeError(f"{test_id} missing STARTED")
        await send({"command": "run", "session_id": test_id})
        if scenario == "cancel":
            await asyncio.sleep(0.01)
            await send({"command": "cancel", "session_id": test_id})
        try:
            message = await read(0.08 if scenario in {"timeout", "force_abort"} else 2.0)
            terminal = str(message.get("event"))
            await asyncio.wait_for(process.wait(), 2.0)
        except TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 0.08)
                terminal = "timeout"
            except TimeoutError:
                process.kill()
                await process.wait()
                terminal = "force_aborted"
                force_abort_used = True
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
            force_abort_used = True
        process.stdin.close()
        await process.stdin.wait_closed()
        await process.stdout.read()
        await process.stderr.read()
    expected_terminal = {
        "error": "error", "timeout": "timeout", "cancel": "cancelled",
        "force_abort": "force_aborted",
    }[scenario]
    cleanup = dict(ZERO_CLEANUP)
    if _pid_alive(process.pid):
        cleanup["child_processes"] = 1
        cleanup["clean"] = False

    recovery = PersistentFakeDomain(domain)
    recovery_pass = False
    try:
        await recovery.start()
        await recovery.run(f"{test_id}-RECOVERY")
        await recovery.shutdown()
        recovery_pass = True
    finally:
        await recovery.abort()
    return {
        "test_id": test_id,
        "domain": domain,
        "scenario": scenario,
        "terminal_status": terminal,
        "force_abort_used": force_abort_used,
        "case_pass": terminal == expected_terminal and cleanup["clean"],
        "recovery_pass": recovery_pass,
        "cleanup": cleanup,
    }


async def build_fake_result(source_sha: str) -> dict[str, Any]:
    sessions = await _combined_success()
    failures = [await _failure_case(*row) for row in FAILURE_ROWS]
    result = {
        "schema_version": "1.0",
        "packet_id": PACKET_ID,
        "run_id": "M4-LOCAL-FAKE-COMBINED-001",
        "run_mode": "fake",
        "evidence_eligible": False,
        "publication_status": PUBLICATION_STATUS,
        "source_sha": source_sha,
        "core_sha": None,
        "network_policy": "FAKE_NO_CANDIDATE_OR_HARDWARE_RUNTIME",
        "model_load_counts": {"vad": 1, "asr": 1, "tts": 1},
        "sessions": sessions,
        "failure_injections": failures,
        "cleanup": dict(ZERO_CLEANUP),
        "proposed_disposition": "NOT_HARDWARE_EVIDENCE",
        "decision_boundary": (
            "Local deterministic protocol verification only; this is not Pi, P9 or "
            "Gate 2B evidence and cannot publish a candidate disposition."
        ),
    }
    return result


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "fake", "lock-fixtures"))
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--fixture-lock", type=Path)
    parser.add_argument("--audio-execution-sha")
    args = parser.parse_args()
    packet = load_packet(args.packet)
    validate_repo_inputs(packet, args.repo_root)
    if args.mode == "validate":
        if any(value is not None for value in (
            args.source_sha, args.output, args.fixture_dir, args.fixture_lock,
            args.audio_execution_sha,
        )):
            parser.error("validate does not accept mode-specific arguments")
        print(json.dumps({
            "packet_id": packet["packet_id"], "session_count": 20,
            "failure_injection_count": 12, "formal_execution_authorized": False,
        }, sort_keys=True))
        return 0
    if args.mode == "lock-fixtures":
        if args.source_sha is not None or args.output is not None:
            parser.error("lock-fixtures does not accept --source-sha or --output")
        if args.fixture_dir is None or args.fixture_lock is None or not args.audio_execution_sha:
            parser.error(
                "lock-fixtures requires --fixture-dir, --fixture-lock and --audio-execution-sha"
            )
        if args.fixture_dir.resolve().is_relative_to(args.repo_root.resolve()):
            raise ValueError("M4 controlled fixture directory must remain outside the repository")
        if args.fixture_lock.resolve().is_relative_to(args.repo_root.resolve()):
            raise ValueError("M4 controlled fixture lock must remain outside the repository")
        lock = build_fixture_lock(
            args.repo_root, args.fixture_dir, args.fixture_lock, args.audio_execution_sha,
        )
        print(json.dumps({
            "fixture_count": lock["fixture_count"], "fixture_lock": str(args.fixture_lock),
            "audio_execution_sha": args.audio_execution_sha,
        }, sort_keys=True))
        return 0
    if not args.source_sha or not GIT_SHA_RE.fullmatch(args.source_sha):
        parser.error("fake requires --source-sha as a full 40-character Git SHA")
    if args.output is None:
        parser.error("fake requires --output")
    if args.output.exists():
        raise ValueError("M4 fake output path must be new")
    result = asyncio.run(build_fake_result(args.source_sha))
    validate_fake_result(result, packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, sort_keys=True)
        destination.write("\n")
    print(json.dumps({
        "output": str(args.output), "session_count": len(result["sessions"]),
        "failure_injection_count": len(result["failure_injections"]),
        "proposed_disposition": result["proposed_disposition"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
