"""Typed, privacy-safe component fault contract for M4 production paths."""

from __future__ import annotations

import re
from enum import StrEnum

from sbd.core.events import ErrorOccurred


class BackendDisposition(StrEnum):
    REUSABLE = "reusable"
    REBUILD_REQUIRED = "rebuild_required"
    UNPROVEN = "unproven"
    NOT_APPLICABLE = "not_applicable"


SAFE_FAULT_SUMMARIES: dict[str, str] = {
    "ASR_FRAME_CONTRACT_VIOLATION": "ASR frame contract failed",
    "ASR_INFERENCE_FAILED": "ASR inference failed",
    "ASR_PROTOCOL_FAILED": "ASR protocol failed",
    "ASR_TIMEOUT_UNPROVEN": "ASR timeout cleanup unproven",
    "ASR_UNEXPECTED": "ASR operation failed",
    "AUDIO_CAPTURE_FAILED": "Audio capture failed",
    "AUDIO_PLAYBACK_FAILED": "Audio playback failed",
    "BUTTON_CALLBACK_FAILED": "Button callback failed",
    "BUS_HANDLER_FAILED": "Event dispatch failed",
    "DISPLAY_RENDER_DISABLED": "Display rendering disabled",
    "GPIO_EVENT_READ_FAILED": "GPIO event read failed",
    "LISTEN_UNEXPECTED": "Listen operation failed",
    "LOOK_UNEXPECTED": "Look operation failed",
    "LLM_BACKEND_FAILED": "LLM backend failed",
    "LLM_CLEANUP_UNPROVEN": "LLM cleanup unproven",
    "LLM_OBSERVATION_FAILED": "LLM observation failed",
    "LLM_PROTOCOL_FAILED": "LLM protocol failed",
    "LLM_UNEXPECTED": "LLM operation failed",
    "READ_UNEXPECTED": "Read operation failed",
    "REST_OBSERVATION_FAILED": "REST_OBSERVATION_FAILED",
    "SPEAK_UNEXPECTED": "Speak operation failed",
    "TOOL_UNEXPECTED": "Tool operation failed",
    "TTS_GENERATION_FAILED": "TTS generation failed",
    "TTS_PROTOCOL_FAILED": "TTS protocol failed",
}

_WHERE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


def safe_category_for_code(code: str) -> str:
    """Project a detailed fault code onto a safe public category."""

    if code.startswith("AUDIO_"):
        return "audio"
    if code.startswith("ASR_"):
        return "asr"
    if code.startswith("LLM_"):
        return "llm"
    if code.startswith("TTS_"):
        return "tts"
    if code.startswith(("BUTTON_", "GPIO_")):
        return "input"
    return "internal"


def legacy_error_event(*, where: str, error: str, exception_type: str) -> ErrorOccurred:
    """Build the retained pre-M4 product-neutral event used by legacy mock flows."""

    return ErrorOccurred(
        where=where,
        error=error,
        exception_type=exception_type,
        code="LEGACY_ERROR",
        backend_disposition=BackendDisposition.NOT_APPLICABLE.value,
        recovery_keys=(),
    )


class ComponentSystemFault(RuntimeError):
    """A classified system fault safe to project into an ``ErrorOccurred``."""

    def __init__(
        self,
        *,
        where: str,
        code: str,
        safe_summary: str,
        backend: BackendDisposition,
        recovery_keys: tuple[str, ...] = (),
    ) -> None:
        if not _WHERE_RE.fullmatch(where):
            raise ValueError("fault where must use the component namespace")
        if not _CODE_RE.fullmatch(code):
            raise ValueError("fault code is invalid")
        if SAFE_FAULT_SUMMARIES.get(code) != safe_summary:
            raise ValueError("safe_summary must be the declared constant for code")
        if "\n" in safe_summary or "\r" in safe_summary:
            raise ValueError("safe_summary must be single-line")
        if not isinstance(backend, BackendDisposition):
            raise TypeError("backend must be BackendDisposition")
        if not isinstance(recovery_keys, tuple) or any(
            not isinstance(key, str) or not key.strip() for key in recovery_keys
        ):
            raise ValueError("recovery_keys must contain non-empty strings")

        normalized_keys = tuple(sorted(set(recovery_keys)))
        if backend in {BackendDisposition.REBUILD_REQUIRED, BackendDisposition.UNPROVEN}:
            if not normalized_keys:
                raise ValueError(f"{backend.value} requires a recovery key")
        elif normalized_keys:
            raise ValueError(f"{backend.value} forbids recovery keys")

        self.where = where
        self.code = code
        self.safe_summary = safe_summary
        self.backend = backend
        self.recovery_keys = normalized_keys
        super().__init__(safe_summary)

    @classmethod
    def create(
        cls,
        *,
        where: str,
        code: str,
        backend: BackendDisposition,
        recovery_keys: tuple[str, ...] = (),
    ) -> "ComponentSystemFault":
        try:
            summary = SAFE_FAULT_SUMMARIES[code]
        except KeyError as exc:
            raise ValueError("fault code has no declared safe summary") from exc
        return cls(
            where=where,
            code=code,
            safe_summary=summary,
            backend=backend,
            recovery_keys=recovery_keys,
        )

    def to_event(self) -> ErrorOccurred:
        return ErrorOccurred(
            where=self.where,
            error=self.safe_summary,
            exception_type=None,
            code=self.code,
            backend_disposition=self.backend.value,
            recovery_keys=self.recovery_keys,
        )
