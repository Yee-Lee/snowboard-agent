"""M3 physical conversation-button acceptance cards."""

from __future__ import annotations

import asyncio

import pytest

from sbd.core.event_bus import EventBus
from sbd.core.events import ButtonPressed, ShutdownRequested
from sbd.core.gpio import make_gpio
from sbd.input_events.button import ButtonInputSource
from tests.rpi_support import interaction_timeout, record_result, require_manual, rpi_config


pytestmark = pytest.mark.rpi


async def _button_event(expected):
    config = rpi_config()
    pin = config.core.gpio.pins[config.input_sources.button.conversation_pin]
    bus = EventBus()
    received: asyncio.Queue = asyncio.Queue()

    async def observe(event) -> None:
        await received.put(event)

    bus.subscribe(expected, observe, name="m3_rpi_button_observer")
    gpio = make_gpio(config.core.gpio)
    source = ButtonInputSource(gpio=gpio, bus=bus, config=config.input_sources.button, pin_config=pin)
    await gpio.start()
    await source.start()
    await source.arm()
    try:
        event = await asyncio.wait_for(received.get(), timeout=interaction_timeout())
        return event
    finally:
        await source.stop()
        await gpio.stop()


def test_m3_btn_001() -> None:
    event = asyncio.run(_button_event(ButtonPressed))
    assert event.duration_ms > 0
    record_result("M3-BTN-001", signal="ButtonPressed", duration_ms=event.duration_ms)


def test_m3_btn_002() -> None:
    rpi_config()
    require_manual("M3-BTN-002")
    record_result("M3-BTN-002", manual="PASS", expected="InterruptRequested during active session")


def test_m3_btn_003() -> None:
    asyncio.run(_button_event(ShutdownRequested))
    record_result("M3-BTN-003", signal="ShutdownRequested")


def test_m3_btn_004() -> None:
    rpi_config()
    require_manual("M3-BTN-004")
    record_result("M3-BTN-004", manual="PASS", expected="ERROR short press starts new session")


def test_m3_btn_005() -> None:
    rpi_config()
    require_manual("M3-BTN-005")
    record_result("M3-BTN-005", manual="PASS", expected="recovery in-flight ignores short press")
