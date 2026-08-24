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
        self.drains = 0
        self.fail_on_write = False
        self.fail_on_drain = False

    def write(self, payload: bytes) -> int:
        if self.fail_on_write:
            raise OSError("mock write error")
        self.payloads.append(payload)
        return len(payload) // 8

    def close(self) -> None:
        self.closed += 1

    def drain(self) -> None:
        self.drains += 1
        if self.fail_on_drain:
            raise OSError("mock drain error")


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
    
    # Real resampler chunking equivalence
    pytest.importorskip("samplerate")
    real_whole = StreamFormatAdapter()
    real_split = StreamFormatAdapter()
    real_expected = real_whole.convert(source) + real_whole.flush()
    real_actual = b"".join(real_split.convert(source[index:index + 2]) for index in range(0, len(source), 2)) + real_split.flush()
    assert real_actual == real_expected


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
    resamplers: list[_TripleResampler] = []

    def make_resampler() -> _TripleResampler:
        r = _TripleResampler()
        resamplers.append(r)
        return r

    def factory() -> StreamFormatAdapter:
        return StreamFormatAdapter(resampler_factory=make_resampler)

    output = AlsaAudioOutput(_adapted_config(), adapter_factory=factory)
    sink = _FakePCM()
    output._pcm = sink
    output._executor = ThreadPoolExecutor(max_workers=1)
    output._started = True

    async def pcm(count=1):
        for _ in range(count):
            yield struct.pack("<h", 1)

    async def error_pcm():
        yield struct.pack("<h", 1)
        raise RuntimeError("force-abort")

    async def infinite_pcm(cancel_event):
        while True:
            yield struct.pack("<h", 1)
            cancel_event.set()
            await asyncio.sleep(0.1)

    async def scenario() -> None:
        # 5-reopen
        for _ in range(5):
            await output.play(pcm(1))

        # force-abort
        with pytest.raises(RuntimeError, match="force-abort"):
            await output.play(error_pcm())

        # write error
        sink.fail_on_write = True
        with pytest.raises(OSError, match="mock write error"):
            await output.play(pcm(1))
        sink.fail_on_write = False

        # cancellation
        cancel_event = asyncio.Event()
        task = asyncio.create_task(output.play(infinite_pcm(cancel_event)))
        await cancel_event.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        await output.stop()

    asyncio.run(scenario())

    # 5 plays + 1 abort + 1 error + 1 cancel = 8 resampler sessions
    assert len(resamplers) == 8
    # Only the five fully consumed, successfully written sessions are drained.
    assert sink.drains == 5
    # Adapter reset discards the current resampler reference
    assert output._adapter._resampler is None
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


def test_m3_audo_008() -> None:
    output = AlsaAudioOutput(
        _adapted_config(),
        adapter_factory=lambda: _adapter(_TripleResampler()),
    )
    sink = _FakePCM()
    sink.fail_on_drain = True
    output._pcm = sink
    output._executor = ThreadPoolExecutor(max_workers=1)
    output._started = True

    async def pcm():
        yield struct.pack("<h", 1)

    async def scenario() -> None:
        with pytest.raises(OSError, match="mock drain error"):
            await output.play(pcm())
        assert output._adapter._resampler is None
        await output.stop()

    asyncio.run(scenario())
    assert sink.drains == 1
    assert sink.closed == 1
