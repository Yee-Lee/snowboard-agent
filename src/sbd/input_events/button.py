"""GPIO-backed conversation button InputSource."""

from __future__ import annotations

import asyncio

from sbd.core.config.models import ButtonInputConfig, GPIOPinConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import ButtonPressed, ShutdownRequested
from sbd.core.gpio.base import GPIO, GPIOEvent


class ButtonInputSource:
    def __init__(
        self, *, gpio: GPIO, bus: EventBus, config: ButtonInputConfig,
        pin_config: GPIOPinConfig,
    ) -> None:
        self._gpio = gpio
        self._bus = bus
        self._config = config
        self._pin_config = pin_config
        self._pressed_at: float | None = None
        self._started = False
        self._armed = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._started:
            return
        await self._gpio.register_input(
            self._pin_config.pin, "both", self._on_gpio_event,
            debounce_ms=self._pin_config.debounce_ms,
        )
        self._started = True

    async def arm(self) -> None:
        if not self._started:
            raise RuntimeError("button source is not started")
        self._armed = True

    async def stop(self) -> None:
        self._armed = False
        self._pressed_at = None
        if self._started:
            await self._gpio.unregister(self._pin_config.pin)
        self._started = False

    def is_available(self) -> bool:
        return self._started and self._armed

    async def _on_gpio_event(self, event: GPIOEvent) -> None:
        if not self.is_available():
            return
        press_edge = "falling" if self._pin_config.active_low else "rising"
        async with self._lock:
            if event.edge == press_edge:
                self._pressed_at = event.at
                return
            pressed_at, self._pressed_at = self._pressed_at, None
            if pressed_at is None or event.at < pressed_at:
                return
            duration_ms = int(round((event.at - pressed_at) * 1000))
            if duration_ms >= self._config.long_press_min_ms:
                await self._bus.publish(ShutdownRequested())
            elif duration_ms >= self._config.short_press_min_ms:
                await self._bus.publish(
                    ButtonPressed(self._config.conversation_pin, duration_ms)
                )
