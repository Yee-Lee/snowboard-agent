"""The manual timeout fixture must keep waiting after a prior Look timeout."""

import asyncio

import pytest

from scripts.m5tool_manual import _TimeoutVision


@pytest.mark.asyncio
async def test_timeout_fixture_remains_blocked_after_abort():
    vision = _TimeoutVision()
    for _ in range(2):
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(vision.describe(b"image"), 0.01)
        await vision.abort()
