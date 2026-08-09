"""
integration/test_st7789_present.py

Hardware diagnostic for the Waveshare 2-inch LCD (ST7789).

Enters at the HAL layer:
    test → HAL → Native

Run::

    pytest tests/integration/test_st7789_present.py -s

Requires libdisplay.so to be compiled in native/waveshare_st7789/.
"""

from __future__ import annotations

import asyncio
import asyncio
import pytest

from sbd.core.display.hal.factory import create_device

pytestmark = [
    pytest.mark.pi_only,
    pytest.mark.skip(reason="optional ST7789 fixture is outside v0.3 primary acceptance"),
]


@pytest.fixture
def device(display_config_path):
    dev = create_device(
        "waveshare_lcd_2in_rgb",
        config_path=display_config_path,
    )
    asyncio.run(dev.start())
    yield dev
    asyncio.run(dev.stop())
    asyncio.run(dev.stop())


@pytest.mark.pi_only
def test_present_black_frame(device):
    """Push a black frame to the LCD."""
    w, h = device.info.width, device.info.height
    black = bytes(w * h * 2)
    device.write_pixels(black)
    device.show()


@pytest.mark.pi_only
def test_present_red_frame(device):
    """Push a solid-red frame (useful for checking orientation)."""
    w, h = device.info.width, device.info.height
    # RGB565: red = 0xF800
    red = b"\xF8\x00" * (w * h)
    device.write_pixels(red)
    device.show()


@pytest.mark.pi_only
def test_clear(device):
    device.clear()
    device.show()


@pytest.mark.pi_only
def test_present_gradient(device):
    """Push a full-colour gradient."""
    from PIL import Image
    from sbd.core.display.rendering.renderer import canvas_to_rgb565

    w, h = device.info.width, device.info.height
    img = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            img.putpixel((x, y), (int(255 * x / w), int(255 * y / h), 128))

    device.write_pixels(canvas_to_rgb565(img))
    device.show()
