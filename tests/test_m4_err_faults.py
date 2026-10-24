"""M4-ERR WP1 portable contract tests."""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import asdict
from pathlib import Path

import pytest

from sbd.core import error_observer
from sbd.core.display import status_bar
from sbd.core.display.hints import DisplayHint
from sbd.core.event_bus import EventBus, FatalDispatchError
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.faults import (
    SAFE_FAULT_SUMMARIES,
    BackendDisposition,
    ComponentSystemFault,
    safe_category_for_code,
)
from sbd.perception.listen import ASRResult, Listen, MockASRAdapter


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


class _Audio:
    def frames(self):
        async def generate():
            yield b"\0" * 640

        return generate()


async def _taxonomy_path(kind: str) -> dict[str, int]:
    counters = {"facts": 0, "faults": 0, "diagnostics": 0, "fatal": 0}
    bus = EventBus()

    async def fact(event: PerceptionResult) -> None:
        counters["facts"] += 1

    async def fault(event: ErrorOccurred) -> None:
        counters["faults"] += 1

    bus.subscribe(PerceptionResult, fact)
    bus.subscribe(ErrorOccurred, fault)
    if kind == "request-outcome":
        await Listen(
            audio_input=_Audio(), asr=MockASRAdapter((ASRResult(""),)), bus=bus,
        ).perceive("session", 1, 1, 1.0)
    elif kind == "system-fault":
        system_fault = _fault(BackendDisposition.REBUILD_REQUIRED,
                              keys=("backend.perception.listen.asr",))
        with pytest.raises(ComponentSystemFault):
            await Listen(
                audio_input=_Audio(), asr=MockASRAdapter((system_fault,)), bus=bus,
            ).perceive("session", 1, 1, 1.0)
    elif kind == "degradation":
        from sbd.core.display.arbiter import DisplayArbiter

        class Device:
            def size(self): return (1, 1)
            def clear(self): pass
            def write_pixels(self, pixels): pass
            def show(self): raise RuntimeError("PRIVATE_DISPLAY")

        class Renderer:
            def validate(self, hint): pass
            def render(self, *, size, model): return b"\0\0"

        class Logger:
            def error(self, message, *, extra): counters["diagnostics"] += 1
            def debug(self, *args): pass

        display = DisplayArbiter(Device(), Renderer(), logger=Logger())
        await display.start()
        await display.stop()
    elif kind == "cancellation":
        adapter = MockASRAdapter(blocked=True)
        listener = Listen(audio_input=_Audio(), asr=adapter, bus=bus)
        operation = asyncio.create_task(listener.perceive("session", 1, 1, 5.0))
        await adapter.entered.wait()
        await listener.abort()
        await operation
    else:
        fatal_bus = EventBus()

        async def fail(event: ErrorOccurred) -> None:
            raise RuntimeError("PRIVATE_FATAL")

        fatal_bus.subscribe(ErrorOccurred, fail)
        with pytest.raises(FatalDispatchError):
            await fatal_bus.publish(_fault(BackendDisposition.REUSABLE).to_event())
        fatal_waiter = asyncio.create_task(fatal_bus.wait_fatal())
        with pytest.raises(FatalDispatchError):
            await fatal_waiter
        counters["fatal"] += 1
    return counters


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    ("request-outcome", "system-fault", "degradation", "cancellation", "fatal"),
    ids=("request-outcome", "system-fault", "optional-degradation", "cancellation", "fatal"),
)
async def test_m4_err_pu_003_runtime_taxonomy_is_mutually_exclusive(kind: str) -> None:
    counters = await _taxonomy_path(kind)
    assert counters == {
        "facts": int(kind == "request-outcome"),
        "faults": int(kind == "system-fault"),
        "diagnostics": int(kind == "degradation"),
        "fatal": int(kind == "fatal"),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("proof", (True, False), ids=("timeout-proof", "timeout-unproven"))
async def test_m4_err_pu_003_timeout_requires_reusable_proof(proof: bool) -> None:
    class TimeoutASR(MockASRAdapter):
        @property
        def ready_for_next(self) -> bool:
            return proof

        async def abort(self) -> None:
            self.release.set()

    bus = EventBus()
    facts: list[PerceptionResult] = []
    faults: list[ErrorOccurred] = []
    bus.subscribe(PerceptionResult, lambda event: _append(facts, event))
    bus.subscribe(ErrorOccurred, lambda event: _append(faults, event))
    listener = Listen(audio_input=_Audio(), asr=TimeoutASR(blocked=True), bus=bus)
    if proof:
        await listener.perceive("session", 1, 1, 0.001)
        assert len(facts) == 1 and facts[0].status == "timeout" and faults == []
    else:
        with pytest.raises(ComponentSystemFault) as raised:
            await listener.perceive("session", 1, 1, 0.001)
        assert raised.value.code == "ASR_TIMEOUT_UNPROVEN"
        assert facts == [] and [event.code for event in faults] == ["ASR_TIMEOUT_UNPROVEN"]


async def _append(target: list, event) -> None:
    target.append(event)


def _assert_sentinel_absent(sentinel: str, *surfaces: object) -> None:
    assert all(sentinel not in repr(surface) for surface in surfaces)


@pytest.mark.asyncio
async def test_m4_err_pu_003_unknown_exception_is_typed_unproven() -> None:
    class UnknownASR(MockASRAdapter):
        legacy_neutral = False

    bus = EventBus()
    faults: list[ErrorOccurred] = []
    bus.subscribe(ErrorOccurred, lambda event: _append(faults, event))
    unknown = RuntimeError("PRIVATE_NATIVE")
    listener = Listen(
        audio_input=_Audio(), asr=UnknownASR((unknown,)), bus=bus,
    )
    with pytest.raises(ComponentSystemFault) as raised:
        await listener.perceive("session", 1, 1, 1.0)
    assert raised.value.code == "ASR_UNEXPECTED"
    assert raised.value.backend is BackendDisposition.UNPROVEN
    assert raised.value.__cause__ is unknown
    assert [event.code for event in faults] == ["ASR_UNEXPECTED"]


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
    assert status_bar.safe_category_for_code is safe_category_for_code


def test_m4_err_pu_007_display_and_log_share_projection_object() -> None:
    assert error_observer.safe_category_for_code is safe_category_for_code
    assert status_bar.safe_category_for_code is safe_category_for_code


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
def test_m4_err_pu_009_private_sentinels_rejected(sentinel: str, caplog) -> None:
    assert sentinel not in repr(SAFE_FAULT_SUMMARIES)
    with pytest.raises(ValueError):
        ComponentSystemFault(
            where="perception.listen",
            code="ASR_PROTOCOL_FAILED",
            safe_summary=sentinel,
            backend=BackendDisposition.REUSABLE,
        )

    async def run() -> tuple[ErrorOccurred, DisplayHint]:
        class Arbiter:
            def __init__(self) -> None:
                self.hints: list[DisplayHint] = []

            def write_status_slot(self, slot, hint) -> None:
                if slot == "error":
                    self.hints.append(hint)

        bus = EventBus()
        observer = error_observer.ErrorLoggingObserver(bus)
        arbiter = Arbiter()
        display = status_bar.StatusBar(arbiter, bus)
        await observer.start()
        await display.start()
        fault = _fault(BackendDisposition.REUSABLE)
        try:
            raise fault from RuntimeError(sentinel)
        except ComponentSystemFault as raised:
            event = raised.to_event()
        await bus.publish(event)
        await display.stop()
        await observer.stop()
        return event, arbiter.hints[-1]

    with caplog.at_level(logging.ERROR, logger="sbd.error_observer"):
        event, hint = asyncio.run(run())
    _assert_sentinel_absent(sentinel, event, caplog.text, hint)
    assert hint.data["category"] == "asr"


@pytest.mark.parametrize("surface", ("event", "structured-log", "display"))
def test_m4_err_pu_009_negative_surface_leak_is_rejected(surface: str) -> None:
    sentinel = "PAYLOAD_SENTINEL"
    surfaces = {
        "event": ({"error": sentinel}, {"message": "safe"}, {"category": "internal"}),
        "structured-log": ({"error": "safe"}, {"message": sentinel}, {"category": "internal"}),
        "display": ({"error": "safe"}, {"message": "safe"}, {"text": sentinel}),
    }[surface]
    with pytest.raises(AssertionError):
        _assert_sentinel_absent(sentinel, *surfaces)


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
