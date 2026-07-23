"""Full coverage of the transition table in docs/arch.md §11.2."""

from __future__ import annotations

from typing import Any

import pytest

from sbd.core.event_bus import EventBus, events as ev
from sbd.core.state_manager import State, StateManager


class Recorder:
    """Captures events published by SM so tests can inspect commands."""

    def __init__(self, bus: EventBus) -> None:
        self.events: list[Any] = []
        for cls in (
            ev.StartPerception,
            ev.StartReasoning,
            ev.ExecuteTool,
            ev.SpeakRequested,
            ev.StopSpeaking,
            ev.GoIdle,
            ev.StateChanged,
            ev.TurnCompleted,
        ):
            bus.subscribe(cls, self._make_handler())

    def _make_handler(self):
        async def handler(evt: Any) -> None:
            self.events.append(evt)
        return handler

    def of(self, cls: type) -> list[Any]:
        return [e for e in self.events if isinstance(e, cls)]

    def state_history(self) -> list[tuple[str, str]]:
        return [(e.old, e.new) for e in self.of(ev.StateChanged)]


@pytest.fixture
def rec(bus: EventBus) -> Recorder:
    return Recorder(bus)


# ─── IDLE ─────────────────────────────────────────────────────────────────

async def test_idle_wake_transitions_to_perception(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))

    assert sm.state is State.PERCEPTION
    assert rec.state_history() == [
        ("IDLE", "WAKE"),
        ("WAKE", "PERCEPTION"),
    ]
    assert rec.of(ev.StartPerception)[0].kind == "listen"


async def test_wake_with_text_payload_uses_read_perception(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="event", payload={"text": "hi"}))

    assert rec.of(ev.StartPerception)[0].kind == "read"


async def test_idle_ignores_unrelated_events(
    bus: EventBus, sm: StateManager, rec: Recorder, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        await bus.publish(ev.SpeechFinished())

    assert sm.state is State.IDLE
    assert not rec.state_history()


# ─── PERCEPTION ───────────────────────────────────────────────────────────

async def test_perception_result_transitions_to_think(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    result = ev.PerceptionResult(kind="listen", text="hello")
    await bus.publish(result)

    assert sm.state is State.THINK
    reasoning = rec.of(ev.StartReasoning)
    assert reasoning and reasoning[0].input is result


# ─── THINK ────────────────────────────────────────────────────────────────

async def test_llm_response_with_tool_calls_stays_in_think(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))

    call = ev.ToolCall(name="time", args={})
    await bus.publish(ev.LLMResponse(text="", tool_calls=[call]))

    assert sm.state is State.THINK
    execs = rec.of(ev.ExecuteTool)
    assert len(execs) == 1 and execs[0].call is call


async def test_tool_executed_keeps_state_in_think(
    bus: EventBus, sm: StateManager
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="", tool_calls=[ev.ToolCall(name="t", args={})]))
    await bus.publish(ev.ToolExecuted(name="t", result="ok"))

    assert sm.state is State.THINK


async def test_llm_response_with_text_transitions_to_action(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="answer"))

    assert sm.state is State.ACTION
    assert rec.of(ev.SpeakRequested)[0].text == "answer"


async def test_empty_llm_response_returns_to_idle(
    bus: EventBus, sm: StateManager
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="", tool_calls=[]))

    assert sm.state is State.IDLE


# ─── ACTION ───────────────────────────────────────────────────────────────

async def test_speech_finished_returns_to_idle_and_publishes_turn_completed(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="ok"))
    await bus.publish(ev.SpeechFinished())

    assert sm.state is State.IDLE
    assert rec.of(ev.TurnCompleted)


async def test_interrupt_during_action_stops_speaking_and_idles(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.PerceptionResult(kind="listen", text="hi"))
    await bus.publish(ev.LLMResponse(text="ok"))
    await bus.publish(ev.InterruptRequested())

    assert sm.state is State.IDLE
    assert rec.of(ev.StopSpeaking)


# ─── GUARDS ───────────────────────────────────────────────────────────────

async def test_wake_ignored_when_not_idle(
    bus: EventBus, sm: StateManager, caplog: pytest.LogCaptureFixture
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    assert sm.state is State.PERCEPTION

    with caplog.at_level("WARNING"):
        await bus.publish(ev.WakeDetected(source="button"))

    assert sm.state is State.PERCEPTION
    assert any("WakeDetected ignored" in rec.message for rec in caplog.records)


async def test_interrupt_ignored_when_idle(
    bus: EventBus, sm: StateManager, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        await bus.publish(ev.InterruptRequested())

    assert sm.state is State.IDLE


# ─── ERROR ────────────────────────────────────────────────────────────────

async def test_error_transitions_through_error_state_back_to_idle(
    bus: EventBus, sm: StateManager, rec: Recorder
) -> None:
    await bus.publish(ev.WakeDetected(source="button"))
    await bus.publish(ev.ErrorOccurred(where="test", error=RuntimeError("boom")))

    assert sm.state is State.IDLE
    history = rec.state_history()
    assert ("PERCEPTION", "ERROR") in history
    assert ("ERROR", "IDLE") in history


# ─── SHUTDOWN ─────────────────────────────────────────────────────────────

async def test_shutdown_sets_shutdown_flag(
    bus: EventBus, sm: StateManager
) -> None:
    await bus.publish(ev.ShutdownRequested())

    # wait_until_shutdown should now be resolved
    import asyncio
    await asyncio.wait_for(sm.wait_until_shutdown(), timeout=0.1)
