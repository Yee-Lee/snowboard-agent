"""Lazy display HAL factory."""

from sbd.core.display.base import DisplayDevice


def make_display(config) -> DisplayDevice:
    if config.driver == "null":
        from sbd.core.display.null.driver import NullDisplay
        return NullDisplay()
    if config.driver == "mock":
        from sbd.core.display.mock.driver import MockDisplay
        return MockDisplay(config)
    if config.driver in {"ssd1306", "ssd1351", "st7789"}:
        module = __import__(
            f"sbd.core.display.{config.driver}.driver",
            fromlist=["DisplayDriver"],
        )
        return module.DisplayDriver(config)
    raise ValueError(f"unknown display driver: {config.driver}")


__all__ = ["DisplayDevice", "make_display"]
