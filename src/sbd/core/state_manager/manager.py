"""StateManager (SM).

Subscribes to fact-report events, guards against illegal transitions,
publishes commands to workers and StateChanged for observers.

Transitions follow docs/arch.md §11.2.
"""

from __future__ import annotations

import asyncio
import logging

from sbd.core.config import StateManagerSettings
from sbd.core.event_bus import EventBus, events as ev
from sbd.core.state_manager.states import State

log = logging.getLogger(__name__)


class StateManager:
    def __init__(self, bus: EventBus, settings: StateManagerSettings) -> None:
        self._bus = bus
        self._settings = settings
        self._state = State.IDLE
        self._shutdown = asyncio.Event()

        bus.subscribe(ev.WakeDetected, self._on_wake_detected)
        bus.subscribe(ev.PerceptionResult, self._on_perception_result)
        bus.subscribe(ev.LLMResponse, self._on_llm_response)
        bus.subscribe(ev.ToolExecuted, self._on_tool_executed)
        bus.subscribe(ev.SpeechFinished, self._on_speech_finished)
        bus.subscribe(ev.InterruptRequested, self._on_interrupt)
        bus.subscribe(ev.ErrorOccurred, self._on_error)
        bus.subscribe(ev.ShutdownRequested, self._on_shutdown)

    @property
    def state(self) -> State:
        return self._state

    async def wait_until_shutdown(self) -> None:
        await self._shutdown.wait()

    # ─── Transition primitive ─────────────────────────────────────────────

    async def _transition(self, target: State) -> None:
        if target is self._state:
            return
        old, self._state = self._state, target
        log.info("state %s -> %s", old.value, target.value)
        await self._bus.publish(ev.StateChanged(old=old.value, new=target.value))

    def _reject(self, event_name: str) -> None:
        log.warning("%s ignored in state %s", event_name, self._state.value)

    # ─── Handlers ─────────────────────────────────────────────────────────

    async def _on_wake_detected(self, event: ev.WakeDetected) -> None:
        if self._state is not State.IDLE:
            self._reject("WakeDetected")
            return
        await self._transition(State.WAKE)
        kind = _perception_kind_for(event)
        await self._transition(State.PERCEPTION)
        await self._bus.publish(ev.StartPerception(kind=kind, payload=event.payload))

    async def _on_perception_result(self, event: ev.PerceptionResult) -> None:
        if self._state is not State.PERCEPTION:
            self._reject("PerceptionResult")
            return
        await self._transition(State.THINK)
        await self._bus.publish(ev.StartReasoning(input=event))

    async def _on_llm_response(self, event: ev.LLMResponse) -> None:
        if self._state is not State.THINK:
            self._reject("LLMResponse")
            return

        if event.tool_calls:
            for call in event.tool_calls:
                await self._bus.publish(ev.ExecuteTool(call=call))
            return

        if event.text:
            await self._transition(State.ACTION)
            await self._bus.publish(ev.SpeakRequested(text=event.text))
            return

        await self._finish_turn()

    async def _on_tool_executed(self, event: ev.ToolExecuted) -> None:
        if self._state is not State.THINK:
            self._reject("ToolExecuted")
            return
        # brain/reasoner re-invokes the LLM with the tool result;
        # SM simply stays in THINK awaiting the next LLMResponse.

    async def _on_speech_finished(self, event: ev.SpeechFinished) -> None:
        if self._state is not State.ACTION:
            self._reject("SpeechFinished")
            return
        await self._finish_turn()

    async def _on_interrupt(self, event: ev.InterruptRequested) -> None:
        if self._state is State.IDLE:
            self._reject("InterruptRequested")
            return
        await self._bus.publish(ev.StopSpeaking())
        await self._finish_turn()

    async def _on_error(self, event: ev.ErrorOccurred) -> None:
        log.error("error in %s: %r", event.where, event.error)
        await self._transition(State.ERROR)
        await asyncio.sleep(self._settings.error_recovery_seconds)
        await self._finish_turn()

    async def _on_shutdown(self, event: ev.ShutdownRequested) -> None:
        log.info("shutdown requested")
        self._shutdown.set()

    # ─── Turn completion ──────────────────────────────────────────────────

    async def _finish_turn(self) -> None:
        await self._transition(State.IDLE)
        await self._bus.publish(ev.TurnCompleted())


def _perception_kind_for(event: ev.WakeDetected) -> str:
    """Pick which perception to invoke based on the wake event.

    Rule (docs/arch.md §6.4): SM decides, not perception itself.
    """
    hint = event.payload.get("perception") if event.payload else None
    if isinstance(hint, str) and hint:
        return hint
    if event.source == "event" and "text" in (event.payload or {}):
        return "read"
    return "listen"
