"""Deterministic M2 button and wake-word InputSources."""

from __future__ import annotations

from sbd.core.event_bus import EventBus
from sbd.core.events import ButtonPressed, WakeWordDetected


class MockButtonInputSource:
    def __init__(self, *, bus: EventBus) -> None:
        self._bus = bus
        self._started = False
        self._armed = False

    async def start(self) -> None:
        self._started = True

    async def arm(self) -> None:
        if not self._started:
            raise RuntimeError("button source is not started")
        self._armed = True

    async def stop(self) -> None:
        self._armed = False
        self._started = False

    def is_available(self) -> bool:
        return self._started and self._armed

    async def emit(self, button_id: str = "conversation", duration_ms: int = 50) -> None:
        if not self.is_available():
            raise RuntimeError("button source is unavailable")
        await self._bus.publish(ButtonPressed(button_id, duration_ms))


class MockWakeWordInputSource:
    def __init__(self, *, bus: EventBus) -> None:
        self._bus = bus
        self._started = False
        self._armed = False
        self._suspended = False

    @property
    def control(self) -> "MockWakeWordInputSource":
        return self

    async def start(self) -> None:
        self._started = True

    async def arm(self) -> None:
        if not self._started:
            raise RuntimeError("wake source is not started")
        self._armed = True

    async def stop(self) -> None:
        self._armed = False
        self._started = False
        self._suspended = False

    def is_available(self) -> bool:
        return self._started and self._armed and not self._suspended

    async def suspend(self) -> None:
        self._suspended = True

    async def resume(self) -> None:
        if self._started:
            self._suspended = False

    async def ensure_released(self) -> None:
        self._suspended = True

    async def emit(self, phrase: str = "snowboard", confidence: float = 1.0) -> None:
        if not self.is_available():
            raise RuntimeError("wake source is unavailable")
        await self._bus.publish(WakeWordDetected(phrase, confidence))


__all__ = ["MockButtonInputSource", "MockWakeWordInputSource"]
