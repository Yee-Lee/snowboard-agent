"""Format-valid null camera including a pure-Python solid JPEG encoder."""

from __future__ import annotations

import logging
import math

from sbd.core.config.models import CameraConfig


def _segment(marker: int, payload: bytes) -> bytes:
    length = len(payload) + 2
    return bytes((0xFF, marker)) + length.to_bytes(2, "big") + payload


def make_blank_jpeg(width: int, height: int) -> bytes:
    """Encode a baseline grayscale black JPEG for arbitrary valid dimensions."""
    if not (1 <= width <= 65_535 and 1 <= height <= 65_535):
        raise ValueError("JPEG dimensions are out of range")
    app0 = _segment(
        0xE0,
        b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00",
    )
    dqt = _segment(0xDB, bytes((0,)) + bytes((16,)) * 64)
    sof = _segment(
        0xC0,
        bytes((8,))
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + bytes((1, 1, 0x11, 0)),
    )
    dc_counts = bytes((0, 2)) + bytes(14)
    dc_table = _segment(0xC4, bytes((0x00,)) + dc_counts + bytes((0, 7)))
    ac_counts = bytes((1,)) + bytes(15)
    ac_table = _segment(0xC4, bytes((0x10,)) + ac_counts + bytes((0,)))
    sos = _segment(0xDA, bytes((1, 1, 0x00, 0, 63, 0)))

    block_count = math.ceil(width / 8) * math.ceil(height / 8)
    bits = "0101111110" + "000" * (block_count - 1)
    bits += "1" * ((8 - len(bits) % 8) % 8)
    entropy = bytearray()
    for offset in range(0, len(bits), 8):
        value = int(bits[offset : offset + 8], 2)
        entropy.append(value)
        if value == 0xFF:
            entropy.append(0)
    return (
        b"\xff\xd8"
        + app0
        + dqt
        + sof
        + dc_table
        + ac_table
        + sos
        + bytes(entropy)
        + b"\xff\xd9"
    )


class NullCamera:
    def __init__(
        self,
        config: CameraConfig | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config or CameraConfig(driver="null")
        self._logger = logger or logging.getLogger(__name__)
        self._started = False
        if self._config.width <= 0 or self._config.height <= 0:
            raise ValueError("camera dimensions must be positive")
        if self._config.format not in {"JPEG", "RGB", "YUV"}:
            raise ValueError("unknown camera format")
        self._blank = self._make_blank()

    async def start(self) -> None:
        if not self._started:
            self._logger.info("camera running in null mode")
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def capture(self) -> bytes:
        return self._blank

    def _make_blank(self) -> bytes:
        pixels = self._config.width * self._config.height
        if self._config.format == "RGB":
            return bytes(pixels * 3)
        if self._config.format == "YUV":
            return bytes(pixels) + bytes((0x80,)) * (pixels // 2)
        return make_blank_jpeg(self._config.width, self._config.height)
