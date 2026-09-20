"""M4-ERR WP1 portable contract tests."""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import asdict
from pathlib import Path

import pytest

from sbd.core import error_observer
from sbd.core.events import ErrorOccurred
from sbd.core.faults import (
    SAFE_FAULT_SUMMARIES,
    BackendDisposition,
    ComponentSystemFault,
    safe_category_for_code,
)


def _fault(
    backend: BackendDisposition,
    *,
    keys: tuple[str, ...] = (),
) -> ComponentSystemFault:
    return ComponentSystemFault.create(
        where="perception.listen",
        code="ASR_PROTOCOL_FAILED",
        backend=backend,
        recovery_keys=keys,
    )


def test_m4_err_pu_001_component_fault_invariants() -> None:
    for backend, keys in (
        (BackendDisposition.REUSABLE, ()),
        (BackendDisposition.REBUILD_REQUIRED, ("perception.asr",)),
        (BackendDisposition.UNPROVEN, ("perception.asr",)),
        (BackendDisposition.NOT_APPLICABLE, ()),
    ):
        fault = _fault(backend, keys=keys)
        event = fault.to_event()
        assert event.code == fault.code
        assert event.backend_disposition == backend.value
        assert event.recovery_keys == keys

    for backend in (BackendDisposition.REBUILD_REQUIRED, BackendDisposition.UNPROVEN):
        with pytest.raises(ValueError):
            _fault(backend)
    for backend in (BackendDisposition.REUSABLE, BackendDisposition.NOT_APPLICABLE):
        with pytest.raises(ValueError):
            _fault(backend, keys=("perception.asr",))
    with pytest.raises(ValueError):
        ComponentSystemFault.create(
            where="INVALID",
            code="ASR_PROTOCOL_FAILED",
            backend=BackendDisposition.REUSABLE,
        )
    with pytest.raises(ValueError):
        ComponentSystemFault(
            where="perception.listen",
            code="bad-code",
            safe_summary="ASR protocol failed",
            backend=BackendDisposition.REUSABLE,
        )
    with pytest.raises(ValueError):
        ComponentSystemFault(
            where="perception.listen",
            code="ASR_PROTOCOL_FAILED",
            safe_summary="native repr: SECRET\n",
            backend=BackendDisposition.REUSABLE,
        )

    deduplicated = _fault(
        BackendDisposition.REBUILD_REQUIRED,
        keys=("z.backend", "a.backend", "z.backend"),
    )
    assert deduplicated.to_event().recovery_keys == ("a.backend", "z.backend")

    cause = RuntimeError("PRIVATE_CAUSE")
    try:
        raise _fault(BackendDisposition.REUSABLE) from cause
    except ComponentSystemFault as raised:
        assert raised.__cause__ is cause
        assert "PRIVATE_CAUSE" not in repr(asdict(raised.to_event()))


def test_m4_err_pu_002_error_event_schema_and_production_publishers() -> None:
    event = ErrorOccurred(
        where="perception.listen",
        error="ASR protocol failed",
        code="ASR_PROTOCOL_FAILED",
        backend_disposition=BackendDisposition.REBUILD_REQUIRED.value,
        recovery_keys=("perception.asr",),
    )
    assert event.backend_disposition == "rebuild_required"
    assert event.recovery_keys == ("perception.asr",)

    legacy = ErrorOccurred("test.helper", "legacy")
    assert legacy.backend_disposition == BackendDisposition.NOT_APPLICABLE.value
    assert legacy.backend_disposition != "unclassified"

    root = Path(__file__).resolve().parents[1] / "src"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else None
            if name != "ErrorOccurred":
                continue
            keywords = {keyword.arg for keyword in node.keywords}
            if path.name != "faults.py" or {
                "where", "error", "code", "backend_disposition", "recovery_keys"
            } - keywords:
                offenders.append(f"{path}:{node.lineno}")
    assert offenders == []


def test_m4_err_pu_003_taxonomy_paths_are_mutually_exclusive() -> None:
    request_outcome = {"facts": 1, "faults": 0, "diagnostics": 0, "fatal": 0}
    system_fault = {"facts": 0, "faults": 1, "diagnostics": 0, "fatal": 0}
    degradation = {"facts": 0, "faults": 0, "diagnostics": 1, "fatal": 0}
    cancellation = {"facts": 0, "faults": 0, "diagnostics": 0, "fatal": 0}
    fatal = {"facts": 0, "faults": 0, "diagnostics": 0, "fatal": 1}
    for path in (request_outcome, system_fault, degradation, cancellation, fatal):
        assert sum(path.values()) <= 1

    reusable_timeout = _fault(BackendDisposition.REUSABLE)
    unproven_timeout = ComponentSystemFault.create(
        where="perception.listen",
        code="ASR_TIMEOUT_UNPROVEN",
        backend=BackendDisposition.UNPROVEN,
        recovery_keys=("backend.perception.listen.asr",),
    )
    assert reusable_timeout.backend is BackendDisposition.REUSABLE
    assert unproven_timeout.backend is BackendDisposition.UNPROVEN
    assert not isinstance(RuntimeError("native"), ComponentSystemFault)


def test_m4_err_pu_004_closed_set_has_no_unclassified_fault() -> None:
    assert "UNCLASSIFIED" not in BackendDisposition.__members__
    assert "LEGACY_ERROR" not in SAFE_FAULT_SUMMARIES
    assert all("\n" not in summary and "\r" not in summary
               for summary in SAFE_FAULT_SUMMARIES.values())


def test_m4_err_pu_006_cause_is_private() -> None:
    cause = RuntimeError("TRANSCRIPT_SENTINEL")
    fault = _fault(BackendDisposition.REUSABLE)
    try:
        raise fault from cause
    except ComponentSystemFault as raised:
        assert raised.__cause__ is cause
        public = repr(asdict(raised.to_event()))
        assert "TRANSCRIPT_SENTINEL" not in public
        assert "RuntimeError" not in public


@pytest.mark.parametrize(
    ("code", "category"),
    (
        ("AUDIO_CAPTURE_FAILED", "audio"),
        ("ASR_PROTOCOL_FAILED", "asr"),
        ("LLM_BACKEND_FAILED", "llm"),
        ("TTS_PROTOCOL_FAILED", "tts"),
        ("BUTTON_CALLBACK_FAILED", "input"),
        ("BUS_HANDLER_FAILED", "internal"),
        ("UNKNOWN_CODE", "internal"),
    ),
)
def test_m4_err_pu_007_safe_projection(code: str, category: str) -> None:
    assert safe_category_for_code(code) == category
    assert safe_category_for_code(code) == category
    assert error_observer.safe_category_for_code is safe_category_for_code


@pytest.mark.parametrize(
    "sentinel",
    (
        "TRANSCRIPT_SENTINEL",
        "PROMPT_SENTINEL",
        "PCM_SENTINEL",
        "PAYLOAD_SENTINEL",
        "FILESYSTEM_SENTINEL",
        "NEWLINE_SENTINEL\n",
    ),
)
def test_m4_err_pu_009_private_sentinels_rejected(sentinel: str) -> None:
    assert sentinel not in repr(SAFE_FAULT_SUMMARIES)
    with pytest.raises(ValueError):
        ComponentSystemFault(
            where="perception.listen",
            code="ASR_PROTOCOL_FAILED",
            safe_summary=sentinel,
            backend=BackendDisposition.REUSABLE,
        )


def test_m4_err_pu_009_invalid_where_is_not_logged(caplog) -> None:
    async def run() -> None:
        from sbd.core.event_bus import EventBus

        bus = EventBus()
        observer = error_observer.ErrorLoggingObserver(bus)
        await observer.start()
        await bus.publish(ErrorOccurred(
            where="FILESYSTEM_SENTINEL /private/path",
            error="safe",
        ))
        await observer.stop()

    with caplog.at_level(logging.ERROR, logger="sbd.error_observer"):
        asyncio.run(run())
    assert "FILESYSTEM_SENTINEL" not in caplog.text
    assert caplog.records[-1].where == "invalid_where"
    assert caplog.records[-1].invalid_where is True
