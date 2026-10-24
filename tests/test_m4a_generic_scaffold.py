"""M4a generic ASR/TTS scaffold tests."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.action.speak import NullTTSAdapter, Speak, make_tts_adapter
from sbd.core.audio.mock import MockAudioInput, MockAudioOutput
from sbd.core.audio.null import NullAudioInput
from sbd.core.config import ConfigValueError, load_config
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import ASRConfig, TTSConfig
from sbd.core.config.validate import validate_config
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, PerceptionResult
from sbd.perception.listen import Listen, NullASRAdapter, make_asr_adapter


def _config_with(**changes):
    return replace(DEFAULT_CONFIG, **changes)


# ASR-NULL-001
def test_asr_null_001_transcribe_drains_frames_and_returns_empty_result() -> None:
    async def run() -> None:
        audio = MockAudioInput(frames=(b"first", b"second"))
        result = await NullASRAdapter().transcribe(audio.frames())
        assert result.text == ""
        reopened = audio.frames()
        await reopened.aclose()

    asyncio.run(run())


# ASR-NULL-002
def test_asr_null_002_closing_frames_exits_without_an_orphan_task() -> None:
    async def run() -> None:
        audio = NullAudioInput()
        frames = audio.frames()
        task = asyncio.create_task(NullASRAdapter().transcribe(frames))
        await asyncio.sleep(0)
        await frames.aclose()
        result = await asyncio.wait_for(task, timeout=0.2)
        assert result.text == ""
        assert task.done() and not task.cancelled()

    asyncio.run(run())


# ASR-NULL-003
def test_asr_null_003_listen_with_null_adapter_publishes_timeout() -> None:
    async def run() -> None:
        bus = EventBus()
        events: list[PerceptionResult] = []
        bus.subscribe(PerceptionResult, events.append)
        listener = Listen(audio_input=MockAudioInput(), asr=NullASRAdapter(), bus=bus)
        await listener.perceive("session", 1, 1, 1.0)
        assert [(event.kind, event.status, event.text) for event in events] == [
            ("listen", "timeout", None),
        ]

    asyncio.run(run())


# ASR-NULL-004 / ASR-NULL-005
def test_asr_null_004_005_factory_selects_null_and_rejects_unavailable_driver() -> None:
    assert isinstance(make_asr_adapter(ASRConfig(driver="null")), NullASRAdapter)
    with pytest.raises(ValueError, match="unsupported"):
        make_asr_adapter(ASRConfig(driver="unknown"))  # type: ignore[arg-type]


# TTS-NULL-001
def test_tts_null_001_synthesize_emits_one_silent_audio_frame() -> None:
    async def run() -> None:
        frames = [frame async for frame in NullTTSAdapter().synthesize("hello")]
        assert frames == [b"\x00" * 640]
        assert all(isinstance(frame, bytes) for frame in frames)

    asyncio.run(run())


# TTS-NULL-002
def test_tts_null_002_speak_with_null_adapter_publishes_ok() -> None:
    async def run() -> None:
        bus = EventBus()
        events: list[ActionCompleted] = []
        bus.subscribe(ActionCompleted, events.append)
        output = MockAudioOutput()
        speaker = Speak(tts=NullTTSAdapter(), audio_output=output, bus=bus)
        await speaker.execute("session", 1, 1, {"text": "hello"})
        assert output.frames_played == [b"\x00" * 640]
        assert [(event.kind, event.status) for event in events] == [("speak", "ok")]

    asyncio.run(run())


# TTS-NULL-003 / TTS-NULL-004
def test_tts_null_003_004_factory_selects_null_and_rejects_unavailable_driver() -> None:
    assert isinstance(make_tts_adapter(TTSConfig(driver="null")), NullTTSAdapter)
    with pytest.raises(ValueError, match="unsupported"):
        make_tts_adapter(TTSConfig(driver="unknown"))  # type: ignore[arg-type]


# CFG-ASR-001 / CFG-ASR-002 / CFG-ASR-003
def test_cfg_asr_001_002_003_validate_null_and_future_engine_name_requirements() -> None:
    validate_config(DEFAULT_CONFIG)
    real_without_name = replace(
        DEFAULT_CONFIG.perception,
        listen=replace(
            DEFAULT_CONFIG.perception.listen,
            adapter=ASRConfig(driver="whispercpp"),
        ),
    )
    with pytest.raises(ConfigValueError, match="perception.listen.adapter.engine_name"):
        validate_config(_config_with(perception=real_without_name))
    unknown = replace(
        real_without_name,
        listen=replace(real_without_name.listen, adapter=ASRConfig(driver="real_engine")),  # type: ignore[arg-type]
    )
    with pytest.raises(ConfigValueError, match="driver is unsupported"):
        validate_config(_config_with(perception=unknown))


# CFG-TTS-001 / CFG-TTS-002
def test_cfg_tts_001_002_validate_null_and_future_engine_name_requirements() -> None:
    null_tts = replace(DEFAULT_CONFIG.action, tts=TTSConfig(driver="null"))
    validate_config(_config_with(action=null_tts))
    real_tts = replace(
        DEFAULT_CONFIG.action,
        tts=TTSConfig(driver="sherpa_matcha"),
    )
    with pytest.raises(ConfigValueError, match="action.tts.engine_name"):
        validate_config(_config_with(action=real_tts))


# CFG-EXAMPLE-001
def test_cfg_example_001_loads_complete_m4a_schema_and_resource_timeouts() -> None:
    config = load_config(
        local_path=Path(__file__).parent.parent / "config.example.yaml", environ={},
    )
    assert config.perception.listen.adapter.engine_name is None
    assert config.action.tts.native_sample_format is None
    assert config.resource.startup_timeout_seconds.by_kind[
        "backend.perception.listen.asr"
    ] == 30.0
    assert config.resource.stop_timeout_seconds.by_kind[
        "backend.action.speak.tts"
    ] == 5.0
