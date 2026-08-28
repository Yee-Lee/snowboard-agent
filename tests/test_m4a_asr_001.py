"""M4A-ASR-001 — 640-byte stream, fixed endpoint, and transcript mapping."""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterError, AdapterRejected
from sbd.adaptor.framed_child import ChildState, FramedProcess
from sbd.core.config.models import ASRConfig
from sbd.perception.listen.whispercpp.adapter import WhisperCppASRAdapter
from sbd.perception.listen.whispercpp import adapter as adapter_module
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


def test_m4a_asr_001_finite_input_flushes_bounded_silence_to_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(adapter_module, "EOF_TERMINAL_SILENCE_FRAMES", 2)
        child = ScriptedChild([
            asr_ack(1, 0), asr_ack(1, 1), asr_endpoint(1, 3),
            asr_result(1, "finite"),
        ])
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def finite_frames():
            yield b"\x00" * 640

        result = await adapter.transcribe(finite_frames())
        frame_messages = [item for item in child.messages if item[0].get("op") == "FRAME"]
        assert result.text == "finite"
        assert [item[0]["sequence"] for item in frame_messages] == [0, 1, 2]
        assert all(item[1] == b"\x00" * 640 for item in frame_messages)
        assert child.state is ChildState.READY

    asyncio.run(run())


def test_m4a_asr_001_finite_no_endpoint_cancels_after_exact_flush_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(adapter_module, "EOF_TERMINAL_SILENCE_FRAMES", 2)
        child = ScriptedChild(
            [asr_ack(1, 0), asr_ack(1, 1), asr_ack(1, 2)],
            cancel_events=[{
                "protocol": 1, "event": "CANCELLED", "request_id": 1,
            }],
        )
        adapter = WhisperCppASRAdapter(_config(), lock=LOCK, child_factory=lambda: child)
        await adapter.start()

        async def finite_frames():
            yield b"\x00" * 640

        with pytest.raises(AdapterRejected, match="ended before an endpoint"):
            await adapter.transcribe(finite_frames())
        assert [item[0]["op"] for item in child.messages] == [
            "BEGIN", "FRAME", "FRAME", "FRAME", "CANCEL",
        ]
        assert child.state is ChildState.READY
        assert child.force_count == 0

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["endpoint", "no_endpoint"])
def test_m4a_asr_001_finite_input_converges_through_actual_supervisor_process(
    tmp_path: Path,
    mode: str,
) -> None:
    launcher = tmp_path / "finite-supervisor-fixture.py"
    artifacts = {}
    for name in ("vad", "worker", "model", "lock"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        artifacts[name] = path
    launcher.write_text(
        "import os, sys\n"
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        "from sbd.perception.listen.whispercpp import supervisor as target\n"
        "mode = sys.argv[2]\n"
        "class Silero:\n"
        "    def __init__(self, path): self.calls = 0\n"
        "    def reset(self): self.calls = 0\n"
        "    def probability(self, frame):\n"
        "        self.calls += 1\n"
        "        if mode == 'no_endpoint': return 0.0\n"
        "        return 1.0 if self.calls <= 10 else 0.0\n"
        "class Native:\n"
        "    def __init__(self, *args): self.pid = os.getpid()\n"
        "    def transcribe(self, path): return ('finite fixture', 0.1)\n"
        "    def stop(self): pass\n"
        "    def terminate(self): pass\n"
        f"artifact_root = Path({str(tmp_path)!r})\n"
        "target.parse_args = lambda: SimpleNamespace("
        "vad_model=artifact_root/'vad', asr_binary=artifact_root/'worker', "
        "asr_model=artifact_root/'model', runtime_lock=artifact_root/'lock', "
        "profile_sha256='a'*64, work_dir=Path(sys.argv[1]))\n"
        "target.Silero = Silero\n"
        "target.NativeWorker = Native\n"
        "raise SystemExit(target.main())\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    source_root = str(Path(__file__).resolve().parents[1] / "src")
    environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
    expected_ready = {
        "runtime_lock_sha256": hashlib.sha256(artifacts["lock"].read_bytes()).hexdigest(),
        "vad_model_sha256": hashlib.sha256(artifacts["vad"].read_bytes()).hexdigest(),
        "asr_binary_sha256": hashlib.sha256(artifacts["worker"].read_bytes()).hexdigest(),
        "asr_model_sha256": hashlib.sha256(artifacts["model"].read_bytes()).hexdigest(),
        "profile_sha256": "a" * 64,
    }
    process = FramedProcess(
        argv_builder=lambda workdir: [
            sys.executable, str(launcher), str(workdir), mode,
        ],
        work_root=tmp_path / "work",
        expected_ready=expected_ready,
        ready_timeout=5,
        terminate_timeout=1,
        kill_timeout=1,
        environment=environment,
    )

    async def run() -> None:
        adapter = WhisperCppASRAdapter(
            _config(), lock=LOCK, child_factory=lambda: process,
        )
        await adapter.start()

        async def finite_frames():
            yield b"\x00" * FRAME_BYTES

        try:
            if mode == "endpoint":
                result = await asyncio.wait_for(
                    adapter.transcribe(finite_frames()), timeout=10,
                )
                assert result.text == "finite fixture"
            else:
                with pytest.raises(AdapterRejected, match="ended before an endpoint"):
                    await asyncio.wait_for(
                        adapter.transcribe(finite_frames()), timeout=10,
                    )
            assert adapter.state is ChildState.READY
        finally:
            if adapter.state is ChildState.READY:
                await adapter.stop()
            elif adapter.state is ChildState.BUSY:
                await adapter.force_abort()
        assert adapter.state is ChildState.STOPPED
        assert process.workdir is None

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
