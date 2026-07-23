"""Wake layer contract."""

from __future__ import annotations

from typing import Protocol

from sbd.core.event_bus import EventBus


class WakeTrigger(Protocol):
    """A resident async task that publishes WakeDetected when triggered."""

    async def start(self, bus: EventBus) -> None: ...
    async def stop(self) -> None: ...
