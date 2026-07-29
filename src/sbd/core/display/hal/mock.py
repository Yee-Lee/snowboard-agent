"""
Mock display device for PC development and CI.

Outputs frames to a PIL Image / log instead of real hardware.
Useful for unit tests and headless CI pipelines.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from pathlib import Path
from typing import Optional

from .protocol import DisplayDevice, DisplayInfo, Rect, Rgb565Frame

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

    async def open(self) -> None:
        self._is_open = True
        logger.info("[MockDisplay] open  (%dx%d)", self.info.width, self.info.height)

    async def present(self, frame: Rgb565Frame) -> None:
        if not self._is_open:
            raise RuntimeError("MockDisplayDevice.present called before open()")

        self._last_frame = bytes(frame)
        self._frame_count += 1
        logger.debug("[MockDisplay] frame #%d (%d bytes)", self._frame_count, len(frame))

        if self._save_dir:
            self._save_png(frame)

    async def present_rect(self, rect: Rect, frame: Rgb565Frame) -> None:
        logger.debug(
            "[MockDisplay] present_rect x=%d y=%d w=%d h=%d",
            rect.x, rect.y, rect.width, rect.height,
        )

    async def clear(self) -> None:
        logger.debug("[MockDisplay] clear")
        self._last_frame = bytes(self.info.width * self.info.height * 2)

    async def close(self) -> None:
        self._is_open = False
        logger.info("[MockDisplay] close (total frames: %d)", self._frame_count)

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
