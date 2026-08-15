"""M3 Audio target-device acceptance cards; run only with ``-m rpi``."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from statistics import quantiles
from time import monotonic

import pytest

from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.audio.null import NullAudioInput
from sbd.core.config.models import AudioConfig, AudioInputConfig
from tests.rpi_support import record_result, require_manual, rpi_config


pytestmark = pytest.mark.rpi


async def _frames(input_device, count: int) -> tuple[list[bytes], list[float]]:
    stream = input_device.frames()
    frames, elapsed = [], []
    try:
        for _ in range(count):
            started = monotonic()
            frame = await anext(stream)
            elapsed.append(monotonic() - started)
            frames.append(frame)
    finally:
        await stream.aclose()
    return frames, elapsed


def test_m3_audi_001() -> None:
    config = rpi_config()
    assert config.core.audio.driver == "alsa"

    async def scenario() -> None:
        capture = make_audio_input(config.core.audio)
        playback = make_audio_output(config.core.audio)
        await capture.start()
        await playback.start()
        try:
            frames, _ = await _frames(capture, 3)
            assert all(len(frame) == 640 for frame in frames)

            async def native_fixture():
                yield bytes(960 * 8)

            await playback.play(native_fixture())
        finally:
            await capture.stop()
            await playback.stop()
    asyncio.run(scenario())
    record_result("M3-AUDI-001", frames=3, frame_bytes=640)


def test_m3_audi_002() -> None:
    config = rpi_config()
    bad_input = replace(config.core.audio.input, device="hw:__missing__,0")
    broken = replace(config.core.audio, input=bad_input)

    async def scenario() -> None:
        real = make_audio_input(broken)
        with pytest.raises(Exception):
            await real.start()
        fallback = NullAudioInput(AudioConfig(driver="null"))
        await fallback.start()
        frame = await anext(fallback.frames())
        assert len(frame) == 640
        await fallback.stop()
    asyncio.run(scenario())
    record_result("M3-AUDI-002", fallback="null", capability=False)


def test_m3_audi_003() -> None:
    rpi_config()
    require_manual("M3-AUDI-003")
    record_result("M3-AUDI-003", manual="PASS")


def test_m3_audi_004() -> None:
    config = rpi_config()
    assert config.core.audio.driver == "alsa"

    async def scenario() -> list[float]:
        all_samples: list[float] = []
        for _ in range(3):
            capture = make_audio_input(config.core.audio)
            await capture.start()
            try:
                frames, samples = await _frames(capture, 100)
                assert all(len(frame) == 640 for frame in frames)
                all_samples.extend(samples)
            finally:
                await capture.stop()
                await capture.stop()
        return all_samples
    samples = asyncio.run(scenario())
    record_result(
        "M3-AUDI-004", samples=len(samples), p50=quantiles(samples, n=100)[49],
        p95=quantiles(samples, n=100)[94], maximum=max(samples),
    )
