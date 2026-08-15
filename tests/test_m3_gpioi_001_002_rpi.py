"""M3 libgpiod target-device acceptance cards."""

from __future__ import annotations

import asyncio
import os

import pytest

from sbd.core.gpio import make_gpio
from sbd.core.gpio.base import GPIOEvent
from tests.rpi_support import interaction_timeout, record_result, require_manual, rpi_config


pytestmark = pytest.mark.rpi


def test_m3_gpioi_001() -> None:
    config = rpi_config()
    assert config.core.gpio.driver == "gpiod"
    button = config.core.gpio.pins[config.input_sources.button.conversation_pin]

    async def scenario() -> GPIOEvent:
        gpio = make_gpio(config.core.gpio)
        observed: asyncio.Queue[GPIOEvent] = asyncio.Queue()

        async def callback(event: GPIOEvent) -> None:
            await observed.put(event)

        await gpio.start()
        try:
            await gpio.register_input(button.pin, "both", callback, debounce_ms=button.debounce_ms)
            return await asyncio.wait_for(observed.get(), timeout=interaction_timeout())
        finally:
            await gpio.stop()
    event = asyncio.run(scenario())
    assert event.pin == button.pin
    assert event.edge in {"rising", "falling"}
    record_result("M3-GPIOI-001", pin=event.pin, edge=event.edge, timestamp=event.at)


def test_m3_gpioi_002() -> None:
    config = rpi_config()
    raw_pin = os.environ.get("SBD_M3_GPIO_OUTPUT_PIN")
    assert raw_pin is not None and raw_pin.isdecimal(), "SBD_M3_GPIO_OUTPUT_PIN must name the safe test output BCM pin"
    pin = int(raw_pin)

    async def scenario() -> None:
        gpio = make_gpio(config.core.gpio)
        await gpio.start()
        try:
            await gpio.configure_output(pin, initial=False)
            await gpio.set_output(pin, True)
            require_manual("M3-GPIOI-002")
            await gpio.set_output(pin, False)
        finally:
            await gpio.stop()
    asyncio.run(scenario())
    record_result("M3-GPIOI-002", pin=pin, manual="PASS")
