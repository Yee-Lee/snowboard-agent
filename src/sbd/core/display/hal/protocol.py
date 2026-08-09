"""Compatibility exports; the sole DisplayDevice protocol lives in base.py."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DisplayDevice


@dataclass(frozen=True)
class DisplayInfo:
    """Non-protocol metadata retained for the current POC renderer."""

    width: int
    height: int
    name: str = "unknown"
    logical_width: int = 0
    logical_height: int = 0

    def __post_init__(self) -> None:
        if self.logical_width == 0:
            object.__setattr__(self, "logical_width", self.width)
        if self.logical_height == 0:
            object.__setattr__(self, "logical_height", self.height)


Rgb565Frame = bytes


@dataclass(frozen=True)
class Rect:
    """Legacy, non-contract rectangle type."""

    x: int
    y: int
    width: int
    height: int


__all__ = ["DisplayDevice", "DisplayInfo", "Rect", "Rgb565Frame"]
