"""
integration/test_ssd1351_present.py

Hardware diagnostic for the Waveshare 1.5-inch OLED (SSD1351).

Enters at the HAL layer:
    test → HAL → Native

Run::

    pytest tests/integration/test_ssd1351_present.py -s

Requires libdisplay.so to be compiled in native/waveshare_ssd1351/.
"""

from __future__ import annotations

import asyncio
import pytest

from sbd.core.display.hal.factory import create_device
from sbd.core.display.hal.protocol import Rect


@pytest.fixture
async def device():
    dev = create_device("waveshare_oled_1in5_rgb")
    await dev.open()
    yield dev
    await dev.close()


@pytest.mark.asyncio
async def test_present_black_frame(device):
    """Push a black frame to the OLED."""
    w, h = device.info.width, device.info.height
    black = bytes(w * h * 2)
    await device.present(black)


@pytest.mark.asyncio
async def test_present_white_frame(device):
    """Push a white (0xFFFF) frame to the OLED."""
    w, h = device.info.width, device.info.height
    white = b"\xFF\xFF" * (w * h)
    await device.present(white)


@pytest.mark.asyncio
async def test_clear(device):
    await device.clear()


@pytest.mark.asyncio
async def test_present_gradient(device):
    """Push a simple blue gradient frame."""
    from PIL import Image
    from sbd.core.display.rendering.renderer import canvas_to_rgb565

    w, h = device.info.width, device.info.height
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), (0, 0, int(255 * x / w)))

    await device.present(canvas_to_rgb565(img))
