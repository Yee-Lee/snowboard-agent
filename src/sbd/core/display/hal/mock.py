"""
Mock display device for PC development and CI.

Outputs frames to a PIL Image / log instead of real hardware.
Useful for unit tests and headless CI pipelines.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path
from typing import Optional

from .protocol import DisplayInfo, Rgb565Frame

logger = logging.getLogger(__name__)


class MockDisplayDevice:
    """
    Headless display backend.

    Implements the DisplayDevice protocol without requiring any hardware.
    Optionally saves each presented frame as a PNG for visual inspection.
    """

    def __init__(
        self,
        width: int = 128,
        height: int = 128,
        name: str = "mock",
        save_dir: Optional[Path] = None,
    ) -> None:
        self.info = DisplayInfo(width=width, height=height, name=name)
        self._save_dir = save_dir
        self._frame_count = 0
        self._is_open = False
        self._last_frame: Optional[bytes] = None

    # ------------------------------------------------------------------
    # DisplayDevice protocol
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._is_open:
            raise RuntimeError("MockDisplayDevice already started")
        self._is_open = True
        self._back_buffer = bytearray(self.info.width * self.info.height * 2)
        logger.info("[MockDisplay] start (%dx%d)", self.info.width, self.info.height)

    async def stop(self) -> None:
        if not self._is_open:
            return
        self._is_open = False
        if hasattr(self, "_back_buffer"):
            del self._back_buffer
        logger.info("[MockDisplay] stop (total frames: %d)", self._frame_count)

    def clear(self) -> None:
        if not self._is_open:
            raise RuntimeError("MockDisplayDevice.clear called before start()")
        logger.debug("[MockDisplay] clear")
        self._back_buffer = bytearray(self.info.width * self.info.height * 2)

    def write_pixels(self, frame: bytes) -> None:
        if not self._is_open:
            raise RuntimeError("MockDisplayDevice.write_pixels called before start()")
        expected = self.info.width * self.info.height * 2
        if len(frame) != expected:
            raise ValueError(f"Expected {expected} bytes, got {len(frame)}")
        self._back_buffer[:] = bytes(frame)

    def show(self) -> None:
        if not self._is_open:
            raise RuntimeError("MockDisplayDevice.show called before start()")
        self._last_frame = bytes(self._back_buffer)
        self._frame_count += 1
        logger.debug("[MockDisplay] show frame #%d", self._frame_count)
        if self._save_dir:
            self._save_png(self._last_frame)

    def size(self) -> tuple[int, int]:
        return (self.info.width, self.info.height)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def last_frame(self) -> Optional[bytes]:
        return self._last_frame

    def _save_png(self, frame: Rgb565Frame) -> None:
        """Save an RGB565 frame as PNG for visual inspection."""
        try:
            from PIL import Image  # type: ignore

            w, h = self.info.width, self.info.height
            rgb_data = bytearray(w * h * 3)
            for i in range(w * h):
                hi, lo = frame[i * 2], frame[i * 2 + 1]
                color = (hi << 8) | lo
                r = (color >> 11) & 0x1F
                g = (color >> 5) & 0x3F
                b = color & 0x1F
                rgb_data[i * 3]     = (r << 3) | (r >> 2)
                rgb_data[i * 3 + 1] = (g << 2) | (g >> 4)
                rgb_data[i * 3 + 2] = (b << 3) | (b >> 2)

            img = Image.frombytes("RGB", (w, h), bytes(rgb_data))
            path = self._save_dir / f"frame_{self._frame_count:06d}.png"
            img.save(path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("[MockDisplay] Failed to save PNG: %s", exc)
