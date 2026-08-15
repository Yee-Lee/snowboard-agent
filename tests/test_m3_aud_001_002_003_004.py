"""M3 portable Audio HAL tests; P4-gated IDs remain Blocked in the manifest."""

from __future__ import annotations

import asyncio
import math
import struct
import time

import pytest

from sbd.core.audio.null import NullAudioInput, NullAudioOutput
from sbd.core.audio.alsa.input import AlsaAudioInput
from sbd.core.config.models import (
    AudioConfig, AudioFormatConfig, AudioInputConfig, AudioOutputConfig,
)


def _alsa_config(*, channel: int = 0) -> AudioConfig:
    native = AudioFormatConfig(sample_rate=48_000, channels=2, sample_format="s32_le")
    stream = AudioFormatConfig(sample_rate=16_000, channels=1, sample_format="s16_le")
    return AudioConfig(
        driver="alsa",
        input=AudioInputConfig(
            stream_format=stream, frame_duration_ms=20, device="hw:0,0",
            native_format=native, channel_index=channel, valid_bits=24,
            valid_bits_alignment="msb", resampler="samplerate.sinc_best",
        ),
        output=AudioOutputConfig(stream_format=native, device="hw:0,0", native_format=native),
    )


def _stereo_s32(left: list[int], right: list[int]) -> bytes:
    return b"".join(
        struct.pack("<ii", value << 8, other << 8)
        for value, other in zip(left, right, strict=True)
    )


class _RawSource:
    def __init__(self, chunks: list[bytes], *, pause_on_read: int | None = None) -> None:
        self._chunks = iter(chunks)
        self._pause_on_read = pause_on_read
        self.reads = 0
        self.close_calls = 0

    def read(self) -> bytes:
        self.reads += 1
        if self._pause_on_read == self.reads:
            time.sleep(0.05)
        return next(self._chunks)

    def close(self) -> None:
        self.close_calls += 1


class _StreamingDecimator:
    """Stateful test seam: preserve every third input sample across chunks."""
    def __init__(self) -> None:
        self.pending: list[float] = []
        self.ratios: list[float] = []

    def process(self, samples: list[float], ratio: float) -> list[float]:
        self.ratios.append(ratio)
        self.pending.extend(samples)
        count = len(self.pending) // 3 * 3
        output = self.pending[:count:3]
        del self.pending[:count]
        return output


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

    def rms(values) -> float:
        settled = values[100:-100]
        return math.sqrt(sum(value * value for value in settled) / len(settled))

    from sbd.core.audio.alsa.input import AlsaAudioInput as SelectedInput
    one_khz = [math.sin(2 * math.pi * 1_000 * index / 48_000) for index in range(48_000)]
    twelve_khz = [math.sin(2 * math.pi * 12_000 * index / 48_000) for index in range(48_000)]
    passband = rms(SelectedInput._make_resampler().process(one_khz, 1 / 3))
    stopband = rms(SelectedInput._make_resampler().process(twelve_khz, 1 / 3))
    assert 20 * math.log10(stopband / passband) <= -40


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


def test_m3_aud_003() -> None:
    """Selected-channel decode, MSB 24-bit scale, framing, and worker isolation."""
    left = [0] * 960
    left[0], left[3], left[6], left[9] = -8_388_608, -1_000_000, 8_388_607, 0
    right = [1_000_000] * 960
    payload = _stereo_s32(left, right)
    source = _RawSource([payload[:37], payload[37:4099], payload[4099:]], pause_on_read=2)
    resampler = _StreamingDecimator()
    audio = AlsaAudioInput(
        _alsa_config(channel=0), source_factory=lambda: source,
        resampler_factory=lambda: resampler,
    )

    async def scenario() -> None:
        await audio.start()
        stream = audio.frames()
        heartbeat = 0

        async def tick() -> None:
            nonlocal heartbeat
            for _ in range(12):
                await asyncio.sleep(0.005)
                heartbeat += 1

        ticker = asyncio.create_task(tick())
        frame = await anext(stream)
        await ticker
        assert len(frame) == 640
        values = struct.unpack("<320h", frame)
        assert values[:4] == (-32_768, -3_906, 32_767, 0)
        assert resampler.ratios and set(resampler.ratios) == {1 / 3}
        assert heartbeat == 12
        await stream.aclose()
        assert source.close_calls == 1
        await audio.stop()
        await audio.stop()
    asyncio.run(scenario())


def test_m3_aud_004() -> None:
    """Closing or failing a stream resets source, converter, and partial state."""
    impulse = [8_388_607] + [0] * 959
    silence = [0] * 960
    first = _RawSource([_stereo_s32(impulse, silence)])
    second = _RawSource([_stereo_s32(impulse, silence)])
    sources = iter((first, second))
    resamplers: list[_StreamingDecimator] = []

    def make_resampler() -> _StreamingDecimator:
        result = _StreamingDecimator()
        resamplers.append(result)
        return result

    audio = AlsaAudioInput(
        _alsa_config(), source_factory=lambda: next(sources), resampler_factory=make_resampler,
    )

    async def scenario() -> None:
        await audio.start()
        stream = audio.frames()
        first_frame = await anext(stream)
        await stream.aclose()
        assert first.close_calls == 1
        reopened = audio.frames()
        reopened_frame = await anext(reopened)
        assert reopened_frame == first_frame
        await reopened.aclose()
        assert second.close_calls == 1
        assert len(resamplers) == 2
        assert all(not item.pending for item in resamplers)
        await audio.stop()
    asyncio.run(scenario())
