"""Bounded Audio Protocol v1 framing and top-level child ownership."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import signal
import tempfile
from collections.abc import Callable, Mapping
from enum import Enum, auto
from pathlib import Path
from typing import Any

from sbd.adaptor.errors import AdapterError


PROTOCOL_VERSION = 1
MAX_CONTROL_BYTES = 16 * 1024
MAX_PCM_BYTES = 64 * 1024 * 1024
SHA256_LENGTH = 64


class AudioProtocolError(AdapterError):
    """The child violated Audio Protocol v1."""


class ChildState(Enum):
    STOPPED = auto()
    STARTING = auto()
    READY = auto()
    BUSY = auto()
    DESTROYED = auto()


def encode_control(value: Mapping[str, Any]) -> bytes:
    if value.get("protocol") != PROTOCOL_VERSION:
        raise AudioProtocolError("outgoing message must declare Audio Protocol v1")
    try:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as error:
        raise AudioProtocolError("outgoing control message is not JSON encodable") from error
    if len(payload) > MAX_CONTROL_BYTES:
        raise AudioProtocolError("control message exceeds 16 KiB")
    return payload


async def read_control(reader: asyncio.StreamReader) -> dict[str, Any]:
    try:
        raw = await reader.readuntil(b"\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as error:
        raise AudioProtocolError("child control stream ended or exceeded its bound") from error
    if len(raw) > MAX_CONTROL_BYTES:
        raise AudioProtocolError("control message exceeds 16 KiB")
    try:
        value = json.loads(raw[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AudioProtocolError("child control message is invalid UTF-8/JSON") from error
    if not isinstance(value, dict) or value.get("protocol") != PROTOCOL_VERSION:
        raise AudioProtocolError("child control message is not an Audio Protocol v1 object")
    return value


def require_schema(value: Mapping[str, Any], *, keys: set[str], label: str) -> None:
    if set(value) != keys or value.get("protocol") != PROTOCOL_VERSION:
        raise AudioProtocolError(f"{label} has missing or extra fields")


def require_positive_request_id(value: Any, expected: int) -> None:
    if type(value) is not int or value <= 0 or value != expected:
        raise AudioProtocolError("request identity mismatch")


def require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != SHA256_LENGTH:
        raise AudioProtocolError(f"{label} must be a 64-character SHA-256")
    try:
        int(value, 16)
    except ValueError as error:
        raise AudioProtocolError(f"{label} must be lowercase hexadecimal") from error
    if value.lower() != value:
        raise AudioProtocolError(f"{label} must be lowercase hexadecimal")


def offline_child_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    environment.update({
        "PYTHONNOUSERSITE": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        # Official non-Windows ONNX Runtime builds include a 1DS uploader.
        # Full disablement must happen before the native runtime initializes.
        "ORT_DISABLE_TELEMETRY": "1",
    })
    for name in tuple(environment):
        if name.lower().endswith("_proxy"):
            environment.pop(name, None)
    return environment


async def read_exact_payload(
    reader: asyncio.StreamReader,
    payload_bytes: int,
    expected_sha256: str,
) -> bytes:
    if type(payload_bytes) is not int or payload_bytes <= 0 or payload_bytes > MAX_PCM_BYTES or payload_bytes % 2:
        raise AudioProtocolError("PCM payload length is outside the positive even 64 MiB bound")
    require_sha256(expected_sha256, "PCM checksum")
    try:
        payload = await reader.readexactly(payload_bytes)
    except asyncio.IncompleteReadError as error:
        raise AudioProtocolError("PCM payload ended before its declared length") from error
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise AudioProtocolError("PCM payload checksum mismatch")
    return payload


class FramedProcess:
    """Own one process group, private workdir, and bounded stdio framing."""

    def __init__(
        self,
        *,
        argv_builder: Callable[[Path], list[str]],
        work_root: Path,
        expected_ready: Mapping[str, str],
        ready_timeout: float,
        terminate_timeout: float,
        kill_timeout: float,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if min(ready_timeout, terminate_timeout, kill_timeout) <= 0:
            raise ValueError("child lifecycle timeouts must be positive")
        self._argv_builder = argv_builder
        self._work_root = work_root
        self._expected_ready = dict(expected_ready)
        self._ready_timeout = ready_timeout
        self._terminate_timeout = terminate_timeout
        self._kill_timeout = kill_timeout
        self._environment = dict(environment) if environment is not None else None
        self._process: asyncio.subprocess.Process | None = None
        self._workdir: Path | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr_digest = hashlib.sha256()
        self._next_id = 1
        self.state = ChildState.STOPPED

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    @property
    def workdir(self) -> Path | None:
        return self._workdir

    @property
    def returncode(self) -> int | None:
        return self._process.returncode if self._process is not None else None

    async def start(self) -> None:
        if self.state is ChildState.READY:
            return
        if self.state is not ChildState.STOPPED:
            raise AudioProtocolError("child start is legal only from STOPPED")
        self.state = ChildState.STARTING
        self._work_root.mkdir(parents=True, exist_ok=True)
        self._workdir = Path(tempfile.mkdtemp(prefix="m4a-child-", dir=self._work_root))
        self._workdir.chmod(0o700)
        try:
            argv = self._argv_builder(self._workdir)
            if not argv or not all(isinstance(item, str) and item for item in argv):
                raise AudioProtocolError("child argv is invalid")
            self._process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workdir,
                env=self._environment,
                start_new_session=True,
                limit=MAX_CONTROL_BYTES + 1,
            )
            self._stderr_task = asyncio.create_task(self._drain_stderr())
            ready = await asyncio.wait_for(self.receive(), self._ready_timeout)
            self._validate_ready(ready)
            self.state = ChildState.READY
        except TimeoutError as error:
            await self.force_terminate()
            raise AudioProtocolError("child READY timeout") from error
        except BaseException:
            await self.force_terminate()
            raise

    def _validate_ready(self, ready: Mapping[str, Any]) -> None:
        identity_keys = set(self._expected_ready)
        keys = {"protocol", "event", "pid", "pgid", *identity_keys}
        require_schema(ready, keys=keys, label="READY")
        if ready["event"] != "READY" or ready["pid"] != self.pid or ready["pgid"] != self.pid:
            raise AudioProtocolError("READY process identity mismatch")
        for name, expected in self._expected_ready.items():
            require_sha256(ready[name], name)
            if ready[name] != expected:
                raise AudioProtocolError(f"READY {name} mismatch")

    def allocate_request_id(self) -> int:
        if self.state is not ChildState.READY:
            raise AudioProtocolError("operation requires READY child")
        request_id = self._next_id
        self._next_id += 1
        self.state = ChildState.BUSY
        return request_id

    async def send(self, value: Mapping[str, Any], payload: bytes | None = None) -> None:
        process = self._process
        if process is None or process.stdin is None or process.returncode is not None:
            raise AudioProtocolError("child input is unavailable")
        process.stdin.write(encode_control(value))
        if payload is not None:
            process.stdin.write(payload)
        try:
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as error:
            raise AudioProtocolError("child input closed unexpectedly") from error

    async def receive(self) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdout is None:
            raise AudioProtocolError("child output is unavailable")
        return await read_control(process.stdout)

    async def read_payload(self, payload_bytes: int, expected_sha256: str) -> bytes:
        process = self._process
        if process is None or process.stdout is None:
            raise AudioProtocolError("child output is unavailable")
        return await read_exact_payload(process.stdout, payload_bytes, expected_sha256)

    def operation_finished(self) -> None:
        if self.state is not ChildState.BUSY:
            raise AudioProtocolError("terminal event arrived outside BUSY")
        self.state = ChildState.READY

    async def stop(self) -> None:
        if self.state is ChildState.STOPPED:
            return
        if self.state is not ChildState.READY:
            raise AudioProtocolError("clean shutdown is legal only from READY")
        try:
            await self.send({"protocol": 1, "op": "SHUTDOWN"})
            ack = await asyncio.wait_for(self.receive(), self._terminate_timeout)
            require_schema(ack, keys={"protocol", "event"}, label="SHUTDOWN_ACK")
            if ack["event"] != "SHUTDOWN_ACK":
                raise AudioProtocolError("child did not acknowledge shutdown")
            assert self._process is not None
            await asyncio.wait_for(
                self._wait_process_group_exit(self._process, self._process.pid),
                self._terminate_timeout,
            )
            if self._process.returncode != 0:
                raise AudioProtocolError("child exited nonzero after shutdown")
            self.state = ChildState.STOPPED
            await self._cleanup()
        except TimeoutError as error:
            await self.force_terminate()
            raise AudioProtocolError(
                "child process group remained alive after shutdown",
            ) from error
        except BaseException:
            await self.force_terminate()
            raise

    async def force_terminate(self) -> None:
        process = self._process
        if process is not None and (
            process.returncode is None
            or self._live_process_group_members(process.pid)
        ):
            pgid = process.pid
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(
                    self._wait_process_group_exit(process, pgid),
                    self._terminate_timeout,
                )
            except TimeoutError:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(
                        self._wait_process_group_exit(process, pgid),
                        self._kill_timeout,
                    )
                except TimeoutError as error:
                    raise AudioProtocolError("child process group exit could not be proven") from error
        self.state = ChildState.DESTROYED
        await self._cleanup()

    @staticmethod
    def _live_process_group_members(pgid: int) -> set[int]:
        live: set[int] = set()
        proc = Path("/proc")
        if not proc.is_dir():
            # M4a production targets Linux.  A platform without /proc cannot
            # provide the required descendant-exit proof.
            return {pgid}
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (
                    (entry / "stat").read_text(encoding="ascii")
                    .rsplit(")", 1)[1].split()
                )
                state, process_group = fields[0], int(fields[2])
                if process_group == pgid and state != "Z":
                    live.add(int(entry.name))
            except (OSError, ValueError, IndexError):
                continue
        return live

    async def _wait_process_group_exit(
        self,
        process: asyncio.subprocess.Process,
        pgid: int,
    ) -> None:
        while process.returncode is None or self._live_process_group_members(pgid):
            await asyncio.sleep(0.01)
        await process.wait()

    async def _drain_stderr(self) -> None:
        assert self._process is not None and self._process.stderr is not None
        while block := await self._process.stderr.read(4096):
            self._stderr_digest.update(block)

    async def _cleanup(self) -> None:
        process = self._process
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
                try:
                    await process.stdin.wait_closed()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            if self._stderr_task is not None:
                try:
                    await asyncio.wait_for(self._stderr_task, self._kill_timeout)
                except (TimeoutError, asyncio.CancelledError):
                    self._stderr_task.cancel()
        if self._workdir is not None and self._workdir.exists():
            shutil.rmtree(self._workdir)
        self._workdir = None


__all__ = [
    "AudioProtocolError", "ChildState", "FramedProcess", "MAX_CONTROL_BYTES",
    "MAX_PCM_BYTES", "encode_control", "read_control", "read_exact_payload",
    "offline_child_environment", "require_positive_request_id", "require_schema",
    "require_sha256",
]
