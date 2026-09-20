"""Lazy target-only construction of Accepted Core TTS and ALSA objects."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Callable

from poc_llm.m4c_ss.target_backend import CoreSpeechBackend


CORE_PRODUCT_SHA = "f87cfa50b9c9415430973076a59c6b1961228090"
BINDING_FORMAT = "m4c-ss-target-binding-v1"
PLAYBACK_DEVICE = "hw:CARD=sndrpigooglevoi,DEV=0"


class TargetBindingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TargetBinding:
    tts_model_path: Path
    tts_vocoder_path: Path
    tts_runtime_python: Path
    audio_artifact_lock_path: Path


def load_target_binding(path: Path, *, expected_core_sha: str = CORE_PRODUCT_SHA) -> TargetBinding:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise TargetBindingError("TARGET_BINDING_INVALID")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TargetBindingError("TARGET_BINDING_INVALID") from error
    fields = {
        "format", "core_source_sha", "tts_model_path", "tts_vocoder_path",
        "tts_runtime_python", "audio_artifact_lock_path",
    }
    if type(value) is not dict or set(value) != fields:
        raise TargetBindingError("TARGET_BINDING_INVALID")
    if value["format"] != BINDING_FORMAT or value["core_source_sha"] != expected_core_sha:
        raise TargetBindingError("TARGET_BINDING_IDENTITY_MISMATCH")
    paths = {}
    for name in fields - {"format", "core_source_sha"}:
        raw = value[name]
        if type(raw) is not str or not raw:
            raise TargetBindingError("TARGET_BINDING_INVALID")
        item = Path(raw)
        if not item.is_absolute():
            raise TargetBindingError("TARGET_BINDING_PATH_INVALID")
        paths[name] = item
    return TargetBinding(**paths)


def materialize_core_backend(
    binding: TargetBinding,
    *,
    observe: Callable[[str, int], None],
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> CoreSpeechBackend:
    """Import Core only after offline identity preflight and build fresh owners."""

    try:
        from sbd.action.speak import make_tts_adapter
        from sbd.core.audio.alsa.output import AlsaAudioOutput
        from sbd.core.config.models import (
            AudioConfig, AudioFormatConfig, AudioOutputConfig, TTSConfig,
        )
    except ImportError as error:
        raise TargetBindingError("ACCEPTED_CORE_IMPORT_UNAVAILABLE") from error

    tts_config = TTSConfig(
        driver="sherpa_matcha",
        engine_name="sherpa-onnx-1.13.5-matcha",
        model_path=binding.tts_model_path,
        vocoder_path=binding.tts_vocoder_path,
        runtime_python=binding.tts_runtime_python,
        artifact_lock_path=binding.audio_artifact_lock_path,
        voice_id="matcha-zh-en-default-sid-0",
        native_sample_rate=16_000,
        native_channels=1,
        native_sample_format="s16_le",
        child_ready_timeout_seconds=120.0,
        child_terminate_timeout_seconds=2.0,
        child_kill_wait_timeout_seconds=1.0,
    )
    stream = AudioFormatConfig(sample_rate=16_000, channels=1, sample_format="s16_le")
    native = AudioFormatConfig(sample_rate=48_000, channels=2, sample_format="s32_le")
    audio_config = AudioConfig(
        driver="alsa",
        output=AudioOutputConfig(
            stream_format=stream,
            device=PLAYBACK_DEVICE,
            native_format=native,
        ),
    )

    class ObservedAlsaAudioOutput(AlsaAudioOutput):
        """POC-private exact write observer; no Core source modification."""

        def __init__(self) -> None:
            super().__init__(audio_config)
            self._m4c_first_write_pending = False

        async def play(self, pcm):
            self._m4c_first_write_pending = True
            return await super().play(pcm)

        def _write_worker(self, chunk: bytes) -> None:
            stamp = clock_ns()
            super()._write_worker(chunk)
            if self._m4c_first_write_pending:
                self._m4c_first_write_pending = False
                observe("audio_first_write", stamp)

    tts = make_tts_adapter(tts_config)
    audio_output = ObservedAlsaAudioOutput()
    return CoreSpeechBackend(
        tts=tts,
        audio_output=audio_output,
        observe=observe,
        clock_ns=clock_ns,
    )
