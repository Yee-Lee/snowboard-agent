"""Thin stable-C-ABI backend for the frozen NeMo-Speech.cpp runtime."""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


NEMO_SPEECH_ASR_OK = 0


class _BackendConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("gpu", ctypes.c_int32),
    ]


class _ModelConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("path", ctypes.c_char_p),
        ("name", ctypes.c_char_p),
    ]


class _RecognizerConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("backend", ctypes.POINTER(_BackendConfig)),
        ("model", ctypes.POINTER(_ModelConfig)),
        ("streaming", ctypes.c_void_p),
        ("decoder", ctypes.c_void_p),
        ("vad", ctypes.c_void_p),
        ("endpointing", ctypes.c_void_p),
        ("postproc", ctypes.c_void_p),
        ("diar", ctypes.c_void_p),
        ("batching", ctypes.c_void_p),
    ]


class _RecognitionOptions(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("request_id", ctypes.c_char_p),
        ("language_code", ctypes.c_char_p),
        ("interim_results", ctypes.c_bool),
        ("enable_word_time_offsets", ctypes.c_bool),
        ("enable_automatic_punctuation", ctypes.c_bool),
        ("verbatim_transcripts", ctypes.c_bool),
        ("profanity_filter", ctypes.c_bool),
        ("stop_history_eou_ms", ctypes.c_int32),
        ("speech_contexts", ctypes.c_void_p),
        ("speech_context_count", ctypes.c_size_t),
        ("max_alternatives", ctypes.c_int32),
        ("enable_speaker_diarization", ctypes.c_bool),
        ("max_speaker_count", ctypes.c_int32),
    ]


@dataclass
class _NemoStream:
    handle: ctypes.c_void_p
    text: str = ""
    pending_result: ctypes.c_void_p | None = None
    final_seen: bool = False
    finish_requested: bool = False
    alternative_count: int = 0
    closed: bool = False


class NemoSpeechCBackend:
    """Adapt NeMo-Speech.cpp v1 streaming handles to the AR1 backend surface."""

    def __init__(
        self,
        model_id: str,
        model_path: Path,
        library_path: Path,
        language_code: str = "zh-CN",
        expected_runtime_version: str = "nemo-speech-asr 0.1.0",
        library_loader: Callable[[str], object] = ctypes.CDLL,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not language_code.strip():
            raise ValueError("language_code must be non-empty")
        if not expected_runtime_version.strip():
            raise ValueError("expected_runtime_version must be non-empty")
        self.model_id = model_id
        self._model_path = model_path.expanduser().resolve()
        self._library_path = library_path.expanduser().resolve()
        self._language_code = language_code
        self._expected_runtime_version = expected_runtime_version
        self._library_loader = library_loader
        self._library = None
        self._recognizer = ctypes.c_void_p()
        self._streams: dict[int, _NemoStream] = {}
        self.runtime_version: str | None = None

    def load_model(self) -> None:
        if self._recognizer.value:
            return
        library = self._open_verified_library()
        backend = _BackendConfig(size=ctypes.sizeof(_BackendConfig), gpu=-1)
        model_path = os.fsencode(self._model_path)
        model = _ModelConfig(
            size=ctypes.sizeof(_ModelConfig),
            path=model_path,
            name=None,
        )
        config = _RecognizerConfig(
            size=ctypes.sizeof(_RecognizerConfig),
            backend=ctypes.pointer(backend),
            model=ctypes.pointer(model),
        )
        recognizer = ctypes.c_void_p()
        self._check(
            library,
            library.nemo_speech_asr_create(
                ctypes.byref(config), ctypes.byref(recognizer)
            ),
        )
        if not recognizer.value:
            raise RuntimeError("NeMo-Speech.cpp returned an empty recognizer")
        self._library = library
        self._recognizer = recognizer

    def verify_runtime_identity(self) -> str:
        """Verify local files and the stable ABI version without loading a model."""

        self._open_verified_library()
        assert self.runtime_version is not None
        return self.runtime_version

    def _open_verified_library(self):
        if not self._model_path.is_file():
            raise FileNotFoundError(self._model_path)
        if not self._library_path.is_file():
            raise FileNotFoundError(self._library_path)
        library = self._library_loader(os.fspath(self._library_path))
        self._configure_api(library)
        version = library.nemo_speech_asr_version()
        if not version:
            raise RuntimeError("NeMo-Speech.cpp returned an empty version")
        self.runtime_version = version.decode("utf-8", errors="strict")
        if self.runtime_version != self._expected_runtime_version:
            raise RuntimeError("NeMo-Speech.cpp runtime identity mismatch")
        return library

    def create_stream(self) -> object:
        library = self._require_library()
        options = library.nemo_speech_asr_recognition_options_default()
        options.request_id = None
        language = self._language_code.encode("utf-8")
        options.language_code = language
        options.interim_results = True
        options.max_alternatives = 1
        handle = ctypes.c_void_p()
        self._check(
            library,
            library.nemo_speech_asr_streaming_recognize(
                self._recognizer, ctypes.byref(options), ctypes.byref(handle)
            ),
        )
        if not handle.value:
            raise RuntimeError("NeMo-Speech.cpp returned an empty stream")
        stream = _NemoStream(handle=handle)
        self._streams[handle.value] = stream
        return stream

    def accept_waveform(self, stream: object, samples: Sequence[float]) -> None:
        selected = self._require_stream(stream)
        if not samples:
            raise ValueError("samples must be non-empty")
        values = (ctypes.c_float * len(samples))(*samples)
        library = self._require_library()
        self._check(
            library,
            library.nemo_speech_asr_stream_push_f32(
                selected.handle,
                values,
                len(samples),
                16_000,
            ),
        )

    def is_ready(self, stream: object) -> bool:
        selected = self._require_stream(stream)
        if selected.pending_result is not None:
            return True
        result = ctypes.c_void_p()
        library = self._require_library()
        self._check(
            library,
            library.nemo_speech_asr_stream_next(
                selected.handle, ctypes.byref(result)
            ),
        )
        if not result.value:
            return False
        selected.pending_result = result
        return True

    def decode_stream(self, stream: object) -> None:
        selected = self._require_stream(stream)
        if selected.pending_result is None:
            raise RuntimeError("no pending NeMo-Speech.cpp result")
        library = self._require_library()
        result = selected.pending_result
        selected.pending_result = None
        try:
            count = int(library.nemo_speech_asr_result_alternative_count(result))
            selected.alternative_count = count
            selected.final_seen = bool(library.nemo_speech_asr_result_is_final(result))
            if count:
                value = library.nemo_speech_asr_result_transcript(result, 0)
                if value:
                    selected.text = value.decode("utf-8", errors="strict").strip()
        finally:
            library.nemo_speech_asr_result_destroy(result)

    def get_text(self, stream: object) -> str:
        selected = self._require_stream(stream)
        if selected.finish_requested and not selected.final_seen:
            raise RuntimeError("NeMo-Speech.cpp did not return a final result")
        return selected.text

    def input_finished(self, stream: object) -> None:
        selected = self._require_stream(stream)
        library = self._require_library()
        self._check(
            library,
            library.nemo_speech_asr_stream_finish(selected.handle),
        )
        selected.finish_requested = True

    def close_stream(self, stream: object) -> None:
        selected = self._require_stream(stream)
        if selected.pending_result is not None:
            self._require_library().nemo_speech_asr_result_destroy(
                selected.pending_result
            )
            selected.pending_result = None
        self._require_library().nemo_speech_asr_stream_close(selected.handle)
        selected.closed = True
        if selected.handle.value:
            self._streams.pop(selected.handle.value, None)

    def close(self) -> None:
        if self._library is None:
            return
        for stream in list(self._streams.values()):
            self.close_stream(stream)
        if self._recognizer.value:
            self._library.nemo_speech_asr_destroy(self._recognizer)
        self._recognizer = ctypes.c_void_p()
        self._library = None

    def _require_library(self):
        if self._library is None or not self._recognizer.value:
            raise RuntimeError("NeMo-Speech.cpp model is not loaded")
        return self._library

    @staticmethod
    def _require_stream(stream: object) -> _NemoStream:
        if not isinstance(stream, _NemoStream) or stream.closed:
            raise RuntimeError("NeMo-Speech.cpp stream is closed or invalid")
        return stream

    @staticmethod
    def _check(library, status: int) -> None:
        if status == NEMO_SPEECH_ASR_OK:
            return
        detail = library.nemo_speech_asr_last_error()
        message = detail.decode("utf-8", errors="replace") if detail else "unknown"
        raise RuntimeError(f"NeMo-Speech.cpp status {status}: {message}")

    @staticmethod
    def _configure_api(library) -> None:
        library.nemo_speech_asr_version.argtypes = []
        library.nemo_speech_asr_version.restype = ctypes.c_char_p
        library.nemo_speech_asr_last_error.argtypes = []
        library.nemo_speech_asr_last_error.restype = ctypes.c_char_p
        library.nemo_speech_asr_create.argtypes = [
            ctypes.POINTER(_RecognizerConfig),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        library.nemo_speech_asr_create.restype = ctypes.c_int
        library.nemo_speech_asr_destroy.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_destroy.restype = None
        library.nemo_speech_asr_recognition_options_default.argtypes = []
        library.nemo_speech_asr_recognition_options_default.restype = (
            _RecognitionOptions
        )
        library.nemo_speech_asr_streaming_recognize.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_RecognitionOptions),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        library.nemo_speech_asr_streaming_recognize.restype = ctypes.c_int
        library.nemo_speech_asr_stream_push_f32.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
            ctypes.c_int32,
        ]
        library.nemo_speech_asr_stream_push_f32.restype = ctypes.c_int
        library.nemo_speech_asr_stream_finish.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_stream_finish.restype = ctypes.c_int
        library.nemo_speech_asr_stream_next.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        library.nemo_speech_asr_stream_next.restype = ctypes.c_int
        library.nemo_speech_asr_stream_close.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_stream_close.restype = None
        library.nemo_speech_asr_result_is_final.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_result_is_final.restype = ctypes.c_bool
        library.nemo_speech_asr_result_alternative_count.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_result_alternative_count.restype = ctypes.c_size_t
        library.nemo_speech_asr_result_transcript.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]
        library.nemo_speech_asr_result_transcript.restype = ctypes.c_char_p
        library.nemo_speech_asr_result_destroy.argtypes = [ctypes.c_void_p]
        library.nemo_speech_asr_result_destroy.restype = None
