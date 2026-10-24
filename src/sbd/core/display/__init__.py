"""Lazy display HAL factory."""

from sbd.core.display.base import DisplayDevice
from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint, DisplayHintError, UnknownDisplaySlot
from sbd.core.display.renderer import Oled128Renderer, RenderModel


def make_display(config) -> DisplayDevice:
    if config.driver == "null":
        from sbd.core.display.null.driver import NullDisplay
        return NullDisplay()
    if config.driver == "mock":
        from sbd.core.display.mock.driver import MockDisplay
        return MockDisplay(config)
    if config.driver == "ssd1351":
        from sbd.core.display.ssd1351.driver import DisplayDriver
        return DisplayDriver(config)
    raise ValueError(f"unknown display driver: {config.driver}")


__all__ = [
    "DisplayArbiter", "DisplayDevice", "DisplayHint", "DisplayHintError",
    "Oled128Renderer", "RenderModel", "UnknownDisplaySlot", "make_display",
]
