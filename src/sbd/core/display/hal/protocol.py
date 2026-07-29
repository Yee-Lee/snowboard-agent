"""
HAL Protocol definitions.

Defines the DisplayDevice protocol (interface) and related data types.
The HAL knows about panel capabilities, resolution, rotation, and pixel
format — but knows nothing about product UI, animations, or content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DisplayInfo:
    """Immutable metadata about a physical display panel."""
    width: int
    height: int
    name: str = "unknown"
    # Logical canvas size (may differ from physical if scaling is applied)
    logical_width: int = 0
    logical_height: int = 0

    def __post_init__(self) -> None:
        # Default logical size equals physical size
        if self.logical_width == 0:
            object.__setattr__(self, "logical_width", self.width)
        if self.logical_height == 0:
            object.__setattr__(self, "logical_height", self.height)


# RGB565 frame: a bytes-like object whose length == width * height * 2
Rgb565Frame = bytes | bytearray | memoryview


@dataclass
class Rect:
    """Axis-aligned rectangle in pixel coordinates."""
    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class DisplayDevice(Protocol):
    """
    Structural protocol that every display backend must implement.

    The HAL layer owns open/present/clear/close.  Only DisplayService
    may call these methods; no other module should touch them directly.
    """

    info: DisplayInfo

    async def open(self) -> None:
        """Initialise the panel (GPIO, SPI, power-on sequence …)."""
        ...

    async def present(self, frame: Rgb565Frame) -> None:
        """Push a full-screen RGB565 frame to the panel."""
        ...

    async def present_rect(self, rect: Rect, frame: Rgb565Frame) -> None:
        """Push a partial RGB565 frame for the given rectangle."""
        ...

    async def clear(self) -> None:
        """Fill the entire panel with black (0x0000)."""
        ...

    async def close(self) -> None:
        """Release hardware resources (GPIO, SPI, power-off …)."""
        ...
