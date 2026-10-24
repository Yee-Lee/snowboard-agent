"""M4C-SS-OUTCOME-001 — streaming/terminal outcome mapping."""
from __future__ import annotations

import asyncio
import hashlib

import pytest

from sbd.action.speak import Speak
from sbd.action.speak.tts import MockTTSAdapter
from sbd.cognition.llm import (
    GenerationMetrics, LLMBackendError, LLMCleanupUnprovenError, LLMProtocolError,
    ReplaceableGenerationFailure, SemanticGeneration,
)
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import LLMComponentSystemFault, Reasoner
from sbd.cognition.semantic import SemanticError
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.events import ActionCompleted, ErrorOccurred, LLMResponse
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from tests.test_m2_wrk_003 import _validator
from tests.test_m4b_outcome_001 import ProductLLM, fact
from sbd.core.event_bus import EventBus


METRICS = GenerationMetrics(1, 0, 80, 80, 1, 81, 1, 2, 3)


class StreamingLLM(ProductLLM):
    supports_safe_text_callback = True

    def __init__(self, result, emitted=()):
        super().__init__(result=result)
        self.emitted = tuple(emitted)

    async def generate(self, snapshot, text, on_safe_text=None):
        for sequence, fragment in enumerate(self.emitted):
            assert on_safe_text is not None
            await on_safe_text(sequence, fragment)
        return await super().generate(snapshot, text)


def _system(result, emitted=()):
    bus = EventBus()
    responses: list[LLMResponse] = []
    errors: list[ErrorOccurred] = []
    actions: list[ActionCompleted] = []
    async def capture_response(value): responses.append(value)
    async def capture_error(value): errors.append(value)
    async def capture_action(value): actions.append(value)
    bus.subscribe(LLMResponse, capture_response)
    bus.subscribe(ErrorOccurred, capture_error)
    bus.subscribe(ActionCompleted, capture_action)
    tts = MockTTSAdapter()
    audio = MockAudioOutput()
    speak = Speak(tts=tts, audio_output=audio, bus=bus)
    llm = StreamingLLM(result, emitted)
    reasoner = Reasoner(
        llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
        _validator(), streaming_speak=speak)
    return reasoner, speak, llm, responses, errors, actions, audio


def test_m4c_ss_outcome_001_o01_zero_fragment_replaceable_keeps_r2() -> None:
    async def run():
        reasoner, speak, _, responses, errors, actions, _ = _system(
            ReplaceableGenerationFailure("GENERATION_REJECTED"))
        await reasoner.reason("session", 1, 1, (fact(),), (), conversation_generation=1)
        assert errors == []
        assert len(responses) == 1
        response = responses[0]
        assert response.post_action_route == "REPLACE_NEXT"
        await speak.execute("session", 1, 2, response.action_payload)
        assert len(actions) == 1 and actions[0].status == "ok"
    asyncio.run(run())


def test_m4c_ss_outcome_001_o02_partial_fragment_terminal_failure() -> None:
    async def run():
        reasoner, speak, _, responses, errors, actions, _ = _system(
            ReplaceableGenerationFailure("GENERATION_REJECTED"), ("部分",))
        with pytest.raises(LLMComponentSystemFault):
            await reasoner.reason("session", 1, 1, (fact(),), (), conversation_generation=1)
        assert responses == [] and actions == []
        assert len(errors) == 1
        assert errors[0].code == "STREAMING_TERMINAL_FAILED"
        assert errors[0].backend_disposition == "reusable"
        assert errors[0].recovery_keys == ()
        assert speak._streaming is None
    asyncio.run(run())


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (LLMCleanupUnprovenError("proof"), "LLM_CLEANUP_UNPROVEN"),
        (LLMProtocolError("wire"), "LLM_PROTOCOL_FAILED"),
    ],
)
def test_m4c_ss_outcome_001_o03_o04_unproven_and_protocol(failure, code) -> None:
    async def run():
        reasoner, speak, _, responses, errors, actions, _ = _system(
            failure, ("部分",))
        with pytest.raises(LLMComponentSystemFault):
            await reasoner.reason("session", 1, 1, (fact(),), (), conversation_generation=1)
        assert responses == [] and actions == []
        assert len(errors) == 1 and errors[0].code == code
        assert errors[0].backend_disposition == "unproven"
        assert errors[0].recovery_keys == ("backend.cognition.reasoner.llm",)
        assert speak._streaming is None
    asyncio.run(run())


def test_m4c_ss_outcome_001_o06_terminal_only_b2_path() -> None:
    async def run():
        result = SemanticGeneration("完整回答。", False, (), METRICS)
        reasoner, speak, _, responses, errors, actions, audio = _system(result)
        await reasoner.reason("session", 1, 1, (fact(),), (), conversation_generation=1)
        assert errors == [] and len(responses) == 1
        await speak.execute("session", 1, 2, responses[0].action_payload)
        assert len(actions) == 1
        assert len(audio.frames_played) == 1
        assert speak._streaming is None
    asyncio.run(run())


def test_m4c_ss_outcome_001_o07_child_partial_invalid_terminal_is_replaceable() -> None:
    from sbd.cognition.litert_lm.worker import WorkerSession

    class Runtime:
        @staticmethod
        def open_conversation() -> None:
            pass

        @staticmethod
        def measure(text):
            return {"user_tokens": 1, "current_kv_tokens": 0,
                    "rendered_incremental_tokens": 1, "runtime_prefill_tokens": 1,
                    "output_reserve_tokens": 128, "engine_context_tokens": 1024}

        @staticmethod
        def generate_stream(text, emit):
            emit("可播放，")
            raise SemanticError()

    session = WorkerSession(Runtime())
    common = {"protocol": 3, "session_id": "session", "generation": 1}
    opened = {**common, "op": "OPEN", "request_id": 1}
    session.ledger.command(opened)
    session.ledger.event(session.execute(opened)[0])
    text = "測試"
    measured = {**common, "op": "MEASURE", "request_id": 2, "text": text,
                "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "output_reserve_tokens": 128}
    session.ledger.command(measured)
    session.ledger.event(session.execute(measured)[0])
    ticket = session.ledger.ticket
    assert ticket is not None
    generated = {**common, "op": "GENERATE", "request_id": 3, "text": text,
                 "input_sha256": measured["input_sha256"],
                 "conversation_revision": 0, "ticket": ticket["ticket"]}
    session.ledger.command(generated)
    safe: list[tuple[int, str, int]] = []
    result = session.execute(
        generated, lambda sequence, fragment, instant: safe.append(
            (sequence, fragment, instant)
        )
    )
    assert safe[0][0:2] == (0, "可播放，")
    assert result[0]["event"] == "REQUEST_FAILED"
    assert result[0]["code"] == "INVALID_SEMANTIC"
    assert result[0]["request_terminal_proven"] is True
    assert result[0]["engine_usable"] is True


def test_m4c_ss_outcome_001_o08_partial_llm_fault_cleans_streaming() -> None:
    async def run() -> None:
        reasoner, speak, _, responses, errors, actions, audio = _system(
            LLMBackendError("backend"), ("部分回答，",)
        )

        with pytest.raises(LLMComponentSystemFault):
            await reasoner.reason(
                "session", 1, 1, (fact(),), (), conversation_generation=1
            )

        played = tuple(audio.frames_played)
        await asyncio.sleep(0)
        assert responses == []
        assert actions == []
        assert len(errors) == 1
        assert errors[0].code == "LLM_BACKEND_FAILED"
        assert errors[0].backend_disposition == "rebuild_required"
        assert errors[0].recovery_keys == ("backend.cognition.reasoner.llm",)
        assert speak._streaming is None
        assert tuple(audio.frames_played) == played

    asyncio.run(run())


def test_m4c_ss_outcome_001_o09_tts_fault_clears_streaming_without_success() -> None:
    async def run() -> None:
        bus = EventBus()
        errors: list[ErrorOccurred] = []
        actions: list[ActionCompleted] = []

        async def capture_error(event: ErrorOccurred) -> None:
            errors.append(event)

        async def capture_action(event: ActionCompleted) -> None:
            actions.append(event)

        bus.subscribe(ErrorOccurred, capture_error, name="m4c.s06.tts.error")
        bus.subscribe(ActionCompleted, capture_action, name="m4c.s06.tts.action")
        fault = ComponentSystemFault.create(
            where="action.speak.tts",
            code="TTS_PROTOCOL_FAILED",
            backend=BackendDisposition.REBUILD_REQUIRED,
            recovery_keys=("backend.action.speak.tts",),
        )
        tts = MockTTSAdapter(error=fault)
        audio = MockAudioOutput()
        speak = Speak(tts=tts, audio_output=audio, bus=bus)
        control = speak.begin_streaming("session", 1, "operation")
        await control.feed("session", 1, 0, "第一段，")
        await control.feed("session", 1, 1, "第二段。")

        await asyncio.wait_for(tts.entered.wait(), 1)
        with pytest.raises(ComponentSystemFault):
            await control.wait()

        assert len(errors) == 1
        assert errors[0].code == "TTS_PROTOCOL_FAILED"
        assert errors[0].backend_disposition == "rebuild_required"
        assert errors[0].recovery_keys == ("backend.action.speak.tts",)
        assert actions == []
        assert audio.frames_played == []
        assert control.state == "FAILED"
        assert control.queue_depth == 0
        assert control.pending_utf8_bytes == 0
        assert control._inflight == ()
        assert control._pcm is None
        speak.release_streaming(control)
        assert speak._streaming is None

    asyncio.run(run())
