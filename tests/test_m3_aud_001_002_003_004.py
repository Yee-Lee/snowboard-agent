"""M3 portable Audio HAL tests; P4-gated IDs remain Blocked in the manifest."""

from __future__ import annotations

import asyncio

import pytest

from sbd.core.audio.null import NullAudioInput, NullAudioOutput
from sbd.core.config.models import AudioConfig


def test_m3_aud_001() -> None:
    async def scenario():
        audio = NullAudioInput(AudioConfig(driver="null"), finite_frames=(bytes(640),))
        await audio.start()
        stream = audio.frames()
        with pytest.raises(RuntimeError, match="already streaming"):
            audio.frames()
        assert await anext(stream) == bytes(640)
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
        reopened = audio.frames()
        assert await anext(reopened) == bytes(640)
        await reopened.aclose()
        await audio.stop()
        await audio.stop()
    asyncio.run(scenario())


def test_m3_aud_002() -> None:
    async def scenario():
        consumed = []
        async def pcm():
            for index in range(5):
                consumed.append(index)
                yield bytes((index,))
        output = NullAudioOutput()
        await output.start()
        await output.play(pcm())
        await output.stop()
        await output.stop()
        assert consumed == list(range(5))
    asyncio.run(scenario())
