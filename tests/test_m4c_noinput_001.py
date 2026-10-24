"""M4C-NOINPUT-001 — Session streak and sanitized ASR request codes."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import asdict
import importlib.util
from pathlib import Path

import pytest

from sbd.adaptor.errors import AdapterRejected
from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.rest import Rest
from sbd.action.speak import Speak
from sbd.action.speak.tts import MockTTSAdapter
from sbd.action.tool import ToolRegistry
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.display import DisplayArbiter, DisplayHint
from sbd.core.display.session import SessionDisplay
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, PerceptionResult, StateChanged,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
from sbd.core.state_manager.session import SessionContext
from sbd.perception.listen.listener import Listen


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m4c_s03_oracle", ROOT / "scripts/m4c_s03_oracle.py"
)
assert SPEC is not None and SPEC.loader is not None
S03_ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S03_ORACLE)


class ProductReasoner:
    _product = True


class Worker:
    async def abort(self): pass
    async def force_abort(self): raise AssertionError


def _manager() -> StateManager:
    catalog = WorkerCatalog()
    catalog.register_perception("listen", Worker())
    catalog.set_reasoner(ProductReasoner())
    catalog.register_action("speak", Worker())
    catalog.register_action("rest", Worker())
    catalog.seal()
    return StateManager(bus=EventBus(), workers=catalog)


def _set_fact(sm: StateManager, fact: PerceptionResult, streak: int = 0) -> None:
    sm._session = SessionContext("session", "button", turn_id=1)
    sm._session.selected_perceptions = ("listen",)
    sm._session.no_input_streak = streak
    sm._session.perception_results = [fact]


@pytest.mark.parametrize(
    ("case", "fact"),
    [
        ("N01", PerceptionResult("listen", "timeout", None)),
        ("N03", PerceptionResult("listen", "error", None, {"asr_error_code": "NO_SPEECH"})),
        ("N04", PerceptionResult("listen", "ok", "   ")),
    ],
)
def test_m4c_noinput_001_first_no_input_retries_same_session(case, fact) -> None:
    sm = _manager()
    _set_fact(sm, fact)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_payload == {"text": "我沒聽清楚，請再說一次。"}
    assert response.post_action_route == "KEEP_NEXT"
    assert response.next_perceptions == ("listen",)
    assert sm._session is not None and sm._session.no_input_streak == 1


def test_m4c_noinput_001_n02_second_no_input_ends_without_speech() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "timeout", None), streak=1)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_kind == "rest"
    assert response.action_payload == {}
    assert response.post_action_route == "END_SESSION"
    assert sm._session is not None and sm._session.no_input_streak == 2


def test_m4c_noinput_001_n05_valid_text_resets_before_llm() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "ok", "有效內容"), streak=1)
    assert sm._m4c_no_input_response() is None
    assert sm._session is not None and sm._session.no_input_streak == 0


def test_m4c_noinput_001_n06_new_session_does_not_inherit_streak() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "timeout", None), streak=1)
    sm._session = SessionContext("new-session", "button")
    assert sm._session.no_input_streak == 0


def test_m4c_noinput_001_n07_multiple_utterances_does_not_change_streak() -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult(
        "listen", "error", None, {"asr_error_code": "MULTIPLE_UTTERANCES"}), streak=1)
    response = sm._m4c_no_input_response()
    assert response is not None
    assert response.action_payload == {"text": "請一次只說一句。"}
    assert response.post_action_route == "KEEP_NEXT"
    assert sm._session is not None and sm._session.no_input_streak == 1


@pytest.mark.parametrize("code", ["INFERENCE_REJECTED", "INVALID_FRAME", "BACKEND_FAILURE"])
def test_m4c_noinput_001_n08_n10_system_fault_is_not_retry(code) -> None:
    sm = _manager()
    _set_fact(sm, PerceptionResult("listen", "error", None, {"asr_error_code": code}), streak=1)
    assert sm._m4c_no_input_response() is None
    assert sm._session is not None and sm._session.no_input_streak == 1


@pytest.mark.parametrize("code", ["NO_SPEECH", "MULTIPLE_UTTERANCES"])
def test_m4c_noinput_001_n11_listener_preserves_only_stable_code(code) -> None:
    class Audio:
        def frames(self):
            async def values():
                yield b"\x00\x00"
            return values()

    class ASR:
        ready_for_next = True
        async def start(self): pass
        async def stop(self): pass
        async def abort(self): pass
        async def force_abort(self): raise AssertionError
        async def transcribe(self, frames):
            async for _ in frames:
                break
            raise AdapterRejected("PRIVATE NATIVE DETAIL", code=code)

    async def run():
        bus = EventBus()
        facts = []
        async def capture(event):
            facts.append(event)
        bus.subscribe(PerceptionResult, capture)
        listen = Listen(audio_input=Audio(), asr=ASR(), bus=bus)
        await listen.perceive("private-session", 1, 4, 1)
        assert len(facts) == 1
        assert facts[0].extra == {"asr_error_code": code}
        assert "PRIVATE" not in str(facts[0].extra)
    asyncio.run(run())


def _valid_s03_evidence() -> dict:
    return {
        "schema_version": 1,
        "perceptions": [
            {"status": "timeout", "session_id": "session", "turn_id": 1},
            {"status": "timeout", "session_id": "session", "turn_id": 2},
        ],
        "responses": [
            {
                "action_kind": "speak",
                "action_payload": {"text": S03_ORACLE.RETRY_TEXT},
                "post_action_route": "KEEP_NEXT",
            },
            {
                "action_kind": "rest",
                "action_payload": {},
                "post_action_route": "END_SESSION",
            },
        ],
        "actions": [
            {"kind": "speak", "status": "ok"},
            {"kind": "rest", "status": "ok"},
        ],
        "no_input_streaks": [1, 2],
        "reasoner_call_count": 0,
        "order": [
            "timeout_1", "retry_speak_complete", "listen_2_started",
            "timeout_2", "rest_complete", "idle",
        ],
        "playback": {"retry_play_count": 1, "complete": True},
        "cleanup": {
            "state": "IDLE",
            "status": "待命",
            "main_empty": True,
        },
    }


def test_m4c_noinput_001_s03_oracle_accepts_only_two_product_timeouts() -> None:
    public = S03_ORACLE.validate_s03_private_evidence(_valid_s03_evidence())
    assert public == {
        "schema_version": 1,
        "scenario_code": "M4C-PI-S03/TWO_TIMEOUTS",
        "timeout_count": 2,
        "streak_transitions": [1, 2],
        "retry_speak_count": 1,
        "rest_count": 1,
        "reasoner_call_count": 0,
        "same_session": True,
        "ordered_after_retry_playback": True,
        "terminal_state_code": "IDLE",
        "status_code": "IDLE_READY",
        "main_empty": True,
    }
    assert "'session'" not in repr(public)
    assert S03_ORACLE.RETRY_TEXT not in repr(public)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["perceptions"][1].update(status="error"),
            "M4C_S03_TIMEOUT_CLASSIFICATION_INVALID",
        ),
        (
            lambda value: value["responses"][0]["action_payload"].update(text="再試一次"),
            "M4C_S03_RETRY_RESPONSE_INVALID",
        ),
        (
            lambda value: value.update(reasoner_call_count=1),
            "M4C_S03_LLM_CALLED",
        ),
        (
            lambda value: value["perceptions"][1].update(session_id="other"),
            "M4C_S03_SESSION_CHANGED",
        ),
        (
            lambda value: value.update(order=[
                "timeout_1", "listen_2_started", "retry_speak_complete",
                "timeout_2", "rest_complete", "idle",
            ]),
            "M4C_S03_ORDER_INVALID",
        ),
        (
            lambda value: value["playback"].update(retry_play_count=2),
            "M4C_S03_RETRY_PLAYBACK_INVALID",
        ),
    ],
)
def test_m4c_noinput_001_s03_oracle_rejects_false_green(mutation, code) -> None:
    value = copy.deepcopy(_valid_s03_evidence())
    mutation(value)
    with pytest.raises(S03_ORACLE.S03OracleError, match=code):
        S03_ORACLE.validate_s03_private_evidence(value)


class _S03Renderer:
    def validate(self, hint: DisplayHint) -> None:
        assert hint.template in {"status.state", "main.text"}

    def render(self, *, size, model) -> bytes:
        return bytes(size[0] * size[1] * 2)


class _S03Display:
    def size(self): return (128, 128)
    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    def clear(self) -> None: pass
    def write_pixels(self, value: bytes) -> None: pass
    def show(self) -> None: pass


class _S03Conversation:
    def __init__(self) -> None:
        self.closed = False

    async def open_conversation(self, session_id, generation):
        return ConversationReady(session_id, generation)

    async def close_conversation(self, session_id, generation, reason):
        assert reason == "session_rest"
        self.closed = True
        return ConversationCloseProof(session_id, generation, True, True, True)

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


class _S03Reasoner:
    _product = True

    def __init__(self) -> None:
        self.calls = 0

    async def reason(self, *args, **kwargs) -> None:
        self.calls += 1
        raise AssertionError("S03 timeout path must not call the LLM")

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


class _S03Listen:
    def __init__(self, bus: EventBus, order: list[str]) -> None:
        self._bus = bus
        self._order = order
        self.calls = 0

    async def perceive(self, session_id, turn_id, correlation_id, timeout_seconds):
        assert timeout_seconds == 10.0
        self.calls += 1
        if self.calls == 2:
            self._order.append("listen_2_started")
        await self._bus.publish(PerceptionResult(
            "listen", "timeout", None, {}, session_id, turn_id, correlation_id
        ))

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


class _RecordingTTS(MockTTSAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []

    def synthesize(self, text: str):
        self.texts.append(text)
        return super().synthesize(text)


def test_m4c_noinput_001_s03_real_state_manager_vertical_path() -> None:
    async def run() -> None:
        bus = EventBus()
        order: list[str] = []
        listen = _S03Listen(bus, order)
        reasoner = _S03Reasoner()
        tts = _RecordingTTS()
        audio = MockAudioOutput()
        speak = Speak(tts=tts, audio_output=audio, bus=bus)
        rest = Rest(bus=bus)
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("speak", speak)
        catalog.register_action("rest", rest)
        catalog.seal()
        tools = ToolRegistry()
        tools.seal()
        sm = StateManager(
            bus=bus, workers=catalog, wake_ack_seconds=0.001,
            perception_timeouts={"listen": 10.0, "read": 0.5, "look": 3.0},
            action_validator=ActionPayloadValidator(tools=tools),
        )
        conversation = _S03Conversation()
        display = DisplayArbiter(_S03Display(), _S03Renderer())
        session_display = SessionDisplay(display, bus, sm)
        states: list[str] = []
        perceptions: list[PerceptionResult] = []
        responses: list[dict] = []
        actions: list[ActionCompleted] = []
        streaks: list[int] = []
        errors: list[ErrorOccurred] = []
        idle = asyncio.Event()

        async def on_perception(event: PerceptionResult) -> None:
            perceptions.append(event)
            order.append(f"timeout_{len(perceptions)}")

        async def on_action(event: ActionCompleted) -> None:
            actions.append(event)
            order.append("retry_speak_complete" if event.kind == "speak" else "rest_complete")

        async def on_state(event: StateChanged) -> None:
            states.append(event.new)
            if event.new == "ACTION":
                assert sm._session is not None and sm._session.llm_response is not None
                responses.append(asdict(sm._session.llm_response))
                streaks.append(sm._session.no_input_streak)
            elif event.new == "IDLE":
                order.append("idle")
                idle.set()

        async def on_error(event: ErrorOccurred) -> None:
            errors.append(event)
            idle.set()

        bus.subscribe(PerceptionResult, on_perception, name="m4c.s03.perception")
        bus.subscribe(ActionCompleted, on_action, name="m4c.s03.action")
        bus.subscribe(StateChanged, on_state, name="m4c.s03.state")
        bus.subscribe(ErrorOccurred, on_error, name="m4c.s03.error")
        await display.start()
        await session_display.start()
        await speak.start()
        await sm.start()
        sm.set_conversation_lifecycle(conversation)
        await bus.publish(ButtonPressed("conversation", 1))
        await asyncio.wait_for(idle.wait(), 2)
        await asyncio.wait_for(sm._inbox.join(), 2)

        assert not errors
        assert states == [
            "WAKE", "PERCEPTION", "ACTION", "PERCEPTION", "ACTION", "IDLE",
        ]
        state_hint = dict(display.snapshot().status_slots).get("state")
        # The portable fixture does not start StatusBar; IDLE and empty Main are
        # the directly relevant SessionDisplay observations here.
        assert state_hint is None
        evidence = {
            "schema_version": 1,
            "perceptions": [asdict(item) for item in perceptions],
            "responses": responses,
            "actions": [asdict(item) for item in actions],
            "no_input_streaks": streaks,
            "reasoner_call_count": reasoner.calls,
            "order": order,
            "playback": {"retry_play_count": len(audio.frames_played), "complete": True},
            "cleanup": {
                "state": sm.state,
                "status": "待命",
                "main_empty": display.snapshot().main is None,
            },
        }
        public = S03_ORACLE.validate_s03_private_evidence(evidence)
        assert public["timeout_count"] == 2
        assert tts.texts == [S03_ORACLE.RETRY_TEXT]
        assert conversation.closed is True
        assert sm._in_flight == {}
        assert sm._session is None
        await sm.stop()
        await speak.stop()
        await session_display.stop()
        await display.stop()

    asyncio.run(run())
