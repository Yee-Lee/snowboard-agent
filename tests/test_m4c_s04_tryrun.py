"""Workstation try-run for M4C-PI-S04 short-press interrupts."""

from __future__ import annotations

import asyncio
import copy
import importlib.util
from pathlib import Path

import pytest

from sbd.action.speak import Speak
from sbd.core.display import DisplayArbiter, DisplayHint
from sbd.core.display.session import SessionDisplay
from sbd.core.display.status_bar import StatusBar
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, LLMResponse,
    PerceptionResult, ShutdownRequested,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager import StateManager
from sbd.core.state_manager.convergence import CancelTimeoutPolicy, DefaultSessionConverger
from sbd.core.state_manager.notices import _WakeAckElapsed
from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
from tests.test_m2_wrk_003 import _validator


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m4c_s04_oracle", ROOT / "scripts/m4c_s04_oracle.py"
)
assert SPEC is not None and SPEC.loader is not None
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def _valid_evidence(variant: str = "PERCEPTION") -> dict:
    return {
        "schema_version": 1,
        "variant": variant,
        "interrupt": {
            "operation": variant,
            "state": variant,
            "operation_active": True,
            "main_text": "已中止",
        },
        "affected_success_count": 0,
        "post_interrupt_start_count": 0,
        "unexpected_error_count": 0,
        "cleanup": {
            "state": "IDLE",
            "main_empty": True,
            "affected_owner_idle": True,
        },
    }


@pytest.mark.parametrize("variant", ORACLE.VARIANTS)
def test_s04_oracle_accepts_each_interrupt_variant(variant: str) -> None:
    public = ORACLE.validate_s04_private_evidence(_valid_evidence(variant))
    assert public["scenario_code"] == f"M4C-PI-S04/{variant}"
    assert "已中止" not in repr(public)


def test_s04_action_accepts_b2_playback_while_state_is_think() -> None:
    value = _valid_evidence("ACTION")
    value["interrupt"]["state"] = "THINK"
    public = ORACLE.validate_s04_private_evidence(value)
    assert public["interrupt_state_code"] == "THINK"
    assert public["affected_operation_code"] == "ACTION"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value["interrupt"].update(operation_active=False),
         "M4C_S04_OPERATION_NOT_ACTIVE"),
        (lambda value: value["interrupt"].update(main_text=None),
         "M4C_S04_INTERRUPT_DISPLAY_MISSING"),
        (lambda value: value.update(affected_success_count=1),
         "M4C_S04_OLD_SUCCESS_PUBLISHED"),
        (lambda value: value.update(post_interrupt_start_count=1),
         "M4C_S04_LATE_OPERATION_STARTED"),
        (lambda value: value.update(unexpected_error_count=1),
         "M4C_S04_SYSTEM_FAULT_FABRICATED"),
        (lambda value: value["cleanup"].update(affected_owner_idle=False),
         "M4C_S04_AFFECTED_OWNER_NOT_IDLE"),
    ],
)
def test_s04_oracle_rejects_product_risk(mutation, code: str) -> None:
    value = copy.deepcopy(_valid_evidence())
    mutation(value)
    with pytest.raises(ORACLE.S04OracleError, match=code):
        ORACLE.validate_s04_private_evidence(value)


class _Renderer:
    def validate(self, hint: DisplayHint) -> None:
        assert hint.template in {"status.state", "main.text"}

    def render(self, *, size, model) -> bytes:
        return bytes(size[0] * size[1] * 2)


class _Display:
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    def clear(self) -> None: pass
    def write_pixels(self, value: bytes) -> None: pass
    def show(self) -> None: pass
    def size(self): return (128, 128)


class _Conversation:
    async def open_conversation(self, session_id: str, generation: int):
        return ConversationReady(session_id, generation)

    async def close_conversation(self, session_id: str, generation: int, reason: str):
        return ConversationCloseProof(session_id, generation, True, True, True)

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


class _Worker:
    def __init__(self, bus: EventBus, phase: str, *, blocked: bool) -> None:
        self.bus = bus
        self.phase = phase
        self.blocked = blocked
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.active = False
        self.start_count = 0
        self.abort_count = 0

    async def start(self) -> None: pass
    async def stop(self) -> None: pass

    async def abort(self) -> None:
        self.abort_count += 1
        self.release.set()

    async def force_abort(self) -> ForceAbortReport:
        self.release.set()
        return ForceAbortReport()

    async def _hold(self) -> None:
        self.start_count += 1
        self.active = True
        self.started.set()
        try:
            await self.release.wait()
        finally:
            self.active = False

    async def perceive(self, session_id, turn_id, correlation_id, timeout_seconds):
        del timeout_seconds
        if self.blocked:
            await self._hold()
            return
        self.start_count += 1
        await self.bus.publish(PerceptionResult(
            "listen", "ok", "請說一個故事", {},
            session_id, turn_id, correlation_id,
        ))

    async def reason(
        self, session_id, turn_id, correlation_id, results, pending,
        *, conversation_generation,
    ):
        del results, pending, conversation_generation
        if self.blocked:
            await self._hold()
            return
        self.start_count += 1
        await self.bus.publish(LLMResponse(
            action_kind="speak",
            action_payload={"text": "這是一個足以播放的回答。"},
            post_action_route="KEEP_NEXT",
            next_perceptions=("listen",),
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        ))

    async def execute(self, session_id, turn_id, correlation_id, payload):
        del session_id, turn_id, correlation_id, payload
        await self._hold()


class _TTS:
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()

    def synthesize(self, text: str):
        assert text

        async def frames():
            yield bytes(640)

        return frames()


class _BlockingAudio:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.active = False
        self.start_count = 0

    async def play(self, pcm) -> None:
        async for chunk in pcm:
            assert chunk
            self.start_count += 1
            self.active = True
            self.started.set()
            try:
                await self.release.wait()
            finally:
                self.active = False


def _main_text(arbiter: DisplayArbiter) -> str | None:
    hint = arbiter.snapshot().main
    return None if hint is None else hint.data.get("text")


async def _wait_until(predicate, timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


async def _run_variant(variant: str) -> dict:
    bus = EventBus()
    listen = _Worker(bus, "PERCEPTION", blocked=variant == "PERCEPTION")
    reasoner = _Worker(bus, "THINK", blocked=variant == "THINK")
    audio = _BlockingAudio()
    speak = Speak(tts=_TTS(), audio_output=audio, bus=bus)
    rest = _Worker(bus, "REST", blocked=True)
    catalog = WorkerCatalog()
    catalog.register_perception("listen", listen)
    catalog.set_reasoner(reasoner)
    catalog.register_action("speak", speak)
    catalog.register_action("rest", rest)
    catalog.seal()
    sm = StateManager(
        bus=bus,
        workers=catalog,
        wake_ack_seconds=60,
        converger=DefaultSessionConverger(timeouts=CancelTimeoutPolicy(
            abort_default_seconds=0.2,
            force_abort_default_seconds=0.2,
        )),
        action_validator=_validator(),
    )
    conversation = _Conversation()
    arbiter = DisplayArbiter(_Display(), _Renderer())
    status = StatusBar(arbiter, bus)
    session_display = SessionDisplay(arbiter, bus, sm)
    facts: list[object] = []
    errors: list[ErrorOccurred] = []
    publications: list[str | None] = []

    async def fact(event) -> None:
        facts.append(event)

    async def error(event: ErrorOccurred) -> None:
        errors.append(event)

    for kind in (PerceptionResult, LLMResponse, ActionCompleted):
        bus.subscribe(kind, fact, name=f"m4c.s04.{kind.__name__.lower()}")
    bus.subscribe(ErrorOccurred, error, name="m4c.s04.error")

    await arbiter.start()
    await sm.start()
    sm.set_conversation_lifecycle(conversation)
    await status.start()
    await session_display.start()
    original_write_main = arbiter.write_main

    def observed_write_main(hint) -> None:
        publications.append(None if hint is None else hint.data.get("text"))
        original_write_main(hint)

    arbiter.write_main = observed_write_main
    target = {"PERCEPTION": listen, "THINK": reasoner, "ACTION": audio}[variant]
    try:
        await bus.publish(ButtonPressed("conversation", 100))
        await _wait_until(lambda: sm._session is not None)
        assert sm._session is not None
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await asyncio.wait_for(target.started.wait(), 2.0)
        assert sm.state == variant and target.active
        starts_at_interrupt = target.start_count
        facts_at_interrupt = len(facts)

        await bus.publish(ButtonPressed("conversation", 100))
        interrupt_main = _main_text(arbiter)
        await _wait_until(lambda: sm.state == "IDLE")
        await asyncio.wait_for(sm._inbox.join(), 2.0)
        await asyncio.sleep(0)

        affected_type = {
            "PERCEPTION": PerceptionResult,
            "THINK": LLMResponse,
            "ACTION": ActionCompleted,
        }[variant]
        affected_successes = [item for item in facts if isinstance(item, affected_type)]
        assert len(facts) == facts_at_interrupt
        evidence = {
            "schema_version": 1,
            "variant": variant,
            "interrupt": {
                "operation": variant,
                "state": variant,
                "operation_active": True,
                "main_text": interrupt_main,
            },
            "affected_success_count": len(affected_successes),
            "post_interrupt_start_count": target.start_count - starts_at_interrupt,
            "unexpected_error_count": len(errors),
            "cleanup": {
                "state": sm.state,
                "main_empty": _main_text(arbiter) is None,
                "affected_owner_idle": not target.active,
            },
        }
        assert publications.count("已中止") == 1
        return evidence
    finally:
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await session_display.stop()
        await status.stop()
        await sm.stop()
        await arbiter.stop()


@pytest.mark.parametrize("variant", ORACLE.VARIANTS)
def test_s04_real_state_manager_short_press_tryrun(variant: str) -> None:
    evidence = asyncio.run(_run_variant(variant))
    public = ORACLE.validate_s04_private_evidence(evidence)
    assert public["interrupt_state_code"] == variant
