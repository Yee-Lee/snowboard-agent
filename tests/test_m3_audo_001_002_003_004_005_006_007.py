"""Portable tests for M3 AudioOutput stream-to-native adaptation."""

from __future__ import annotations

import asyncio
import struct
from concurrent.futures import ThreadPoolExecutor

import pytest

from sbd.core.audio.alsa.adaptation import StreamFormatAdapter
from sbd.core.audio.alsa.output import AlsaAudioOutput
from sbd.core.config.models import AudioConfig, AudioFormatConfig, AudioOutputConfig


class _TripleResampler:
    """Deterministic stateful test seam that expands every input sample by three."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[float], bool]] = []

    def process(self, samples, *, ratio: float, end_of_input: bool):
        assert ratio == 3.0
        items = [float(sample) for sample in samples]
        self.calls.append((items, end_of_input))
        return [sample for sample in items for _ in range(3)]


class _TailResampler(_TripleResampler):
    def __init__(self) -> None:
        super().__init__()
        self._tail: list[float] = []

    def process(self, samples, *, ratio: float, end_of_input: bool):
        items = [float(sample) for sample in samples]
        self.calls.append((items, end_of_input))
        if end_of_input:
            result, self._tail = self._tail, []
            return result
        if items:
            self._tail = [items[-1]] * 3
        return [sample for sample in items[:-1] for _ in range(3)]


class _FakePCM:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []
        self.closed = 0

    def write(self, payload: bytes) -> int:
        self.payloads.append(payload)
        return len(payload) // 8

    def close(self) -> None:
        self.closed += 1


def _adapted_config() -> AudioConfig:
    stream = AudioFormatConfig(sample_rate=16_000, channels=1, sample_format="s16_le")
    native = AudioFormatConfig(sample_rate=48_000, channels=2, sample_format="s32_le")
    return AudioConfig(driver="alsa", output=AudioOutputConfig(stream_format=stream, native_format=native))


def _passthrough_config() -> AudioConfig:
    native = AudioFormatConfig(sample_rate=48_000, channels=2, sample_format="s32_le")
    return AudioConfig(driver="alsa", output=AudioOutputConfig(stream_format=native, native_format=native))


def _adapter(resampler) -> StreamFormatAdapter:
    return StreamFormatAdapter(resampler_factory=lambda: resampler)


def test_m3_audo_001() -> None:
    adapter = _adapter(_TripleResampler())
    samples = [-32_768, 0, 32_767]
    converted = adapter.convert(struct.pack("<3h", *samples))
    assert len(converted) == len(samples) * 3 * 2 * 4
    values = struct.unpack(f"<{len(converted) // 4}i", converted)
    assert values == tuple(
        value
        for sample in (-2_147_483_648, 0, 2_147_418_112)
        for _ in range(3)
        for value in (sample, sample)
    )


def test_m3_audo_002() -> None:
    source = struct.pack("<8h", *range(-4, 4))
    whole = _adapter(_TripleResampler())
    split = _adapter(_TripleResampler())
    expected = whole.convert(source) + whole.flush()
    actual = b"".join(split.convert(source[index:index + 2]) for index in range(0, len(source), 2)) + split.flush()
    assert actual == expected


def test_m3_audo_003() -> None:
    converted = _adapter(_TripleResampler()).convert(struct.pack("<2h", -16_384, 16_384))
    assert len(converted) == 2 * 3 * 2 * 4
    assert struct.unpack("<12i", converted) == (
        -1_073_741_824, -1_073_741_824, -1_073_741_824, -1_073_741_824,
        -1_073_741_824, -1_073_741_824, 1_073_741_824, 1_073_741_824,
        1_073_741_824, 1_073_741_824, 1_073_741_824, 1_073_741_824,
    )


def test_m3_audo_004() -> None:
    adapter = _adapter(_TailResampler())
    assert adapter.convert(struct.pack("<2h", 0, 16_384)) == bytes(24)
    tail = adapter.flush()
    assert struct.unpack("<6i", tail) == (1_073_741_824,) * 6


def test_m3_audo_005() -> None:
    adapters: list[StreamFormatAdapter] = []

    def factory() -> StreamFormatAdapter:
        adapter = _adapter(_TripleResampler())
        adapters.append(adapter)
        return adapter

    output = AlsaAudioOutput(_adapted_config(), adapter_factory=factory)
    sink = _FakePCM()
    output._pcm = sink
    output._executor = ThreadPoolExecutor(max_workers=1)
    output._started = True

    async def pcm():
        yield struct.pack("<h", 1)

    async def scenario() -> None:
        await output.play(pcm())
        await output.play(pcm())
        await output.stop()

    asyncio.run(scenario())
    assert len(b"".join(sink.payloads)) == 2 * 3 * 2 * 4
    assert all(adapter._resampler is None for adapter in adapters)
    assert sink.closed == 1


def test_m3_audo_006() -> None:
    unsupported = AudioFormatConfig(sample_rate=44_100, channels=2, sample_format="s32_le")
    with pytest.raises(ValueError, match="native format"):
        AlsaAudioOutput(AudioConfig(driver="alsa", output=AudioOutputConfig(stream_format=unsupported, native_format=unsupported)))
    assert AlsaAudioOutput(_passthrough_config())._adapter is None


def test_m3_audo_007() -> None:
    output = AlsaAudioOutput(_passthrough_config())
    sink = _FakePCM()
    output._pcm = sink
    output._write_worker(bytes(16))
    assert sink.payloads == [bytes(16)]
