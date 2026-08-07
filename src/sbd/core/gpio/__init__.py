"""Lazy GPIO HAL factory (GPIO intentionally has no null backend)."""

from sbd.core.gpio.base import GPIO, GPIOEvent


def make_gpio(config) -> GPIO:
    if config.driver == "mock":
        from sbd.core.gpio.mock.driver import MockGPIO
        return MockGPIO()
    if config.driver == "gpiod":
        from sbd.core.gpio.gpiod.driver import GpiodGPIO
        return GpiodGPIO(config)
    if config.driver == "null":
        raise ValueError("GPIO does not provide a null backend")
    raise ValueError(f"unknown GPIO driver: {config.driver}")


__all__ = ["GPIO", "GPIOEvent", "make_gpio"]
