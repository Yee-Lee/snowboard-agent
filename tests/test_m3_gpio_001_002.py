"""M3 portable MockGPIO tests."""

from __future__ import annotations

import asyncio

import pytest

from sbd.core.gpio.mock import MockGPIO


def test_m3_gpio_001() -> None:
    async def scenario():
        gpio, events = MockGPIO(), []
        async def good(event): events.append(event)
        async def bad(event): raise RuntimeError("isolated")
        await gpio.start()
        await gpio.register_input(5, "both", good, debounce_ms=50)
        with pytest.raises(ValueError):
            await gpio.register_input(5, "rising", good)
        await gpio.register_input(6, "rising", bad)
        assert await gpio.simulate_event(5, "rising", at=1.0)
        assert not await gpio.simulate_event(5, "falling", at=1.01)
        assert await gpio.simulate_event(6, "rising", at=1.0)
        assert await gpio.simulate_event(5, "falling", at=1.06)
        await gpio.wait_callbacks()
        assert [(event.pin, event.edge) for event in events] == [(5, "rising"), (5, "falling")]
        await gpio.unregister(50)
        await gpio.stop()
    asyncio.run(scenario())


def test_m3_gpio_002() -> None:
    async def scenario():
        gpio = MockGPIO()
        await gpio.configure_output(10, initial=False)
        assert gpio.output_value(10) is False
        await gpio.set_output(10, True)
        assert gpio.output_value(10) is True
        with pytest.raises(ValueError):
            await gpio.configure_output(10)
        with pytest.raises(ValueError):
            await gpio.set_output(20, True)
    asyncio.run(scenario())
