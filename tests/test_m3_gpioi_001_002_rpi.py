"""M3 libgpiod target-device acceptance cards."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import replace

import pytest

from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.event_bus import EventBus
from sbd.core.gpio import make_gpio
from sbd.core.gpio.base import GPIOEvent
from sbd.core.gpio.gpiod.driver import GpiodGPIO
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager
from tests.rpi_support import interaction_timeout, record_result, rpi_config


pytestmark = pytest.mark.rpi


def _loopback_pins() -> tuple[int, int]:
    raw_output = os.environ.get("SBD_M3_GPIO_OUTPUT_PIN")
    raw_input = os.environ.get("SBD_M3_GPIO_INPUT_PIN")
    assert raw_output and raw_output.isdecimal()
    assert raw_input and raw_input.isdecimal()
    output, input_ = int(raw_output), int(raw_input)
    assert output != input_, "loopback output and input GPIOs must differ"
    return output, input_


def test_m3_gpioi_001() -> None:
    config = rpi_config("M3-GPIOI-001")
    assert config.core.gpio.driver == "gpiod"
    output_pin, input_pin = _loopback_pins()
    debounce_ms = max(20, config.core.gpio.pins[config.input_sources.button.conversation_pin].debounce_ms)

    async def scenario() -> list[GPIOEvent]:
        gpio = make_gpio(config.core.gpio)
        observed: asyncio.Queue[GPIOEvent] = asyncio.Queue()

        async def callback(event: GPIOEvent) -> None:
            observed.put_nowait(event)

        await gpio.start()
        try:
            await gpio.configure_output(output_pin, initial=False)
            await gpio.register_input(input_pin, "both", callback, debounce_ms=debounce_ms)

            await gpio.set_output(output_pin, True)
            first = await asyncio.wait_for(observed.get(), timeout=interaction_timeout())
            await gpio.set_output(output_pin, False)  # deliberately inside debounce window
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(observed.get(), timeout=debounce_ms / 1000)

            falling = await asyncio.wait_for(observed.get(), timeout=interaction_timeout())
            assert falling.pin == input_pin and falling.edge == "falling"

            await asyncio.sleep(debounce_ms / 1000 + 0.02)
            await gpio.set_output(output_pin, True)
            second = await asyncio.wait_for(observed.get(), timeout=interaction_timeout())
            assert first.pin == second.pin == input_pin
            assert first.edge == second.edge == "rising"
            assert first.at <= falling.at <= second.at

            await gpio.unregister(input_pin)
            await gpio.unregister(input_pin)
            await gpio.set_output(output_pin, False)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(observed.get(), timeout=debounce_ms / 1000 + 0.05)
            await gpio.unregister(output_pin)
            await gpio.unregister(output_pin)
            return [first, falling, second]
        finally:
            await gpio.stop()

    events = asyncio.run(scenario())
    record_result(
        "M3-GPIOI-001",
        expected="loopback edge, kernel debounce, idempotent unregister, and output level all work",
        actual=f"events={[(event.edge, event.at) for event in events]}; fast edge suppressed",
        fixture={"name": f"BCM{output_pin}-to-BCM{input_pin} loopback", "sha256": "physical-fixture"},
        operation="Install the documented loopback jumper before running the card",
    )


def test_m3_gpioi_002(monkeypatch, caplog) -> None:
    config = rpi_config("M3-GPIOI-002")

    class MissingGpiod:
        @staticmethod
        def is_gpiochip_device(path: str) -> bool:
            return False

    failed_gpio = GpiodGPIO(config.core.gpio, gpiod_module=MissingGpiod())
    monkeypatch.setattr("sbd.core.m2_composition.make_gpio", lambda _: failed_gpio)
    isolated = replace(
        DEFAULT_CONFIG,
        core=replace(DEFAULT_CONFIG.core, gpio=config.core.gpio),
        input_sources=replace(
            DEFAULT_CONFIG.input_sources,
            button=config.input_sources.button,
        ),
    )

    async def scenario() -> None:
        bus = EventBus()
        rm = ResourceManager(isolated, bus)
        composition = M2Composition()
        composition(rm, bus, isolated)
        with caplog.at_level(logging.WARNING):
            await rm.start()
        gpio_record = rm._records["core.gpio"]
        input_record = rm._records["input.button"]
        assert gpio_record.started is False
        assert gpio_record.using_null is False
        assert ".null." not in type(gpio_record.instance).__module__
        assert rm.capability_of("gpio") is False
        assert input_record.started is False
        assert "configured GPIO chip is unavailable" in caplog.text
        assert rm._startup_complete is True
        report = await rm.stop_all()
        assert report.failures == ()

    asyncio.run(scenario())
    record_result(
        "M3-GPIOI-002",
        expected="GPIO start failure creates no NullGPIO, disables input, logs warning, app continues",
        actual="gpio=False; no NullGPIO; input.button not started; RM startup completed",
        fixture={"name": "deterministic unavailable-gpiochip module", "sha256": "inline-fixture"},
    )
