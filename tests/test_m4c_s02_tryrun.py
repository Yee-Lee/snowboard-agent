"""Workstation try-run for composite M4C-PI-S02/NORMAL_END_B2."""

from __future__ import annotations

import copy
from contextlib import asynccontextmanager
import asyncio
import hashlib
import importlib.util
from pathlib import Path
import time

import pytest

from sbd.action.rest import Rest
from sbd.action.speak import Speak
from sbd.action.speak.tts import MockTTSAdapter
from sbd.cognition.llm import AdmissionSnapshot, GenerationMetrics, SemanticGeneration
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.display import DisplayArbiter, DisplayHint
from sbd.core.display.session import SessionDisplay
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted,
    ButtonPressed,
    ErrorOccurred,
    LLMResponse,
    PerceptionResult,
    StateChanged,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager import StateManager
from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
from tests.test_m2_wrk_003 import _validator


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m4c_s02_oracle", ROOT / "scripts/m4c_s02_oracle.py"
)
assert SPEC is not None and SPEC.loader is not None
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def _valid_evidence() -> dict:
    keys = ORACLE.TIMELINE_KEYS
    timeline = {key: (index + 1) * 100_000_000 for index, key in enumerate(keys)}
    return {
        "schema_version": 1,
        "streaming_path": "B2-ONE-LOOKAHEAD-COALESCE",
        "fragments": ["天空呈現藍色，", "主要是藍光散射較明顯。"],
        "terminal_text": "天空呈現藍色，主要是藍光散射較明顯。",
        "spoken_text": "天空呈現藍色，主要是藍光散射較明顯。",
        "display_text": "天空呈現藍色，主要是藍光散射較明顯。",
        "provisional_display_publications": 0,
        "timeline": timeline,
        "playback": {
            "admitted_fragment_count": 2,
            "played_fragment_count": 2,
            "play_call_count": 2,
            "drain_call_count": 2,
            "complete": True,
        },
        "turn2": {
            "end": True,
            "branch": "nonempty_play_then_rest",
            "answer_length": 5,
        },
        "cleanup": {
            "state": "IDLE",
            "status": "待命",
            "main_empty": True,
        },
    }


def test_s02_display_publication_contract_covers_both_end_branches() -> None:
    assert ORACLE.expected_display_publications("actual-asr-1", "a1", "actual-asr-2", "a2") == [
        ("WAKE", None),
        ("THINK", "actual-asr-1"),
        ("ACTION", "a1"),
        ("THINK", "actual-asr-2"),
        ("ACTION", "a2"),
        ("IDLE", None),
    ]
    assert ORACLE.expected_display_publications("actual-asr-1", "a1", "actual-asr-2", "") == [
        ("WAKE", None),
        ("THINK", "actual-asr-1"),
        ("ACTION", "a1"),
        ("THINK", "actual-asr-2"),
        ("IDLE", None),
    ]


def test_s02_oracle_accepts_atomic_composite_and_projects_no_private_text() -> None:
    public = ORACLE.validate_s02_private_evidence(_valid_evidence())
    assert public["scenario_code"] == "M4C-PI-S02/NORMAL_END_B2"
    assert public["fragment_count"] == 2
    assert public["answer_matches_spoken"] is True
    assert public["answer_matches_display"] is True
    rendered = repr(public)
    assert "天空呈現藍色" not in rendered
    assert "請結束對話" not in rendered


def test_s02_oracle_does_not_gate_on_asr_text() -> None:
    value = _valid_evidence()
    ORACLE.validate_s02_private_evidence(value)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(fragments=[]), "M4C_S02_ELIGIBLE_FRAGMENT_MISSING"),
        (lambda value: value.update(spoken_text="不同"), "M4C_S02_ANSWER_MISMATCH"),
        (
            lambda value: value.update(provisional_display_publications=1),
            "M4C_S02_PROVISIONAL_DISPLAY_LEAK",
        ),
        (
            lambda value: value["timeline"].update(llm_terminal=950_000_000),
            "M4C_S02_TIMELINE_ORDER_INVALID",
        ),
        (
            lambda value: value["timeline"].update(llm_terminal=700_000_000),
            "M4C_S02_FIRST_WRITE_NOT_PRETERMINAL",
        ),
        (
            lambda value: value["playback"].update(drain_call_count=1),
            "M4C_S02_PLAYBACK_DRAIN_INCOMPLETE",
        ),
        (lambda value: value["cleanup"].update(state="ACTION"),
         "M4C_S02_FINAL_STATE_INVALID"),
    ],
)
def test_s02_oracle_fails_closed_for_unstitchable_evidence(mutation, code) -> None:
    value = copy.deepcopy(_valid_evidence())
    mutation(value)
    with pytest.raises(ORACLE.S02OracleError, match=code):
        ORACLE.validate_s02_private_evidence(value)


class _Renderer:
    def validate(self, hint: DisplayHint) -> None:
        assert hint.template in {"status.state", "main.text"}

    def render(self, *, size, model) -> bytes:
        return bytes(size[0] * size[1] * 2)


class _Display:
    def __init__(self) -> None:
        self._size = (128, 128)

    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    def clear(self) -> None: pass
    def write_pixels(self, value: bytes) -> None:
        assert len(value) == 128 * 128 * 2
    def show(self) -> None: pass
    def size(self): return self._size


class _Listen:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._values = iter(("天空為什麼是藍色的？", "請結束對話。"))

    async def perceive(self, session_id, turn_id, correlation_id, timeout_seconds):
        del timeout_seconds
        await self._bus.publish(PerceptionResult(
            "listen", "ok", next(self._values), {}, session_id, turn_id, correlation_id
        ))

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


class _ProductLLM:
    supports_safe_text_callback = True

    def __init__(self) -> None:
        self.control = self
        self.conversation_revision = 0
        self.session_id: str | None = None
        self.closed = False
        self.close_reason: str | None = None
        self.generated: list[str] = []

    @asynccontextmanager
    async def serialized(self):
        yield

    def assert_conversation(self, session_id, generation):
        assert (session_id, generation) == (self.session_id, 1)

    async def open_conversation(self, session_id, generation):
        assert generation == 1
        self.session_id = session_id
        return ConversationReady(session_id, generation)

    async def close_conversation(self, session_id, generation, reason):
        assert (session_id, generation) == (self.session_id, 1)
        assert type(reason) is str and reason
        self.closed = True
        self.close_reason = reason
        return ConversationCloseProof(session_id, generation, True, True, True)

    async def measure(self, session_id, generation, text):
        return AdmissionSnapshot(
            "a" * 32, session_id, generation, hashlib.sha256(text.encode()).hexdigest(),
            1, 0, 80, 80, 128, 1024,
        )

    async def generate(self, snapshot, text, on_safe_text=None):
        del snapshot
        self.generated.append(text)
        if text == "天空為什麼是藍色的?":
            fragments = ("因為藍光容易散射,", "所以天空看起來是藍色的。")
            terminal, end = "".join(fragments), False
            assert on_safe_text is not None
            for sequence, fragment in enumerate(fragments):
                await on_safe_text(sequence, fragment)
        else:
            fragments = ("好的,再見。",)
            terminal, end = fragments[0], True
            assert on_safe_text is not None
            await on_safe_text(0, fragments[0])
        self.conversation_revision += 1
        now = time.monotonic_ns()
        return SemanticGeneration(
            terminal, end, fragments,
            GenerationMetrics(1, 0, 80, 80, 1, 81, now, now + 1, now + 2),
        )

    async def abort(self) -> None: pass
    async def force_abort(self) -> ForceAbortReport: return ForceAbortReport()


def test_s02_product_integration_uses_real_state_reasoner_streaming_and_display() -> None:
    async def run() -> None:
        bus = EventBus()
        llm = _ProductLLM()
        tts = MockTTSAdapter()
        audio = MockAudioOutput()
        speak = Speak(tts=tts, audio_output=audio, bus=bus)
        reasoner = Reasoner(
            llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
            _validator(), control=llm, streaming_speak=speak,
        )
        listen = _Listen(bus)
        rest = Rest(bus=bus)
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("speak", speak)
        catalog.register_action("rest", rest)
        catalog.seal()
        sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=0.001)

        display = DisplayArbiter(_Display(), _Renderer())
        await display.start()
        display_history: list[tuple[str, str | None]] = []
        states: list[str] = []
        responses: list[LLMResponse] = []
        actions: list[ActionCompleted] = []
        errors: list[ErrorOccurred] = []
        idle = asyncio.Event()

        async def on_response(event: LLMResponse) -> None:
            responses.append(event)

        async def on_action(event: ActionCompleted) -> None:
            actions.append(event)

        async def on_state(event: StateChanged) -> None:
            states.append(event.new)
            display.write_status_slot("state", DisplayHint("status.state", {"state": event.new}))
            main = display.snapshot().main
            display_history.append((
                event.new,
                None if main is None else main.data["text"],
            ))
            if event.new == "IDLE":
                idle.set()

        session_display = SessionDisplay(display, bus, sm)
        await session_display.start()
        bus.subscribe(LLMResponse, on_response, name="m4c.s02.display.response")
        bus.subscribe(ActionCompleted, on_action, name="m4c.s02.display.action")
        bus.subscribe(StateChanged, on_state, name="m4c.s02.display.state")
        async def on_error(event: ErrorOccurred) -> None: errors.append(event)
        bus.subscribe(ErrorOccurred, on_error, name="m4c.s02.errors")
        await sm.start()
        sm.set_conversation_lifecycle(llm)
        await bus.publish(ButtonPressed("conversation", 1))
        try:
            await asyncio.wait_for(idle.wait(), 2)
        except TimeoutError:
            pytest.fail(f"S02 did not converge: errors={errors!r} generated={llm.generated!r}")
        await asyncio.wait_for(sm._inbox.join(), 2)

        assert llm.generated == ["天空為什麼是藍色的?", "請結束對話。"]
        assert llm.closed is True
        assert [response.post_action_route for response in responses] == [
            "KEEP_NEXT", "END_SESSION"
        ]
        assert [action.kind for action in actions] == ["speak", "speak", "rest"]
        assert all(action.status == "ok" for action in actions)
        assert states == [
            "WAKE", "PERCEPTION", "THINK", "ACTION",
            "PERCEPTION", "THINK", "ACTION", "IDLE",
        ]
        terminal_answers = [response.action_payload["text"] for response in responses]
        assert display_history == [
            ("WAKE", None),
            ("PERCEPTION", None),
            ("THINK", "天空為什麼是藍色的？"),
            ("ACTION", terminal_answers[0]),
            ("PERCEPTION", terminal_answers[0]),
            ("THINK", "請結束對話。"),
            ("ACTION", terminal_answers[1]),
            ("IDLE", None),
        ]
        assert len(audio.frames_played) == 2
        assert len(speak._streaming_history) == 2
        assert len(speak._streaming_completion_history) == 2
        assert speak._streaming_completion_history == sorted(
            speak._streaming_completion_history
        )
        assert speak._streaming_history[0][1] == (
            "因為藍光容易散射,", "所以天空看起來是藍色的。"
        )
        assert sm._session is None and sm._in_flight == {}
        assert display.snapshot().main is None

        await sm.stop()
        await session_display.stop()
        await display.stop()

    asyncio.run(run())


def test_composed_reasoner_does_not_duplicate_backend_lifecycle() -> None:
    async def run() -> None:
        bus = EventBus()
        llm = _ProductLLM()
        reasoner = Reasoner(
            llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
            _validator(), control=llm, owns_llm_lifecycle=False,
        )
        # _ProductLLM deliberately has no start()/stop(); the ResourceManager's
        # backend resource owns those calls in the product composition.
        await reasoner.start()
        await reasoner.stop()

    asyncio.run(run())
