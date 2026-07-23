"""Perception layer contract."""

from __future__ import annotations

from typing import Protocol

from sbd.core.event_bus.events import PerceptionResult


class Perception(Protocol):
    """Turns physical-world input into internal text/data."""

    async def perceive(self) -> PerceptionResult: ...
