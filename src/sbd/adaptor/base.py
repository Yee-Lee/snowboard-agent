"""Adaptor layer contract.

Adaptors project internal state onto the physical world (display/leds)
or bridge external channels bidirectionally (external_broker).
"""

from __future__ import annotations

from typing import Protocol

from sbd.core.event_bus import EventBus


class Adaptor(Protocol):
    async def start(self, bus: EventBus) -> None: ...
    async def stop(self) -> None: ...
