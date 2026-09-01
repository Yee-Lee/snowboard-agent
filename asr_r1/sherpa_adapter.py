"""Thin AR1 protocol adapter for a lazily loaded sherpa-onnx backend."""

from __future__ import annotations

import sys
from array import array
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Protocol, Sequence

from .protocol import (
    ErrorCode,
    EventKind,
    PCMChunk,
    ProtocolError,
    SessionState,
    TranscriptAlternative,
    TranscriptEvent,
)


class OnlineBackend(Protocol):
    """Small backend surface kept separate from the AR1 wire contract."""

    model_id: str

    def load_model(self) -> None: ...

    def create_stream(self) -> object: ...

    def accept_waveform(self, stream: object, samples: Sequence[float]) -> None: ...

    def is_ready(self, stream: object) -> bool: ...

    def decode_stream(self, stream: object) -> None: ...

    def get_text(self, stream: object) -> str: ...

    def input_finished(self, stream: object) -> None: ...

    def close_stream(self, stream: object) -> None: ...

    def close(self) -> None: ...


@dataclass
class _AdapterSession:
    stream: object | None
    state: SessionState = SessionState.OPEN
    next_chunk_sequence: int = 0
    last_timestamp_ms: int = -1
    event_sequence: int = 0
    last_partial: str = ""
    stream_closed: bool = False


class SherpaStreamingRuntime:
    """Map one resident backend model and isolated streams to the AR1 protocol."""

    def __init__(self, backend: OnlineBackend) -> None:
        self._backend = backend
        self._model_loaded = False
        self._shutdown = False
        self._sessions: dict[str, _AdapterSession] = {}
        self._next_session = 1

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    def state(self, session_id: str) -> SessionState:
        return self._session(session_id).state

    def load_model(self) -> str:
        self._require_running()
        if not self._model_loaded:
            self._backend_call(self._backend.load_model)
            self._model_loaded = True
        return self._backend.model_id

    def create_session(self) -> str:
        self._require_running()
        if not self._model_loaded:
            raise ProtocolError(ErrorCode.INVALID_STATE, "load the model first")
        session_id = f"sherpa-session-{self._next_session}"
        self._next_session += 1
        stream = self._backend_call(self._backend.create_stream)
        self._sessions[session_id] = _AdapterSession(stream=stream)
        return session_id

    def accept_chunk(
        self, chunk: PCMChunk, decode_timeout_ms: int = 1_000
    ) -> TranscriptEvent | None:
        self._require_running()
        session = self._session(chunk.session_id)
        if session.state not in {SessionState.OPEN, SessionState.STREAMING}:
            raise ProtocolError(ErrorCode.INVALID_STATE, "session no longer accepts PCM")
        if chunk.sequence != session.next_chunk_sequence:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "chunk sequence is not contiguous")
        if chunk.timestamp_ms <= session.last_timestamp_ms:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "chunk timestamp is not increasing")

        samples = array("h")
        samples.frombytes(chunk.samples_s16le)
        if sys.byteorder != "little":
            samples.byteswap()
        normalized = tuple(sample / 32768.0 for sample in samples)
        try:
            self._backend.accept_waveform(session.stream, normalized)
            self._drain_ready(session, decode_timeout_ms)
            text = self._backend.get_text(session.stream).strip()
        except ProtocolError:
            session.state = SessionState.ERROR
            raise
        except Exception as exc:
            session.state = SessionState.ERROR
            raise self._runtime_failure(exc) from exc

        session.state = SessionState.STREAMING
        session.next_chunk_sequence += 1
        session.last_timestamp_ms = chunk.timestamp_ms
        if not text or text == session.last_partial:
            return None
        event = TranscriptEvent(
            kind=EventKind.PARTIAL,
            session_id=chunk.session_id,
            sequence=session.event_sequence,
            emitted_at_ms=chunk.timestamp_ms,
            text=text,
        )
        session.event_sequence += 1
        session.last_partial = text
        return event

    def finish_input(
        self, session_id: str, emitted_at_ms: int, decode_timeout_ms: int = 5_000
    ) -> TranscriptEvent:
        self._require_running()
        session = self._session(session_id)
        if session.state is not SessionState.STREAMING:
            raise ProtocolError(ErrorCode.INVALID_STATE, "input-finished requires streamed PCM")
        if emitted_at_ms < session.last_timestamp_ms:
            raise ProtocolError(ErrorCode.OUT_OF_ORDER, "final event precedes the last PCM chunk")
        try:
            self._backend.input_finished(session.stream)
            self._drain_ready(session, decode_timeout_ms)
            text = self._backend.get_text(session.stream).strip()
        except ProtocolError:
            session.state = SessionState.ERROR
            raise
        except Exception as exc:
            session.state = SessionState.ERROR
            raise self._runtime_failure(exc) from exc
        if not text:
            session.state = SessionState.ERROR
            raise ProtocolError(ErrorCode.INVALID_STATE, "backend returned an empty final")

        self._close_session_stream(session)
        session.state = SessionState.FINAL
        event = TranscriptEvent(
            kind=EventKind.FINAL,
            session_id=session_id,
            sequence=session.event_sequence,
            emitted_at_ms=emitted_at_ms,
            text=text,
            alternatives=(TranscriptAlternative(text=text, rank=1),),
        )
        session.event_sequence += 1
        return event

    def reset_session(self, session_id: str) -> None:
        self._require_running()
        current = self._session(session_id)
        self._close_session_stream(current)
        stream = self._backend_call(self._backend.create_stream)
        self._sessions[session_id] = _AdapterSession(stream=stream)

    def cancel_session(self, session_id: str, emitted_at_ms: int) -> TranscriptEvent:
        self._require_running()
        session = self._session(session_id)
        if session.state in {SessionState.FINAL, SessionState.CANCELLED}:
            raise ProtocolError(ErrorCode.INVALID_STATE, "terminal session cannot be cancelled")
        self._close_session_stream(session)
        session.state = SessionState.CANCELLED
        event = TranscriptEvent(
            kind=EventKind.ERROR,
            session_id=session_id,
            sequence=session.event_sequence,
            emitted_at_ms=emitted_at_ms,
            error_code=ErrorCode.CANCELLED,
            error_message="session cancelled",
        )
        session.event_sequence += 1
        return event

    def shutdown(self, timeout_ms: int) -> int:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        started = monotonic()
        for session in self._sessions.values():
            self._close_session_stream(session)
        self._sessions.clear()
        try:
            self._backend.close()
        except Exception as exc:
            raise self._runtime_failure(exc) from exc
        elapsed_ms = int((monotonic() - started) * 1000)
        self._model_loaded = False
        self._shutdown = True
        if elapsed_ms > timeout_ms:
            raise ProtocolError(ErrorCode.SHUTDOWN, "shutdown exceeded its bound")
        return elapsed_ms

    def _drain_ready(self, session: _AdapterSession, timeout_ms: int) -> None:
        if timeout_ms <= 0:
            raise ValueError("decode_timeout_ms must be positive")
        deadline = monotonic() + timeout_ms / 1_000
        while self._backend.is_ready(session.stream):
            if monotonic() >= deadline:
                raise ProtocolError(ErrorCode.INVALID_STATE, "decode timeout")
            self._backend.decode_stream(session.stream)

    def _backend_call(self, operation):
        try:
            return operation()
        except Exception as exc:
            raise self._runtime_failure(exc) from exc

    def _close_session_stream(self, session: _AdapterSession) -> None:
        if session.stream_closed:
            return
        stream = session.stream
        if stream is None:
            raise ProtocolError(ErrorCode.INVALID_STATE, "session stream is missing")
        self._backend_call(lambda: self._backend.close_stream(stream))
        session.stream = None
        session.stream_closed = True

    @staticmethod
    def _runtime_failure(exc: Exception) -> ProtocolError:
        return ProtocolError(
            ErrorCode.INVALID_STATE,
            f"backend failure: {type(exc).__name__}",
        )

    def _require_running(self) -> None:
        if self._shutdown:
            raise ProtocolError(ErrorCode.SHUTDOWN, "runtime is shut down")

    def _session(self, session_id: str) -> _AdapterSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise ProtocolError(ErrorCode.SESSION_NOT_FOUND, session_id) from exc


class SherpaOnnxTransducerBackend:
    """Lazy official sherpa-onnx transducer backend."""

    encoder_name = "encoder.int8.onnx"
    decoder_name = "decoder.onnx"
    joiner_name = "joiner.int8.onnx"
    tokens_name = "tokens.txt"

    def __init__(
        self, model_id: str, model_dir: Path, num_threads: int = 2
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        if num_threads <= 0:
            raise ValueError("num_threads must be positive")
        self.model_id = model_id
        self._model_dir = model_dir.resolve()
        self._num_threads = num_threads
        self._recognizer = None

    def load_model(self) -> None:
        self._verify_files(
            self.encoder_name,
            self.decoder_name,
            self.joiner_name,
            self.tokens_name,
        )
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError("sherpa_onnx 1.13.5 is not installed") from exc
        self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(self._model_dir / self.tokens_name),
            encoder=str(self._model_dir / self.encoder_name),
            decoder=str(self._model_dir / self.decoder_name),
            joiner=str(self._model_dir / self.joiner_name),
            num_threads=self._num_threads,
            sample_rate=16_000,
            feature_dim=80,
            decoding_method="greedy_search",
            provider="cpu",
        )

    def create_stream(self) -> object:
        return self._require_recognizer().create_stream()

    def accept_waveform(self, stream: object, samples: Sequence[float]) -> None:
        stream.accept_waveform(16_000, samples)

    def is_ready(self, stream: object) -> bool:
        return self._require_recognizer().is_ready(stream)

    def decode_stream(self, stream: object) -> None:
        self._require_recognizer().decode_stream(stream)

    def get_text(self, stream: object) -> str:
        result = self._require_recognizer().get_result(stream)
        return result.text if hasattr(result, "text") else str(result)

    def input_finished(self, stream: object) -> None:
        stream.input_finished()

    def close_stream(self, stream: object) -> None:
        del stream

    def close(self) -> None:
        self._recognizer = None

    def _require_recognizer(self):
        if self._recognizer is None:
            raise RuntimeError("model is not loaded")
        return self._recognizer

    def _verify_files(self, *names: str) -> None:
        if not self._model_dir.is_dir():
            raise FileNotFoundError(self._model_dir)
        for name in names:
            path = self._model_dir / name
            if not path.is_file():
                raise FileNotFoundError(path)


class SherpaOnnxWenetCtcBackend(SherpaOnnxTransducerBackend):
    """Lazy official sherpa-onnx online WeNet CTC backend."""

    model_name = "model-streaming.int8.onnx"

    def load_model(self) -> None:
        self._verify_files(self.model_name, self.tokens_name)
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError("sherpa_onnx 1.13.5 is not installed") from exc
        self._recognizer = sherpa_onnx.OnlineRecognizer.from_wenet_ctc(
            tokens=str(self._model_dir / self.tokens_name),
            model=str(self._model_dir / self.model_name),
            chunk_size=16,
            num_left_chunks=4,
            num_threads=self._num_threads,
            sample_rate=16_000,
            feature_dim=80,
            decoding_method="greedy_search",
            provider="cpu",
        )


class SherpaOnnxBackend(SherpaOnnxTransducerBackend):
    """Compatibility name for the frozen large Zipformer row."""

    def __init__(self, model_dir: Path, num_threads: int = 2) -> None:
        super().__init__(
            model_id="sherpa-onnx-streaming-zipformer-zh-int8-2025-06-30",
            model_dir=model_dir,
            num_threads=num_threads,
        )
