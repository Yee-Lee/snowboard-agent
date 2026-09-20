"""State projection owner for the selected display profile."""

from __future__ import annotations

from sbd.core.events import ErrorOccurred, StateChanged
from sbd.core.faults import safe_category_for_code
from sbd.core.event_bus import EventBus
from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint


class StatusBar:
    def __init__(self, arbiter: DisplayArbiter, bus: EventBus) -> None:
        self._arbiter = arbiter
        self._bus = bus
        self._subscriptions = []

    async def start(self) -> None:
        self._arbiter.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
        self._subscriptions = [
            self._bus.subscribe(
                StateChanged, self._on_state_changed, name="observer.status_bar.state"
            ),
            self._bus.subscribe(
                ErrorOccurred, self._on_error, name="observer.status_bar.error"
            ),
        ]

    async def stop(self) -> None:
        for subscription in self._subscriptions:
            self._bus.unsubscribe(subscription)
        self._subscriptions.clear()

    async def _on_state_changed(self, event: StateChanged) -> None:
        self._arbiter.write_status_slot(
            "state", DisplayHint("status.state", {"state": event.new})
        )

    async def _on_error(self, event: ErrorOccurred) -> None:
        self._arbiter.write_status_slot(
            "error",
            DisplayHint(
                "status.error",
                {"category": safe_category_for_code(event.code)},
            ),
        )
