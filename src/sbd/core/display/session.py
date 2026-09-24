"""Projection of State-Manager-accepted session content into Display Main."""

from __future__ import annotations

from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint
from sbd.core.event_bus import EventBus
from sbd.core.events import StateChanged


class SessionDisplay:
    """Render only facts already accepted into the active State Manager session."""

    def __init__(self, arbiter: DisplayArbiter, bus: EventBus, state_manager) -> None:
        self._arbiter = arbiter
        self._bus = bus
        self._state_manager = state_manager
        self._subscription = None

    async def start(self) -> None:
        self._arbiter.write_main(None)
        self._subscription = self._bus.subscribe(
            StateChanged, self._on_state_changed, name="observer.session_display.state"
        )

    async def stop(self) -> None:
        if self._subscription is not None:
            self._bus.unsubscribe(self._subscription)
            self._subscription = None

    async def _on_state_changed(self, event: StateChanged) -> None:
        if event.new in {"IDLE", "WAKE"}:
            self._arbiter.write_main(None)
            return
        session = self._state_manager._session
        if session is None:
            return
        text = None
        if event.new == "THINK":
            for fact in reversed(session.perception_results):
                if fact.kind == "listen" and fact.status == "ok" and type(fact.text) is str:
                    candidate = fact.text.strip()
                    if candidate:
                        text = candidate
                        break
        elif event.new == "ACTION" and session.llm_response is not None:
            candidate = session.llm_response.action_payload.get("text")
            if type(candidate) is str and candidate.strip():
                text = candidate
        if text is not None:
            self._arbiter.write_main(DisplayHint("main.text", {"text": text}))


__all__ = ["SessionDisplay"]
