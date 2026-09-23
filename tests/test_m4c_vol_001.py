"""M4C-VOL-001 — startup-static S16_LE gain and product composition."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from sbd.core.audio import VolumeControl, VolumeControlledAudioOutput
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.config import ConfigTypeError, ConfigValueError, load_config
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import AudioOutputConfig
from sbd.core.event_bus import EventBus
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager


async def _chunks(*values: bytes):
    for value in values:
        yield value


def _pcm(*samples: int) -> bytes:
    return b"".join(value.to_bytes(2, "little", signed=True) for value in samples)


def _samples(value: bytes) -> tuple[int, ...]:
    return tuple(
        int.from_bytes(value[index:index + 2], "little", signed=True)
        for index in range(0, len(value), 2)
    )


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (100, (-32768, -101, -1, 0, 1, 101, 32767)),
        (0, (0, 0, 0, 0, 0, 0, 0)),
        (25, (-8192, -25, 0, 0, 0, 25, 8191)),
        (1, (-327, -1, 0, 0, 0, 1, 327)),
        (99, (-32440, -99, 0, 0, 0, 99, 32439)),
    ],
)
def test_m4c_vol_001_v01_v04_exact_scaling(percent, expected) -> None:
    async def run() -> None:
        raw = MockAudioOutput()
        output = VolumeControlledAudioOutput(raw, percent)
        source = _pcm(-32768, -101, -1, 0, 1, 101, 32767)
        await output.play(_chunks(source))
        assert len(raw.frames_played) == 1
        assert len(raw.frames_played[0]) == len(source)
        assert _samples(raw.frames_played[0]) == expected
        if percent == 100:
            assert raw.frames_played[0] is source

    asyncio.run(run())


@pytest.mark.parametrize("value", [-1, 101, 100.5, None, True])
def test_m4c_vol_001_v05_invalid_value_has_no_side_effect(value) -> None:
    raw = MockAudioOutput()
    with pytest.raises((TypeError, ValueError)):
        VolumeControlledAudioOutput(raw, value)  # type: ignore[arg-type]
    assert raw.frames_played == []


@pytest.mark.parametrize("chunk", [b"x", b"xyz", bytearray(b"xx")])
def test_m4c_vol_001_v06_rejects_invalid_pcm(chunk) -> None:
    async def run() -> None:
        raw = MockAudioOutput()
        output = VolumeControlledAudioOutput(raw, 25)
        with pytest.raises(ValueError):
            await output.play(_chunks(chunk))  # type: ignore[arg-type]
        assert raw.frames_played == []

    asyncio.run(run())


def test_m4c_vol_001_v07_chunks_are_independent_and_control_updates_next_chunk() -> None:
    async def source(output):
        yield _pcm(100)
        output.set_volume_percent(50)
        yield _pcm(100)

    async def run() -> None:
        raw = MockAudioOutput()
        output = VolumeControlledAudioOutput(raw, 25)
        await output.play(source(output))
        assert tuple(_samples(value)[0] for value in raw.frames_played) == (25, 50)

    asyncio.run(run())


def test_m4c_vol_001_v08_cancel_and_error_propagate() -> None:
    async def cancelled():
        yield _pcm(1)
        raise asyncio.CancelledError

    async def run() -> None:
        raw = MockAudioOutput()
        output = VolumeControlledAudioOutput(raw, 25)
        with pytest.raises(asyncio.CancelledError):
            await output.play(cancelled())
        assert raw.frames_played == [_pcm(0)]

    asyncio.run(run())


def test_m4c_vol_001_v09_separate_control_port() -> None:
    output = VolumeControlledAudioOutput(MockAudioOutput(), 25)
    assert isinstance(output, VolumeControl)
    assert output.get_volume_percent() == 25
    output.set_volume_percent(75)
    assert output.get_volume_percent() == 75


def test_m4c_vol_001_v10_composition_has_exactly_one_wrapper() -> None:
    async def run() -> None:
        bus = EventBus()
        rm = ResourceManager(DEFAULT_CONFIG, bus)
        M2Composition()(rm, bus, DEFAULT_CONFIG)
        await rm.start()
        try:
            output = rm._records["core.audio.output"].instance
            assert type(output) is VolumeControlledAudioOutput
            assert not isinstance(output.raw_output, VolumeControlledAudioOutput)
            speak = rm._records["worker.action.speak"].instance
            assert speak._audio_output is output
        finally:
            await rm.stop_all()

    asyncio.run(run())


def test_m4c_vol_001_v11_default_and_explicit_100_are_identical(tmp_path) -> None:
    default = load_config(local_path=tmp_path / "missing", environ={})
    config_path = tmp_path / "config.yaml"
    config_path.write_text("core:\n  audio:\n    output:\n      volume_percent: 100\n")
    explicit = load_config(local_path=config_path, environ={})
    assert default.core.audio.output.volume_percent == 100
    assert explicit.core.audio.output.volume_percent == 100


@pytest.mark.parametrize("value", [-1, 101])
def test_m4c_vol_001_v05_config_range(value, tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"core:\n  audio:\n    output:\n      volume_percent: {value}\n")
    with pytest.raises(ConfigValueError, match="volume_percent"):
        load_config(local_path=config_path, environ={})


@pytest.mark.parametrize("value", ["true", "100.5", "null"])
def test_m4c_vol_001_v05_config_type(value, tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(f"core:\n  audio:\n    output:\n      volume_percent: {value}\n")
    with pytest.raises(ConfigTypeError, match="volume_percent"):
        load_config(local_path=config_path, environ={})


def test_m4c_vol_001_v12_portable_import() -> None:
    config = AudioOutputConfig()
    assert config.volume_percent == 100
    assert VolumeControlledAudioOutput
