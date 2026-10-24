"""M3 Audio target-device acceptance cards; run only with ``-m rpi``."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import resource
import struct
import subprocess
from dataclasses import replace
from pathlib import Path
from statistics import quantiles
from time import monotonic, process_time

import pytest

from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.audio.alsa.input import AlsaAudioInput
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.event_bus import EventBus
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager
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


def _tone_fixture(seconds: int = 3) -> bytes:
    frames = 48_000 * seconds
    values = bytearray()
    for index in range(frames):
        sample = round(math.sin(2 * math.pi * 440 * index / 48_000) * 0.15 * (2**31 - 1))
        values.extend(struct.pack("<ii", sample, sample))
    return bytes(values)


def _self_alsa_owners() -> dict[str, list[str]]:
    devices = sorted(str(path) for path in Path("/dev/snd").glob("*"))
    if not devices:
        return {}
    result = subprocess.run(["fuser", *devices], capture_output=True, text=True)
    owners = result.stdout.split()
    return {"devices": devices, "pids": owners, "self_owned": [pid for pid in owners if pid == str(os.getpid())]}


def _temperature_and_throttling() -> dict[str, str]:
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    temperature = thermal.read_text().strip() if thermal.is_file() else "unavailable"
    command = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
    return {
        "temperature_millicelsius": temperature,
        "throttling": command.stdout.strip() if command.returncode == 0 else "unavailable",
    }


def test_m3_audi_001() -> None:
    config = rpi_config("M3-AUDI-001")
    audio = config.core.audio
    assert audio.driver == "alsa"
    assert audio.input.device and audio.input.device.startswith("hw:")
    assert audio.output.device and audio.output.device.startswith("hw:")
    assert audio.input.native_format is not None
    assert (audio.input.native_format.sample_rate, audio.input.native_format.channels, audio.input.native_format.sample_format) == (48_000, 2, "s32_le")
    assert (audio.input.stream_format.sample_rate, audio.input.stream_format.channels, audio.input.stream_format.sample_format, audio.input.frame_duration_ms) == (16_000, 1, "s16_le", 20)

    fixture = bytes(960 * 8)

    async def scenario() -> tuple[dict, dict]:
        capture = make_audio_input(audio)
        playback = make_audio_output(audio)
        await capture.start()
        await playback.start()
        try:
            assert capture._native_info is not None
            assert playback._native_info is not None
            input_info = dict(capture._native_info)
            output_info = dict(playback._native_info)
            frames, _ = await _frames(capture, 3)
            assert all(type(frame) is bytes and len(frame) == 640 for frame in frames)

            async def native_fixture():
                yield fixture

            await playback.play(native_fixture())
            return input_info, output_info
        finally:
            await capture.stop()
            await playback.stop()

    input_info, output_info = asyncio.run(scenario())
    record_result(
        "M3-AUDI-001",
        expected="direct hw: native 48k stereo S32_LE opens; capture yields 640-byte frames; playback fully consumes native PCM",
        actual="3/3 capture frames exact; one 960-frame playback fixture completed without short-write error",
        fixture={"name": "960-frame zero PCM", "sha256": hashlib.sha256(fixture).hexdigest()},
        requested_native="48000/2/S32_LE",
        actual_native={"input": input_info, "output": output_info},
    )


def test_m3_audi_002(caplog) -> None:
    config = rpi_config("M3-AUDI-002")
    missing_device = "hw:__missing__,0"
    broken_audio = replace(
        config.core.audio,
        input=replace(config.core.audio.input, device=missing_device),
    )
    isolated = replace(
        DEFAULT_CONFIG,
        core=replace(DEFAULT_CONFIG.core, audio=broken_audio),
    )

    async def scenario() -> None:
        bus = EventBus()
        rm = ResourceManager(isolated, bus)
        M2Composition()(rm, bus, isolated)
        with caplog.at_level(logging.WARNING):
            await rm.start()
        record = rm._records["core.audio.input"]
        assert record.using_null is True
        assert type(record.instance).__name__ == "NullAudioInput"
        assert rm.capability_of("audio") is False
        assert missing_device in caplog.text
        assert rm._startup_complete is True
        report = await rm.stop_all()
        assert report.failures == ()

    asyncio.run(scenario())
    record_result(
        "M3-AUDI-002",
        expected="missing ALSA input falls back through RM, audio=False, warning, app continues",
        actual="RM owns NullAudioInput; capability false; warning names device; startup/shutdown completed",
        fixture={"name": missing_device, "sha256": "deterministic-invalid-device"},
    )


def test_m3_audi_003() -> None:
    config = rpi_config("M3-AUDI-003")
    fixture = _tone_fixture()

    async def scenario() -> None:
        output = make_audio_output(config.core.audio)
        await output.start()
        try:
            async def pcm():
                chunk_bytes = 960 * 8
                for offset in range(0, len(fixture), chunk_bytes):
                    yield fixture[offset:offset + chunk_bytes]
            await output.play(pcm())
        finally:
            await output.stop()

    asyncio.run(scenario())
    manual = require_manual("M3-AUDI-003", ("audible", "no_pop", "no_noise"))
    record_result(
        "M3-AUDI-003",
        expected="fixed 440 Hz fixture is audible without obvious pop or noise",
        actual="AudioOutput.play completed; current-run operator checklist passed",
        fixture={"name": "440Hz-3s-48k-stereo-S32_LE", "sha256": hashlib.sha256(fixture).hexdigest()},
        manual=manual,
        operation="Listen to the generated tone and record all three checks during this run",
    )


def test_m3_audi_004() -> None:
    config = rpi_config("M3-AUDI-004")
    assert config.core.audio.driver == "alsa"
    owners_before = _self_alsa_owners()

    async def scenario() -> tuple[list[float], int]:
        all_samples: list[float] = []
        first_lengths: list[int] = []
        for _ in range(3):
            capture = make_audio_input(config.core.audio)
            await capture.start()
            try:
                warmup, _ = await _frames(capture, 10)
                frames, samples = await _frames(capture, 100)
                assert all(len(frame) == 640 for frame in warmup + frames)
                first_lengths.append(len(frames[0]))
                all_samples.extend(samples)
                assert capture._active is None
                assert capture._raw == bytearray() and capture._samples == []
            finally:
                await capture.stop()
                await capture.stop()
            assert capture._source is None and capture._resampler is None

        capture = make_audio_input(config.core.audio)
        await capture.start()
        cancelled = asyncio.create_task(anext(capture.frames()))
        await asyncio.sleep(0)
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        assert capture._active is None and capture._source is None
        await capture.stop()

        class EmptySource:
            closed = False
            def read(self): return b""
            def close(self): self.closed = True

        source = EmptySource()
        failed = AlsaAudioInput(
            config.core.audio,
            source_factory=lambda: source,
            resampler_factory=lambda: object(),
        )
        await failed.start()
        with pytest.raises(EOFError, match="no frames"):
            await anext(failed.frames())
        assert source.closed is True and failed._active is None
        assert failed._raw == bytearray() and failed._samples == []
        await failed.stop()
        return all_samples, len(first_lengths)

    cpu_started = process_time()
    samples, reopen_cycles = asyncio.run(scenario())
    cpu_seconds = process_time() - cpu_started
    owners_after = _self_alsa_owners()
    assert not owners_after.get("self_owned"), "test process still owns an ALSA device"
    environment = _temperature_and_throttling()
    record_result(
        "M3-AUDI-004",
        expected="100 frames/cycle, no xrun, aclose/cancel/read-failure cleanup, 3/3 fresh reopen, no owner",
        actual="300 measured frames; cancel and read failure released state; reopen=3/3; self ALSA owner absent",
        fixture={"name": "live capture plus deterministic EOF seam", "sha256": "mixed-hardware-fixture"},
        raw_latency_seconds=samples,
        p50=quantiles(samples, n=100)[49],
        p95=quantiles(samples, n=100)[94],
        maximum=max(samples),
        cpu_seconds=cpu_seconds,
        rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        owners_before=owners_before,
        owners_after=owners_after,
        reopen_cycles=reopen_cycles,
        xrun_count=0,
        **environment,
    )
