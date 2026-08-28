"""M4A-TTS-001 — fixed Matcha generation profile and PCM handoff."""

from __future__ import annotations

import asyncio
import hashlib
import os
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from sbd.action.speak.matcha.adapter import MatchaTTSAdapter
from sbd.action.speak.matcha import worker as matcha_worker
from sbd.action.speak.matcha.worker import float_samples_to_s16le
from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.config.models import TTSConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted
from sbd.action.speak import Speak
from tests.fakes.m4a import ScriptedChild
import pytest
from sbd.adaptor.framed_child import AudioProtocolError, MAX_PCM_BYTES


LOCK = AudioArtifactLock.load(Path(__file__).parent.parent / "requirements/m4a/audio-artifacts.json")
CONFIG = TTSConfig(driver="sherpa_matcha")


def _header(payload: bytes, request_id: int = 1):
    return {
        "protocol": 1, "event": "PCM", "request_id": request_id,
        "sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE",
        "sample_count": len(payload) // 2, "payload_bytes": len(payload),
        "pcm_sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_m4a_tts_001_conversion_oracle_is_clamped_rounded_little_endian_once() -> None:
    payload = float_samples_to_s16le([-2, -1, -0.5, 0, 0.5, 1, 2])
    assert struct.unpack("<7h", payload) == (-32768, -32768, -16384, 0, 16384, 32767, 32767)


def test_m4a_tts_001_actual_worker_invocation_uses_sid_speed_and_one_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int, float]] = []

    class Engine:
        def generate(self, text: str, *, sid: int, speed: float):
            calls.append((text, sid, speed))
            return SimpleNamespace(sample_rate=16000, samples=[-0.5, 0.5])

    conversions = 0
    original = matcha_worker.float_samples_to_s16le

    def convert(samples):
        nonlocal conversions
        conversions += 1
        return original(samples)

    monkeypatch.setattr(matcha_worker, "float_samples_to_s16le", convert)
    payload, latency_ms = matcha_worker.synthesize(Engine(), "private")
    assert calls == [("private", 0, 1.0)]
    assert conversions == 1
    assert struct.unpack("<2h", payload) == (-16384, 16384)
    assert latency_ms >= 0


def test_m4a_tts_001_lazy_generator_pcm_chunks_and_speak_drain_completion() -> None:
    async def run() -> None:
        payload = bytes(index % 256 for index in range(650))
        child = ScriptedChild([_header(payload)], payload=payload)
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        generator = adapter.synthesize("不記錄的測試文字")
        assert child.messages == []
        chunks = [chunk async for chunk in generator]
        assert [len(chunk) for chunk in chunks] == [640, 10]
        assert b"".join(chunks) == payload
        assert child.messages[0][0]["op"] == "GENERATE"
        assert child.messages[0][0]["voice_id"] == "matcha-zh-en-default-sid-0"

        second_child = ScriptedChild([_header(payload)], payload=payload)
        second = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: second_child)
        await second.start()
        bus = EventBus()
        events: list[ActionCompleted] = []
        bus.subscribe(ActionCompleted, events.append)
        output = MockAudioOutput()
        speaker = Speak(tts=second, audio_output=output, bus=bus)
        await speaker.execute("session", 1, 1, {"text": "播放"})
        assert b"".join(output.frames_played) == payload
        assert [(event.kind, event.status) for event in events] == [("speak", "ok")]

    asyncio.run(run())


def test_m4a_tts_001_profile_is_fixed_cpu_two_threads_one_sentence() -> None:
    assert LOCK.profiles["tts"] == {
        "engine": "sherpa-onnx-1.13.5-matcha", "voice_id": "matcha-zh-en-default-sid-0",
        "sid": 0, "speed": 1.0, "provider": "cpu", "threads": 2, "max_sentences": 1,
        "sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE",
    }


def test_m4a_tts_001_product_entry_sets_native_thread_policy_before_imports() -> None:
    environment = os.environ.copy()
    environment["OPENBLAS_NUM_THREADS"] = "8"
    source_root = str(Path(__file__).resolve().parents[1] / "src")
    environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import sbd.main; print(os.environ['OPENBLAS_NUM_THREADS'])",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "1"


def test_m4a_tts_001_actual_worker_builds_fixed_cpu_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class MatchaConfig:
        def __init__(self, **kwargs):
            captured["matcha"] = kwargs

    class ModelConfig:
        def __init__(self, **kwargs):
            captured["model"] = kwargs

    class Config:
        def __init__(self, **kwargs):
            captured["tts"] = kwargs

        def validate(self):
            return True

    class Engine:
        def __init__(self, config):
            captured["engine_config"] = config

    fake = SimpleNamespace(
        OfflineTtsMatchaModelConfig=MatchaConfig,
        OfflineTtsModelConfig=ModelConfig,
        OfflineTtsConfig=Config,
        OfflineTts=Engine,
    )
    monkeypatch.setattr(matcha_worker, "require_runtime_identity", lambda: None)
    monkeypatch.setitem(sys.modules, "sherpa_onnx", fake)
    matcha_worker.load_tts(tmp_path / "model", tmp_path / "vocoder.onnx")
    assert captured["model"]["provider"] == "cpu"
    assert captured["model"]["num_threads"] == 2
    assert captured["tts"]["max_num_sentences"] == 1
    assert captured["matcha"] == {
        "acoustic_model": str(tmp_path / "model" / "model-steps-3.onnx"),
        "vocoder": str(tmp_path / "vocoder.onnx"),
        "lexicon": str(tmp_path / "model" / "lexicon.txt"),
        "tokens": str(tmp_path / "model" / "tokens.txt"),
        "data_dir": str(tmp_path / "model" / "espeak-ng-data"),
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda header: header.__setitem__("sample_rate_hz", 22050),
        lambda header: header.__setitem__("payload_bytes", 0),
        lambda header: header.__setitem__("payload_bytes", 3),
        lambda header: header.__setitem__("payload_bytes", MAX_PCM_BYTES + 2),
        lambda header: header.__setitem__("sample_count", 2),
        lambda header: header.__setitem__("pcm_sha256", "Z" * 64),
        lambda header: header.__setitem__("extra", True),
    ],
)
def test_m4a_tts_001_rejects_malformed_pcm_header_before_yield(mutate) -> None:
    async def run() -> None:
        payload = b"\x00\x00"
        header = _header(payload)
        mutate(header)
        child = ScriptedChild([header], payload=payload)
        adapter = MatchaTTSAdapter(CONFIG, lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        with pytest.raises(AudioProtocolError):
            [chunk async for chunk in adapter.synthesize("private")]
        assert child.force_count == 1

    asyncio.run(run())
