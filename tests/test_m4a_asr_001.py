"""M4A-ASR-001 — 640-byte stream, fixed endpoint, and transcript mapping."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterError
from sbd.core.config.models import ASRConfig
from sbd.perception.listen.whispercpp.adapter import WhisperCppASRAdapter
from sbd.perception.listen.whispercpp.supervisor import (
    EndpointDetector,
    FRAME_BYTES,
    PRE_SPEECH_FRAMES,
    StreamingEndpoint,
)
from sbd.perception.listen.whispercpp import supervisor as supervisor_module
from tests.fakes.m4a import ScriptedChild, asr_ack, asr_endpoint, asr_result


LOCK = AudioArtifactLock.load(Path(__file__).parent.parent / "requirements/m4a/audio-artifacts.json")


def _config() -> ASRConfig:
    return ASRConfig(driver="whispercpp", engine_name="whisper.cpp-1.9.2", language="zh-TW", dsp_profile="silero-6.2.1-endpoint-v1", decoder_profile="p0-greedy-best-of-1")


def test_m4a_asr_001_stream_credit_endpoint_stops_pull_and_maps_result() -> None:
    async def run() -> None:
        child = ScriptedChild([asr_ack(1, 0), asr_endpoint(1), asr_result(1, "你好")])
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()
        pulls = 0

        async def frames():
            nonlocal pulls
            for _ in range(3):
                pulls += 1
                yield b"\x00" * 640

        result = await adapter.transcribe(frames())
        assert (result.text, result.language) == ("你好", "zh-TW")
        assert pulls == 2
        sent = [message for message, _ in child.messages]
        assert [item["op"] for item in sent] == ["BEGIN", "FRAME", "FRAME"]
        assert [item.get("sequence") for item in sent[1:]] == [0, 1]
        assert all(len(payload) == 640 for _, payload in child.messages[1:])

    asyncio.run(run())


@pytest.mark.parametrize("size", [639, 641])
def test_m4a_asr_001_wrong_frame_rejected_before_any_child_message(size: int) -> None:
    async def run() -> None:
        child = ScriptedChild()
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def frames():
            yield b"x" * size

        with pytest.raises(AdapterError, match="640"):
            await adapter.transcribe(frames())
        assert child.messages == []
        assert child.request_id == 0

    asyncio.run(run())


def test_m4a_asr_001_sequence_gap_is_protocol_failure_and_destroys_child() -> None:
    async def run() -> None:
        child = ScriptedChild([asr_ack(1, 1)])
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def frames():
            yield b"\x00" * 640

        with pytest.raises(AdapterError, match="sequence"):
            await adapter.transcribe(frames())
        assert child.force_count == 1

    asyncio.run(run())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda event: event.__setitem__("captured_frames", 2),
        lambda event: event.__setitem__("bounded_samples", 321),
        lambda event: event.__setitem__("bounded_pcm_sha256", "0" * 64),
    ],
)
def test_m4a_asr_001_endpoint_count_or_bounded_hash_mismatch_destroys_child(
    mutate,
) -> None:
    async def run() -> None:
        endpoint = asr_endpoint(1, 1)
        mutate(endpoint)
        child = ScriptedChild([endpoint])
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def frames():
            yield b"\x00" * 640

        with pytest.raises(AdapterError):
            await adapter.transcribe(frames())
        assert child.force_count == 1

    asyncio.run(run())


def test_m4a_asr_001_invalid_later_frame_destroys_inflight_child() -> None:
    async def run() -> None:
        child = ScriptedChild([asr_ack(1, 0)])
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def frames():
            yield b"\x00" * 640
            yield b"\x00" * 639

        with pytest.raises(AdapterError, match="640"):
            await adapter.transcribe(frames())
        assert child.force_count == 1

    asyncio.run(run())


def test_m4a_asr_001_fixed_startup_window_hysteresis_and_padding_boundaries() -> None:
    calls: list[int] = []
    stream = StreamingEndpoint(lambda window: calls.append(len(window)) or 0.0)
    for _ in range(8):
        assert not stream.add_frame(b"\x00" * 640)
    assert calls == []
    stream.add_frame(b"\x00" * 640)
    stream.add_frame(b"\x00" * 640)
    assert calls == [1024]

    rejected = EndpointDetector()
    rejected.observe(0.5, 0)
    rejected.observe(0.0, 249)
    rejected.observe(0.0, 749)
    assert rejected.speech_end_ms is None

    accepted = EndpointDetector()
    accepted.observe(0.5, 0)
    accepted.observe(0.0, 250)
    accepted.observe(0.0, 749)
    assert accepted.speech_end_ms is None
    accepted.observe(0.0, 750)
    assert accepted.speech_end_ms == 250
    assert not accepted.endpoint(849)
    assert accepted.endpoint(850)
    assert accepted.bounds(850) == (0, 850)

    assert LOCK.profiles["vad"] == {
        "engine": "silero-6.2.1-endpoint-v1", "provider": "CPUExecutionProvider",
        "intra_threads": 1, "inter_threads": 1, "window_samples": 512,
        "context_samples": 64, "positive_threshold": 0.5, "negative_threshold": 0.35,
        "startup_mask_ms": 160, "minimum_speech_ms": 250, "end_silence_ms": 500,
        "pre_padding_ms": 500, "post_padding_ms": 600,
    }
    assert LOCK.profiles["asr"]["threads"] == 4
    assert LOCK.profiles["asr"]["strategy"] == "greedy"
    assert LOCK.profiles["asr"]["best_of"] == 1
    assert LOCK.profiles["asr"]["temperature"] == 0
    assert not any(LOCK.profiles["asr"][field] for field in ("timestamps", "translate", "internal_vad", "previous_text"))


def test_m4a_asr_001_pre_speech_ring_is_exactly_25_frames() -> None:
    calls = 0

    def probability(window: bytes) -> float:
        nonlocal calls
        assert len(window) == 1024
        calls += 1
        # With the fixed startup/window schedule, call 11 consumes frame 26.
        return 1.0 if calls == 11 else 0.0

    stream = StreamingEndpoint(probability)
    for sequence in range(PRE_SPEECH_FRAMES):
        frame = sequence.to_bytes(2, "little") * 320
        assert not stream.add_frame(frame)
    assert stream.captured_frames == 25
    assert stream.retained_frames == PRE_SPEECH_FRAMES

    trigger = PRE_SPEECH_FRAMES.to_bytes(2, "little") * 320
    assert not stream.add_frame(trigger)
    assert stream.detector.triggered is True
    assert stream.retained_frames == PRE_SPEECH_FRAMES + 1
    assert bytes(stream.pcm[:FRAME_BYTES]) == b"\x00" * FRAME_BYTES


def test_m4a_asr_001_native_worker_wrapper_uses_fixed_decoder_and_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(pid=1234, stdin=None, stdout=None)

    monkeypatch.setattr(supervisor_module.subprocess, "Popen", popen)
    monkeypatch.setattr(
        supervisor_module.NativeWorker,
        "_line",
        lambda self, timeout: "READY\t1.9.2\t0\t1234",
    )
    worker = supervisor_module.NativeWorker(
        tmp_path / "worker", tmp_path / "model", tmp_path,
    )
    try:
        argv, kwargs = calls[0]
        assert argv == [
            str(tmp_path / "worker"), "--model", str(tmp_path / "model"),
            "--threads", "4", "--decoder", "greedy", "--initial-prompt",
            supervisor_module.PROMPT,
        ]
        assert kwargs["start_new_session"] is False
        assert hashlib.sha256(supervisor_module.PROMPT.encode()).hexdigest() == LOCK.profiles["asr"]["prompt_sha256"]
    finally:
        worker._stderr.close()
