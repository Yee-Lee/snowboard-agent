"""State projection owner for the selected display profile."""

from __future__ import annotations

from sbd.core.events import StateChanged
from sbd.core.event_bus import EventBus
from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint


class StatusBar:
    def __init__(self, arbiter: DisplayArbiter, bus: EventBus) -> None:
        self._arbiter = arbiter
        self._bus = bus
        self._subscription = None

    async def start(self) -> None:
        self._arbiter.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
        self._subscription = self._bus.subscribe(
            StateChanged, self._on_state_changed, name="observer.status_bar.state"
        )

    async def stop(self) -> None:
        if self._subscription is not None:
            self._bus.unsubscribe(self._subscription)
            self._subscription = None

    async def _on_state_changed(self, event: StateChanged) -> None:
        self._arbiter.write_status_slot(
            "state", DisplayHint("status.state", {"state": event.new})
        )
