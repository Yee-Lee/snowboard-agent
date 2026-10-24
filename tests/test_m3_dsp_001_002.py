"""M3 portable DisplayDevice tests."""

from __future__ import annotations

import asyncio

import pytest

from sbd.core.config.models import DisplayConfig
from sbd.core.display.mock import MockDisplay
from sbd.core.display.null import NullDisplay


def test_m3_dsp_001() -> None:
    async def scenario():
        display = NullDisplay()
        await display.start()
        display.clear()
        display.write_pixels(b"buffer ignored by null device")
        display.show()
        assert display.size() == (0, 0)
        await display.stop()
        await display.stop()
    asyncio.run(scenario())


def test_m3_dsp_002() -> None:
    display = MockDisplay(DisplayConfig())
    display.write_pixels(bytes(32768))
    with pytest.raises(ValueError, match="invalid length"):
        display.write_pixels(bytes(32767))
