"""Parent-side streaming ASR owner for the isolated M4a supervisor."""

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
    offline_child_environment,
    require_positive_request_id,
    require_schema,
    require_sha256,
)
from sbd.core.config.models import ASRConfig, AppConfig
from sbd.core.lifecycle import ForceAbortReport
from sbd.perception.listen.asr import ASRResult


ASR_KEY = "backend.perception.listen.asr"
ASR_ERROR_CODES = {"INVALID_FRAME", "NO_SPEECH", "MULTIPLE_UTTERANCES", "INFERENCE_REJECTED"}


class _Child(Protocol):
    state: ChildState
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def force_terminate(self) -> None: ...
    def allocate_request_id(self) -> int: ...
    async def send(self, value: Mapping[str, Any], payload: bytes | None = None) -> None: ...
    async def receive(self) -> dict[str, Any]: ...
    def operation_finished(self) -> None: ...


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _profile_sha256(profile: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(profile), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class WhisperCppASRAdapter:
    def __init__(
        self,
        config: ASRConfig,
        *,
        lock: AudioArtifactLock,
        child_factory: Callable[[], _Child] | None = None,
    ) -> None:
        self._config = config
        self._lock = lock
        self._child_factory = child_factory or self._default_child
        self._child: _Child = self._child_factory()
        self._operation_lock = asyncio.Lock()
        self._active_request_id: int | None = None
        self._cancel_requested = asyncio.Event()
        self._request_ready = asyncio.Event()
        self._request_ready.set()
        self._cancel_sent_for: int | None = None

    @property
    def state(self) -> ChildState:
        return self._child.state

    def _default_child(self) -> FramedProcess:
        config = self._config
        assert config.runtime_python and config.model_path and config.worker_path
        assert config.vad_model_path and config.artifact_lock_path
        runtime_lock = config.artifact_lock_path.parent / "vad-rpi-cp313.json"
        expected = {
            "runtime_lock_sha256": _file_sha256(runtime_lock),
            "vad_model_sha256": self._lock.require("silero-model").sha256,
            "asr_binary_sha256": self._lock.worker_binary_sha256(config.worker_path),
            "asr_model_sha256": self._lock.require("whisper-model").sha256,
            "profile_sha256": _profile_sha256(self._lock.profiles["vad"] | self._lock.profiles["asr"]),
        }
        supervisor = Path(__file__).with_name("supervisor.py")

        def argv(workdir: Path) -> list[str]:
            return [
                str(config.runtime_python), str(supervisor),
                "--vad-model", str(config.vad_model_path),
                "--asr-binary", str(config.worker_path),
                "--asr-model", str(config.model_path),
                "--runtime-lock", str(runtime_lock),
                "--profile-sha256", expected["profile_sha256"],
                "--work-dir", str(workdir),
            ]

        return FramedProcess(
            argv_builder=argv,
            work_root=Path(tempfile.gettempdir()) / "sbd-m4a-asr",
            expected_ready=expected,
            ready_timeout=config.child_ready_timeout_seconds,
            terminate_timeout=config.child_terminate_timeout_seconds,
            kill_timeout=config.child_kill_wait_timeout_seconds,
            environment=offline_child_environment(),
        )

    async def start(self) -> None:
        await self._child.start()

    async def stop(self) -> None:
        if self._child.state is ChildState.BUSY:
            await self.force_abort()
            return
        await self._child.stop()

    async def transcribe(self, frames: AsyncIterator[bytes]) -> ASRResult:
        if self._operation_lock.locked():
            raise AdapterUnavailable("ASR backend is busy")
        async with self._operation_lock:
            if self._child.state is not ChildState.READY:
                raise AdapterUnavailable("ASR backend is not ready")
            try:
                first = await anext(frames)
            except StopAsyncIteration:
                raise AdapterRejected("ASR input contains no frames") from None
            if len(first) != 640:
                raise AdapterError("ASR frame must be exactly 640 bytes")
            request_id = self._child.allocate_request_id()
            self._active_request_id = request_id
            self._cancel_requested.clear()
            self._request_ready.clear()
            self._cancel_sent_for = None
            captured_pcm = bytearray()
            try:
                await self._child.send({"protocol": 1, "op": "BEGIN", "request_id": request_id, "format": "16000_mono_s16le", "frame_bytes": 640})
                sequence = 0
                frame: bytes | None = first
                while frame is not None:
                    if len(frame) != 640:
                        raise AdapterError("ASR frame must be exactly 640 bytes")
                    await self._child.send({"protocol": 1, "op": "FRAME", "request_id": request_id, "sequence": sequence, "payload_bytes": 640}, frame)
                    captured_pcm.extend(frame)
                    event = await self._receive_with_cancel(request_id)
                    name = event.get("event")
                    if name == "FRAME_ACCEPTED":
                        require_schema(event, keys={"protocol", "event", "request_id", "sequence"}, label="FRAME_ACCEPTED")
                        require_positive_request_id(event["request_id"], request_id)
                        if event["sequence"] != sequence:
                            raise AudioProtocolError("FRAME_ACCEPTED sequence mismatch")
                        sequence += 1
                        frame, asynchronous_event = await self._next_frame_or_event(
                            frames, request_id,
                        )
                        if asynchronous_event is not None:
                            name = asynchronous_event.get("event")
                            if name == "CANCEL_DEFERRED":
                                self._validate_simple(asynchronous_event, request_id, name)
                                frame = None
                            elif name == "CANCELLED":
                                self._validate_simple(asynchronous_event, request_id, name)
                                self._finish()
                                raise AdapterRejected("ASR request was cancelled")
                            elif name == "ERROR":
                                self._raise_request_error(asynchronous_event, request_id)
                            else:
                                raise AudioProtocolError("unexpected ASR event while awaiting input")
                    elif name == "ENDPOINT":
                        self._validate_endpoint(event, request_id, captured_pcm)
                        frame = None
                    elif name == "CANCEL_DEFERRED":
                        self._validate_simple(event, request_id, name)
                        frame = None
                    elif name == "CANCELLED":
                        self._validate_simple(event, request_id, name)
                        self._finish()
                        raise AdapterRejected("ASR request was cancelled")
                    elif name == "ERROR":
                        self._raise_request_error(event, request_id)
                    elif name == "BUSY":
                        self._validate_simple(event, request_id, "BUSY")
                        raise AdapterUnavailable("ASR child rejected concurrent work")
                    else:
                        raise AudioProtocolError("unexpected ASR capture event")
                while True:
                    terminal = await self._receive_with_cancel(request_id)
                    name = terminal.get("event")
                    if name == "CANCEL_DEFERRED":
                        self._validate_simple(terminal, request_id, name)
                        continue
                    if name == "RESULT":
                        result = self._result(terminal, request_id)
                        self._finish()
                        return result
                    if name == "ERROR":
                        self._raise_request_error(terminal, request_id)
                    if name == "CANCELLED":
                        self._validate_simple(terminal, request_id, name)
                        self._finish()
                        raise AdapterRejected("ASR request was cancelled")
                    raise AudioProtocolError("unexpected ASR terminal event")
            except asyncio.CancelledError:
                raise
            except (AudioProtocolError, EOFError):
                await self._protocol_failure()
                raise
            except AdapterError:
                if self._active_request_id is not None:
                    await self._protocol_failure()
                raise
            finally:
                captured_pcm.clear()

    def _validate_endpoint(
        self,
        event: Mapping[str, Any],
        request_id: int,
        captured_pcm: bytearray,
    ) -> None:
        require_schema(event, keys={"protocol", "event", "request_id", "captured_frames", "bounded_samples", "bounded_pcm_sha256"}, label="ENDPOINT")
        require_positive_request_id(event["request_id"], request_id)
        if (
            type(event["captured_frames"]) is not int
            or event["captured_frames"] <= 0
            or event["captured_frames"] * 640 != len(captured_pcm)
        ):
            raise AudioProtocolError("ENDPOINT captured_frames is invalid")
        if (
            type(event["bounded_samples"]) is not int
            or event["bounded_samples"] <= 0
            or event["bounded_samples"] * 2 > len(captured_pcm)
        ):
            raise AudioProtocolError("ENDPOINT bounded_samples is invalid")
        require_sha256(event["bounded_pcm_sha256"], "bounded PCM checksum")
        bounded = bytes(captured_pcm[-event["bounded_samples"] * 2:])
        if hashlib.sha256(bounded).hexdigest() != event["bounded_pcm_sha256"]:
            raise AudioProtocolError("ENDPOINT bounded PCM checksum mismatch")

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

    async def _next_frame_or_event(
        self,
        frames: AsyncIterator[bytes],
        request_id: int,
    ) -> tuple[bytes | None, dict[str, Any] | None]:
        frame = asyncio.create_task(anext(frames))
        cancellation = asyncio.create_task(self._cancel_requested.wait())
        try:
            done, _ = await asyncio.wait(
                {frame, cancellation}, return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation in done:
                await self._send_cancel_once(request_id)
                return None, await self._child.receive()
            try:
                return frame.result(), None
            except StopAsyncIteration:
                return None, None
        finally:
            for task in (frame, cancellation):
                if not task.done():
                    task.cancel()
            await asyncio.gather(frame, cancellation, return_exceptions=True)

    def _result(self, event: Mapping[str, Any], request_id: int) -> ASRResult:
        require_schema(event, keys={"protocol", "event", "request_id", "text", "language", "latency_ms"}, label="RESULT")
        require_positive_request_id(event["request_id"], request_id)
        if not isinstance(event["text"], str) or event["language"] != "zh-TW":
            raise AudioProtocolError("ASR RESULT text/language is invalid")
        if type(event["latency_ms"]) not in (int, float) or event["latency_ms"] < 0:
            raise AudioProtocolError("ASR RESULT latency is invalid")
        return ASRResult(event["text"], language="zh-TW")

    def _validate_simple(self, event: Mapping[str, Any], request_id: int, name: str) -> None:
        require_schema(event, keys={"protocol", "event", "request_id"}, label=name)
        require_positive_request_id(event["request_id"], request_id)
        if event["event"] != name:
            raise AudioProtocolError(f"expected {name}")

    def _raise_request_error(self, event: Mapping[str, Any], request_id: int) -> None:
        require_schema(event, keys={"protocol", "event", "request_id", "code"}, label="ERROR")
        require_positive_request_id(event["request_id"], request_id)
        if event["code"] not in ASR_ERROR_CODES:
            raise AudioProtocolError("unknown ASR request error code")
        self._finish()
        raise AdapterRejected(f"ASR request rejected: {event['code']}")

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
            return ForceAbortReport()
        await self._child.force_terminate()
        self._active_request_id = None
        self._request_ready.set()
        return ForceAbortReport((ASR_KEY,))

    async def _protocol_failure(self) -> None:
        await self._child.force_terminate()
        self._active_request_id = None
        self._request_ready.set()

    async def rebuild(self, bus: Any, config: AppConfig) -> None:
        if self._child.state is not ChildState.DESTROYED:
            raise AdapterError("ASR rebuild is legal only from DESTROYED")
        if config.perception.listen.adapter != self._config:
            raise AdapterError("ASR rebuild baseline differs from the destroyed owner")
        replacement = self._child_factory()
        try:
            await replacement.start()
        except BaseException:
            await replacement.force_terminate()
            raise
        self._child = replacement


__all__ = ["ASR_KEY", "WhisperCppASRAdapter"]
