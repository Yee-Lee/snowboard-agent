"""Parent-side bounded PCM owner for the isolated Matcha worker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from collections.abc import AsyncIterator, Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterError, AdapterRejected, AdapterUnavailable
from sbd.adaptor.framed_child import (
    AudioProtocolError,
    ChildState,
    FramedProcess,
    MAX_PCM_BYTES,
    offline_child_environment,
    require_positive_request_id,
    require_schema,
    require_sha256,
)
from sbd.core.config.models import AppConfig, TTSConfig
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.fault_injection import DeterministicFaultInjector
from sbd.core.lifecycle import ForceAbortReport


TTS_KEY = "backend.action.speak.tts"
TTS_ERROR_CODES = {"INVALID_TEXT", "GENERATION_REJECTED", "INVALID_PCM"}


class _TTSRequestFault(AdapterError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class TTSProtocolSystemFault(ComponentSystemFault, AudioProtocolError):
    """Typed M4-ERR protocol fault retaining the M4A protocol boundary."""


class TTSEOFSystemFault(ComponentSystemFault, EOFError):
    """Typed M4-ERR EOF fault retaining the M4A EOF boundary."""


class _Child(Protocol):
    state: ChildState
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def force_terminate(self) -> None: ...
    def allocate_request_id(self) -> int: ...
    async def send(self, value: Mapping[str, Any], payload: bytes | None = None) -> None: ...
    async def receive(self) -> dict[str, Any]: ...
    async def read_payload(self, payload_bytes: int, expected_sha256: str) -> bytes: ...
    def operation_finished(self) -> None: ...


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _profile_sha256(profile: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(profile), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class MatchaTTSAdapter:
    def __init__(
        self,
        config: TTSConfig,
        *,
        lock: AudioArtifactLock,
        child_factory: Callable[[], _Child] | None = None,
        fault_injector: DeterministicFaultInjector | None = None,
    ) -> None:
        self._config = config
        self._lock = lock
        self._child_factory = child_factory or self._default_child
        self._fault_injector = fault_injector
        self._child: _Child = self._child_factory()
        self._operation_lock = asyncio.Lock()
        self._active_request_id: int | None = None
        self._cancel_requested = asyncio.Event()
        self._request_ready = asyncio.Event()
        self._request_ready.set()
        self._cancel_sent_for: int | None = None
        self._destroyed_for_fault = False

    @property
    def state(self) -> ChildState:
        return self._child.state

    def _default_child(self) -> FramedProcess:
        config = self._config
        assert config.runtime_python and config.model_path and config.vocoder_path and config.artifact_lock_path
        runtime_lock = config.artifact_lock_path.parent / "tts-rpi-cp313.json"
        expected = {
            "runtime_lock_sha256": _file_sha256(runtime_lock),
            "acoustic_model_sha256": self._lock.require("matcha-model").sha256,
            "vocoder_sha256": self._lock.require("vocos-model").sha256,
            "profile_sha256": _profile_sha256(self._lock.profiles["tts"]),
        }
        worker = Path(__file__).with_name("worker.py")

        def argv(workdir: Path) -> list[str]:
            return [
                str(config.runtime_python), str(worker),
                "--model-dir", str(config.model_path), "--vocoder", str(config.vocoder_path),
                "--runtime-lock", str(runtime_lock), "--profile-sha256", expected["profile_sha256"],
                "--work-dir", str(workdir),
            ]

        return FramedProcess(
            argv_builder=argv,
            work_root=Path(tempfile.gettempdir()) / "sbd-m4a-tts",
            expected_ready=expected,
            ready_timeout=config.child_ready_timeout_seconds,
            terminate_timeout=config.child_terminate_timeout_seconds,
            kill_timeout=config.child_kill_wait_timeout_seconds,
            environment=offline_child_environment(),
        )

    async def start(self) -> None:
        await self._child.start()

    async def stop(self) -> None:
        if self._child.state in {ChildState.STOPPED, ChildState.DESTROYED}:
            return
        if self._child.state is ChildState.BUSY:
            await self.force_abort()
            return
        await self._child.stop()

    def synthesize(self, text: str) -> AsyncIterator[bytes]:
        async def generate() -> AsyncIterator[bytes]:
            if type(text) is not str or not text.strip() or "\x00" in text:
                raise AdapterRejected("TTS text is invalid")
            if self._operation_lock.locked():
                raise AdapterUnavailable("TTS backend is busy")
            async with self._operation_lock:
                if self._child.state is not ChildState.READY:
                    raise AdapterUnavailable("TTS backend is not ready")
                request_id = self._child.allocate_request_id()
                self._active_request_id = request_id
                self._cancel_requested.clear()
                self._request_ready.clear()
                self._cancel_sent_for = None
                payload = b""
                try:
                    await self._child.send({"protocol": 1, "op": "GENERATE", "request_id": request_id, "text": text, "voice_id": "matcha-zh-en-default-sid-0"})
                    injector = self._fault_injector
                    if injector is not None and injector.fire(
                        "tts.child.exit", self.backend_identity()
                    ):
                        await self._child.force_terminate()
                        raise EOFError("M4_ERR_INJECTED_TTS_CHILD_EXIT")
                    while True:
                        header = await self._receive_with_cancel(request_id)
                        name = header.get("event")
                        if name == "CANCEL_DEFERRED":
                            self._validate_simple(header, request_id, name)
                            continue
                        if name == "CANCELLED":
                            self._validate_simple(header, request_id, name)
                            self._finish()
                            raise AdapterRejected("TTS request was cancelled")
                        if name == "ERROR":
                            self._raise_request_error(header, request_id)
                        if name == "BUSY":
                            self._validate_simple(header, request_id, "BUSY")
                            raise AdapterUnavailable("TTS child rejected concurrent work")
                        if name != "PCM":
                            raise AudioProtocolError("unexpected TTS terminal event")
                        break
                    require_schema(
                        header,
                        keys={"protocol", "event", "request_id", "sample_rate_hz", "channels", "sample_format", "sample_count", "payload_bytes", "pcm_sha256"},
                        label="PCM",
                    )
                    require_positive_request_id(header["request_id"], request_id)
                    if (header["sample_rate_hz"], header["channels"], header["sample_format"]) != (16000, 1, "S16_LE"):
                        raise AudioProtocolError("TTS PCM format mismatch")
                    sample_count = header["sample_count"]
                    payload_bytes = header["payload_bytes"]
                    if (
                        type(sample_count) is not int
                        or sample_count <= 0
                        or type(payload_bytes) is not int
                        or payload_bytes <= 0
                        or payload_bytes > MAX_PCM_BYTES
                        or payload_bytes % 2
                        or payload_bytes != sample_count * 2
                    ):
                        raise AudioProtocolError("TTS PCM sample/byte count mismatch")
                    require_sha256(header["pcm_sha256"], "TTS PCM checksum")
                    payload = await self._child.read_payload(payload_bytes, header["pcm_sha256"])
                    self._finish()
                    for offset in range(0, len(payload), 640):
                        chunk = payload[offset:offset + 640]
                        if len(chunk) % 2:
                            raise AudioProtocolError("TTS emitted a partial sample")
                        yield chunk
                except asyncio.CancelledError:
                    raise
                except _TTSRequestFault as exc:
                    await self._protocol_failure()
                    code = (
                        "TTS_GENERATION_FAILED"
                        if exc.code == "GENERATION_REJECTED"
                        else "TTS_PROTOCOL_FAILED"
                    )
                    fault = ComponentSystemFault.create(
                        where="action.speak.tts",
                        code=code,
                        backend=BackendDisposition.REBUILD_REQUIRED,
                        recovery_keys=(TTS_KEY,),
                    )
                    raise fault from exc
                except AdapterRejected:
                    raise
                except (AudioProtocolError, EOFError) as exc:
                    await self._protocol_failure()
                    fault_type = (
                        TTSEOFSystemFault if isinstance(exc, EOFError)
                        else TTSProtocolSystemFault
                    )
                    fault = fault_type.create(
                        where="action.speak.tts",
                        code="TTS_PROTOCOL_FAILED",
                        backend=BackendDisposition.REBUILD_REQUIRED,
                        recovery_keys=(TTS_KEY,),
                    )
                    if isinstance(exc, AudioProtocolError):
                        # M4A retained this fixed, payload-free protocol token
                        # as the local exception boundary.  Public Event/log
                        # projection still uses the M4-ERR code and summary.
                        fault.args = (str(exc),)
                    raise fault from exc
                except AdapterError as exc:
                    if self._active_request_id is not None:
                        await self._protocol_failure()
                    fault = ComponentSystemFault.create(
                        where="action.speak.tts",
                        code="TTS_GENERATION_FAILED",
                        backend=BackendDisposition.REBUILD_REQUIRED,
                        recovery_keys=(TTS_KEY,),
                    )
                    raise fault from exc
                finally:
                    payload = b""

        return generate()

    async def _send_cancel_once(self, request_id: int) -> None:
        if self._cancel_sent_for == request_id:
            return
        await self._child.send({"protocol": 1, "op": "CANCEL", "request_id": request_id})
        self._cancel_sent_for = request_id

    async def _receive_with_cancel(self, request_id: int) -> dict[str, Any]:
        receive = asyncio.create_task(self._child.receive())
        cancellation = asyncio.create_task(self._cancel_requested.wait())
        try:
            done, _ = await asyncio.wait(
                {receive, cancellation}, return_when=asyncio.FIRST_COMPLETED,
            )
            if receive in done:
                return receive.result()
            await self._send_cancel_once(request_id)
            return await receive
        finally:
            for task in (receive, cancellation):
                if not task.done():
                    task.cancel()
            await asyncio.gather(receive, cancellation, return_exceptions=True)

    def _validate_simple(self, event: Mapping[str, Any], request_id: int, name: str) -> None:
        require_schema(event, keys={"protocol", "event", "request_id"}, label=name)
        require_positive_request_id(event["request_id"], request_id)
        if event["event"] != name:
            raise AudioProtocolError(f"expected {name}")

    def _raise_request_error(self, event: Mapping[str, Any], request_id: int) -> None:
        require_schema(event, keys={"protocol", "event", "request_id", "code"}, label="ERROR")
        require_positive_request_id(event["request_id"], request_id)
        if event["code"] not in TTS_ERROR_CODES:
            raise AudioProtocolError("unknown TTS request error code")
        code = event["code"]
        self._finish()
        raise _TTSRequestFault(code)

    def _finish(self) -> None:
        self._child.operation_finished()
        self._active_request_id = None
        self._request_ready.set()

    async def abort(self) -> None:
        request_id = self._active_request_id
        if request_id is None or self._child.state is not ChildState.BUSY:
            return
        self._cancel_requested.set()
        await self._request_ready.wait()

    async def force_abort(self) -> ForceAbortReport:
        if self._child.state in {ChildState.STOPPED, ChildState.DESTROYED}:
            if self._destroyed_for_fault:
                self._destroyed_for_fault = False
                return ForceAbortReport((TTS_KEY,))
            return ForceAbortReport()
        await self._child.force_terminate()
        self._active_request_id = None
        self._request_ready.set()
        return ForceAbortReport((TTS_KEY,))

    async def _protocol_failure(self) -> None:
        await self._child.force_terminate()
        self._destroyed_for_fault = True
        self._active_request_id = None
        self._request_ready.set()

    async def rebuild(self, bus: Any, config: AppConfig) -> None:
        if self._child.state is not ChildState.DESTROYED:
            raise AdapterError("TTS rebuild is legal only from DESTROYED")
        if config.action.tts != self._config:
            raise AdapterError("TTS rebuild baseline differs from the destroyed owner")
        replacement = self._child_factory()
        try:
            await replacement.start()
        except BaseException:
            await replacement.force_terminate()
            raise
        self._child = replacement
        self._destroyed_for_fault = False

    def backend_identity(self) -> dict[str, str | int | bool]:
        pid = getattr(self._child, "pid", None)
        return {
            "backend": "matcha",
            "driver": self._config.driver,
            "artifact_lock_sha256": self._lock.digest,
            "pid": int(pid) if type(pid) is int else 0,
            "live": (
                type(pid) is int
                and pid > 0
                and self._child.state in {ChildState.READY, ChildState.BUSY}
            ),
        }


__all__ = ["MatchaTTSAdapter", "TTS_KEY"]
