"""Host behaviour tests for the GPIO-backed conversation button."""

from __future__ import annotations

import asyncio

from sbd.core.config.models import ButtonInputConfig, GPIOPinConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import ButtonPressed, ShutdownRequested
from sbd.core.gpio.mock import MockGPIO
from sbd.input_events.button import ButtonInputSource


def test_button_source_short_long_thresholds_and_cleanup() -> None:
    async def scenario():
        bus, gpio = EventBus(), MockGPIO()
        seen = []
        async def record(event): seen.append(event)
        bus.subscribe(ButtonPressed, record)
        bus.subscribe(ShutdownRequested, record)
        source = ButtonInputSource(
            gpio=gpio, bus=bus,
            config=ButtonInputConfig(short_press_min_ms=50, long_press_min_ms=1500),
            pin_config=GPIOPinConfig(pin=5, debounce_ms=20),
        )
        await gpio.start(); await source.start(); await source.arm()
        await gpio.simulate_event(5, "rising", at=1.0)
        await gpio.simulate_event(5, "falling", at=1.01)
        await gpio.simulate_event(5, "rising", at=2.0)
        await gpio.simulate_event(5, "falling", at=2.1)
        await gpio.simulate_event(5, "rising", at=3.0)
        await gpio.simulate_event(5, "falling", at=4.5)
        await gpio.wait_callbacks()
        assert [(type(event).__name__, getattr(event, "duration_ms", None)) for event in seen] == [
            ("ButtonPressed", 100), ("ShutdownRequested", None),
        ]
        await source.stop(); await source.stop()
        assert not source.is_available()
        await gpio.stop()
    asyncio.run(scenario())
