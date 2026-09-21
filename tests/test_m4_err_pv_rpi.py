"""M4-ERR same-bytes Raspberry Pi actual-backend fault-injection cases."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import wave
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.speak import Speak
from sbd.action.speak.matcha.adapter import MatchaTTSAdapter, TTS_KEY
from sbd.action.tool import ToolRegistry
from sbd.adaptor.audio_lock import AudioArtifactLock
from sbd.adaptor.errors import AdapterUnavailable
from sbd.adaptor.framed_child import ChildState
from sbd.cognition.litert_lm.adapter import AdapterState, LiteRTLMAdapter
from sbd.cognition.litert_lm.lock import LLMArtifactLock
from sbd.cognition.litert_lm.resource import ProcessResource, SystemResourceSample
from sbd.cognition.llm import LLMBackendError, LLMCleanupUnprovenError
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core._m4b_resource_binding import _pi_temperature, _pi_throttled
from sbd.core.audio.alsa.input import AlsaAudioInput
from sbd.core.audio.alsa.output import AlsaAudioOutput
from sbd.core.candidate_identity import tracked_content_digest
from sbd.core.config import load_config
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, LLMResponse, PerceptionResult
from sbd.core.events import ShutdownRequested, StateChanged
from sbd.core.error_observer import ErrorLoggingObserver
from sbd.core.fault_injection import DeterministicFaultInjector
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.gpio.gpiod.driver import GpiodGPIO
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase
from sbd.core.resource_manager.manager import RecoveryContractViolation
from sbd.core.m1_composition import register_m1_resources
from sbd.main import EXIT_RUNTIME_FATAL, run_app
from sbd.core.logger import SbdJsonFormatter
from sbd.perception.listen import Listen, MockASRAdapter
from sbd.perception.listen.whispercpp.adapter import ASR_KEY, WhisperCppASRAdapter
from tests.test_state_manager import make_sm, start_perception


pytestmark = pytest.mark.rpi
ROOT = Path(__file__).resolve().parents[1]


class _ReadyResource:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class _StablePiSampler:
    """Keep admission deterministic while the adapter authenticates the real child."""

    def __init__(self) -> None:
        self._counter = time.monotonic_ns()

    def _sample(self, child_pid: int) -> SystemResourceSample:
        self._counter += 1
        return SystemResourceSample(
            self._counter,
            (
                ProcessResource(
                    os.getpid(), frozenset({"core", "vad", "asr", "tts"}),
                    1, 1, 1, 0.0, 1,
                ),
                ProcessResource(child_pid, "llm", 1, 1, 1, 0.0, 1),
            ),
            8 * 1024**3,
            4 * 1024**3,
            0,
            0,
            _pi_temperature(),
            _pi_throttled(),
        )

    def sample(self, *, child_pid: int, child_pgid: int) -> SystemResourceSample:
        assert child_pid == child_pgid
        return self._sample(child_pid)

    def rebase_llm_owner(self, *, child_pid: int, child_pgid: int) -> SystemResourceSample:
        return self.sample(child_pid=child_pid, child_pgid=child_pgid)

    @staticmethod
    def validate_sample(sample: SystemResourceSample, previous) -> None:
        del previous
        sample.validate()


def _context(test_id: str):
    assert os.environ["SBD_M4_ERR_TEST_ID"] == test_id
    root = Path(os.environ["SBD_M4_ERR_RUN_ROOT"]).resolve(strict=True)
    binding = json.loads((root / "private/binding.json").read_text(encoding="utf-8"))
    assert binding["run_id"] == os.environ["SBD_M4_ERR_RUN_ID"]
    pending = tuple(binding["pending_new_paths"])
    assert tracked_content_digest(ROOT, pending_new_paths=pending) == binding["content_sha256"]
    config_path = Path(os.environ["SBD_M4_ERR_CONFIG"]).resolve(strict=True)
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == binding["config_sha256"]
    config = load_config(local_path=config_path, dotenv_path=Path(os.devnull), environ={})
    artifact_paths = {
        "asr_lock": config.perception.listen.adapter.artifact_lock_path,
        "llm_lock": config.cognition.llm.artifact_lock_path,
        "llm_profile": config.cognition.llm.product_profile_path,
        "tts_lock": config.action.tts.artifact_lock_path,
    }
    assert all(path is not None for path in artifact_paths.values())
    assert binding["artifact_identity"] == {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in artifact_paths.items()
        if path is not None
    }
    return config


def _record(bus: EventBus, event_type, target: list) -> None:
    async def append(event) -> None:
        target.append(event)

    bus.subscribe(event_type, append)


def _write_product_observation(test_id: str, value: dict[str, object]) -> None:
    root = Path(os.environ["SBD_M4_ERR_RUN_ROOT"]).resolve(strict=True)
    path = root / "private" / test_id / "product-observation.json"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as sink:
        json.dump(value, sink, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sink.write("\n")


class _StructuredLogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.setFormatter(SbdJsonFormatter())
        self.entries: list[dict[str, object]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.entries.append(json.loads(self.format(record)))


def _register_required_workers(
    rm: ResourceManager, *, dependency: str | None = None
) -> None:
    for key, capability in (
        ("worker.perception.listen", "listen"),
        ("worker.cognition.reasoner", None),
        ("worker.action.rest", None),
    ):
        dependencies = (dependency,) if dependency and key == "worker.cognition.reasoner" else ()
        rm.register(ResourceSpec(
            key=key,
            phase=StartPhase.WORKER,
            dependencies=dependencies,
            factory=lambda resolver: _ReadyResource(),
            capability_kind=capability,
        ))


async def _wav_frames(path: Path):
    with wave.open(str(path), "rb") as source:
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getframerate() == 16_000
        while payload := source.readframes(320):
            assert len(payload) == 640
            yield payload


async def _assert_product_exit4(event: ErrorOccurred) -> None:
    class Trigger(_ReadyResource):
        async def arm(self) -> None:
            asyncio.create_task(self._bus.publish(event))

        def __init__(self, bus: EventBus) -> None:
            self._bus = bus

    def composition(rm, bus, config) -> None:
        register_m1_resources(rm, bus, config)
        rm.register(ResourceSpec(
            key="input.m4_err_fatal_probe",
            phase=StartPhase.INPUT_PRODUCER,
            factory=lambda resolver: Trigger(bus),
        ))

    config_path = os.environ["SBD_M4_ERR_CONFIG"]
    product_environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("SBD_M4_ERR_")
    }
    with patch.dict(os.environ, product_environment, clear=True):
        assert await asyncio.wait_for(
            run_app(config_path, composition=composition),
            10,
        ) == EXIT_RUNTIME_FATAL


@pytest.mark.asyncio
async def test_m4_err_pv_001() -> None:
    config = _context("M4-ERR-PV-001")
    audio = config.core.audio
    assert audio.driver == "alsa"
    injector = DeterministicFaultInjector(
        "alsa.capture.read",
        expected_identity={
            "backend": "alsa.capture", "device": audio.input.device,
            "rate": 48_000, "channels": 2, "format": "S32_LE", "period_size": 960,
        },
    )
    owner = AlsaAudioInput(audio, fault_injector=injector)
    bus = EventBus()
    events: list[ErrorOccurred] = []
    _record(bus, ErrorOccurred, events)
    observer = ErrorLoggingObserver(bus)
    capture = _StructuredLogCapture()
    product_logger = logging.getLogger("sbd.error_observer")
    original_level = product_logger.level
    product_logger.addHandler(capture)
    product_logger.setLevel(logging.ERROR)
    await observer.start()
    listen = Listen(audio_input=owner, asr=MockASRAdapter(), bus=bus)
    await owner.start()
    try:
        with pytest.raises(ComponentSystemFault) as raised:
            await listen.perceive("session", 1, 1, 10.0)
        fault = raised.value
        assert (fault.code, fault.backend, fault.recovery_keys) == (
            "AUDIO_CAPTURE_FAILED", BackendDisposition.UNPROVEN, ("core.audio.input",),
        )
        assert len(events) == 1 and events[0].code == "AUDIO_CAPTURE_FAILED"
        assert "M4_ERR_INJECTED_ALSA_CAPTURE" not in repr(events)
        assert len(capture.entries) == 1
        assert capture.entries[0]["code"] == "AUDIO_CAPTURE_FAILED"
        assert "M4_ERR_INJECTED_ALSA_CAPTURE" not in json.dumps(capture.entries)
        assert injector.evidence.backend_identity["live"] is True
        await _assert_product_exit4(events[0])
        _write_product_observation("M4-ERR-PV-001", {
            "event_code": events[0].code,
            "structured_log": capture.entries[0],
            "raw_sentinel_absent": True,
        })
    finally:
        await observer.stop()
        product_logger.removeHandler(capture)
        product_logger.setLevel(original_level)
        await owner.stop()


@pytest.mark.asyncio
async def test_m4_err_pv_002() -> None:
    config = _context("M4-ERR-PV-002")
    pin_name = config.input_sources.button.conversation_pin
    pin = config.core.gpio.pins[pin_name].pin
    observed: list[ErrorOccurred] = []
    states: list[str] = []

    bus, sm, listen, *_ = make_sm(hold_perception=True)
    _record(bus, ErrorOccurred, observed)
    _record(bus, StateChanged, states)
    await start_perception(bus, sm, listen)

    async def callback(event) -> None:
        del event

    for point in ("gpio.button.callback", "gpio.edge.read"):
        injector = DeterministicFaultInjector(
            point,
            expected_identity={
                "backend": "gpiod", "chip": config.core.gpio.chip, "pin": pin,
            },
        )
        gpio = GpiodGPIO(config.core.gpio, fault_injector=injector)
        if point == "gpio.button.callback":
            gpio.set_fault_publisher(bus.publish)
        else:
            async def publish_edge(event) -> None:
                observed.append(event)

            gpio.set_fault_publisher(publish_edge)
        await gpio.start()
        try:
            await gpio.register_input(pin, "both", callback)
            await gpio.inject_verification_fault(pin)
            assert injector.evidence.backend_identity["live"] is True
            if point == "gpio.button.callback":
                # The live driver publishes into the SM inbox; wait for the
                # serial consumer so the observation proves the transition,
                # not merely successful event publication.
                await sm._inbox.join()
        finally:
            await gpio.stop()
    assert [(event.code, event.backend_disposition) for event in observed] == [
        ("BUTTON_CALLBACK_FAILED", "reusable"),
        ("GPIO_EVENT_READ_FAILED", "unproven"),
    ]
    state_names = [event.new for event in states]
    assert state_names.count("ERROR") == 1
    assert "M4_ERR_INJECTED_GPIO" not in repr(observed)
    await _assert_product_exit4(observed[-1])
    if sm._loop_task is not None and not sm._loop_task.done():
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
    await sm.stop()
    _write_product_observation("M4-ERR-PV-002", {
        "event_codes": [event.code for event in observed],
        "error_transition_count": state_names.count("ERROR"),
        "state_transitions": state_names,
    })


async def _run_asr_fault(config, point: str, wav: Path) -> None:
    cfg = config.perception.listen.adapter
    assert cfg.artifact_lock_path is not None
    lock = AudioArtifactLock.load(cfg.artifact_lock_path)
    injector = DeterministicFaultInjector(
        point,
        expected_identity={
            "backend": "whispercpp", "driver": cfg.driver,
            "artifact_lock_sha256": lock.digest,
        },
    )
    adapter = WhisperCppASRAdapter(cfg, lock=lock, fault_injector=injector)
    bus = EventBus()
    rm = ResourceManager(config, bus)
    rm.register(ResourceSpec(
        key=ASR_KEY, phase=StartPhase.BACKEND, factory=lambda resolver: adapter,
        recoverable=True, recovery_hook=adapter,
    ))
    _register_required_workers(rm)
    await rm.start()
    try:
        with pytest.raises(ComponentSystemFault) as raised:
            await adapter.transcribe(_wav_frames(wav))
        expected = (
            "ASR_INFERENCE_FAILED" if point == "asr.inference.rejected"
            else "ASR_PROTOCOL_FAILED"
        )
        assert raised.value.code == expected
        assert raised.value.backend is BackendDisposition.REBUILD_REQUIRED
        assert raised.value.recovery_keys == (ASR_KEY,)
        assert adapter.state is ChildState.DESTROYED
        report = await adapter.force_abort()
        assert report.destroyed_backends == (ASR_KEY,)
        ticket = rm.begin_recovery(report.destroyed_backends)
        assert rm.recovery_ready() is False
        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True and adapter.ready_for_next
        result = await adapter.transcribe(_wav_frames(wav))
        assert result.text.strip()
    finally:
        await rm.stop_all()


@pytest.mark.asyncio
async def test_m4_err_pv_003() -> None:
    config = _context("M4-ERR-PV-003")
    wav = Path(os.environ["SBD_M4_ERR_ASR_WAV"]).resolve(strict=True)
    await _run_asr_fault(config, "asr.inference.rejected", wav)
    await _run_asr_fault(config, "asr.child.exit", wav)


def _llm_lock(config):
    cfg = config.cognition.llm
    assert cfg.artifact_lock_path is not None
    lock = LLMArtifactLock.load(cfg.artifact_lock_path, repo_root=ROOT)
    profile = lock.verify_config_paths(cfg)
    return replace(lock, identity=lock.ready_identity(profile), product_profile=profile)


def _validator() -> ActionPayloadValidator:
    tools = ToolRegistry()
    tools.seal()
    return ActionPayloadValidator(tools=tools)


@pytest.mark.asyncio
async def test_m4_err_pv_004() -> None:
    config = _context("M4-ERR-PV-004")
    cfg = config.cognition.llm
    lock = _llm_lock(config)
    injector = DeterministicFaultInjector(
        "llm.child.exit",
        expected_identity={"backend": "litert_lm", "artifact_lock_sha256": lock.digest},
    )
    bus = EventBus()
    responses: list[LLMResponse] = []
    errors: list[ErrorOccurred] = []
    _record(bus, LLMResponse, responses)
    _record(bus, ErrorOccurred, errors)
    rm = ResourceManager(config, bus)
    adapter = LiteRTLMAdapter(
        cfg, lock=lock, schedule_recovery=rm.begin_recovery,
        wait_recovery=rm.wait_recovery, resource_sampler=_StablePiSampler(),
        fault_injector=injector,
    )
    rm.register(ResourceSpec(
        key="backend.cognition.reasoner.llm", phase=StartPhase.BACKEND,
        factory=lambda resolver: adapter, recoverable=True, recovery_hook=adapter,
    ))
    _register_required_workers(rm, dependency="backend.cognition.reasoner.llm")
    await rm.start()
    reasoner = Reasoner(
        adapter, ListenProjector(), bus, {"listen", "speak"}.__contains__, _validator()
    )
    try:
        await adapter.open_conversation("session", 1)
        perception = PerceptionResult(
            "listen", "ok", "請簡短介紹台灣。", session_id="session", turn_id=1,
        )
        with pytest.raises(ComponentSystemFault) as raised:
            await reasoner.reason(
                "session", 1, 1, (perception,), (), conversation_generation=1,
            )
        assert raised.value.code == "LLM_BACKEND_FAILED"
        assert raised.value.backend is BackendDisposition.REBUILD_REQUIRED
        assert adapter.state is AdapterState.DESTROYED
        report = await adapter.force_abort()
        ticket = rm.begin_recovery(report.destroyed_backends)
        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True and adapter.state is AdapterState.ENGINE_READY
        await adapter.open_conversation("session", 2)
        await reasoner.reason(
            "session", 2, 2,
            (replace(perception, turn_id=2),), (), conversation_generation=2,
        )
        assert len(responses) == 1 and len(errors) == 1
    finally:
        await rm.stop_all()

    cleanup_injector = DeterministicFaultInjector(
        "llm.cleanup.unproven",
        expected_identity={"backend": "litert_lm", "artifact_lock_sha256": lock.digest},
    )
    cleanup = LiteRTLMAdapter(
        cfg, lock=lock, schedule_recovery=lambda keys: None,
        wait_recovery=lambda ticket: None, resource_sampler=_StablePiSampler(),
        fault_injector=cleanup_injector,
    )
    await cleanup.start()
    try:
        await cleanup.open_conversation("cleanup", 1)
        with pytest.raises(ComponentSystemFault) as cleanup_fault:
            await cleanup.control.close_conversation("cleanup", 1, "session_end")
        assert cleanup_fault.value.code == "LLM_CLEANUP_UNPROVEN"
        assert cleanup_fault.value.backend is BackendDisposition.UNPROVEN
        assert cleanup_fault.value.recovery_keys == (
            "backend.cognition.reasoner.llm",
        )
        assert isinstance(cleanup_fault.value.__cause__, LLMCleanupUnprovenError)
        assert cleanup.state is AdapterState.DESTROYED
        await _assert_product_exit4(cleanup_fault.value.to_event())
    finally:
        await cleanup.force_abort()


@pytest.mark.asyncio
async def test_m4_err_pv_005() -> None:
    config = _context("M4-ERR-PV-005")
    cfg = config.action.tts
    assert cfg.artifact_lock_path is not None
    lock = AudioArtifactLock.load(cfg.artifact_lock_path)
    injector = DeterministicFaultInjector(
        "tts.child.exit",
        expected_identity={
            "backend": "matcha", "driver": cfg.driver,
            "artifact_lock_sha256": lock.digest,
        },
    )
    adapter = MatchaTTSAdapter(cfg, lock=lock, fault_injector=injector)
    bus = EventBus()
    rm = ResourceManager(config, bus)
    rm.register(ResourceSpec(
        key=TTS_KEY, phase=StartPhase.BACKEND, factory=lambda resolver: adapter,
        recoverable=True, recovery_hook=adapter,
    ))
    _register_required_workers(rm)
    await rm.start()
    output = None
    try:
        with pytest.raises(ComponentSystemFault) as raised:
            _ = [chunk async for chunk in adapter.synthesize("這是錯誤處理驗證。")]
        assert raised.value.code == "TTS_PROTOCOL_FAILED"
        assert raised.value.backend is BackendDisposition.REBUILD_REQUIRED
        with pytest.raises(AdapterUnavailable):
            _ = [chunk async for chunk in adapter.synthesize("不可提早接收。")]
        report = await adapter.force_abort()
        ticket = rm.begin_recovery(report.destroyed_backends)
        await rm.wait_recovery(ticket)
        assert rm.recovery_ready() is True and adapter.state is ChildState.READY
        assert b"".join([chunk async for chunk in adapter.synthesize("重建完成。")])

        drain = DeterministicFaultInjector(
            "alsa.playback.drain",
            expected_identity={
                "backend": "alsa.playback", "device": config.core.audio.output.device,
                "rate": 48_000, "channels": 2, "format": "S32_LE", "period_size": 960,
            },
        )
        output = AlsaAudioOutput(config.core.audio, fault_injector=drain)
        events: list[ErrorOccurred] = []
        _record(bus, ErrorOccurred, events)
        speaker = Speak(tts=adapter, audio_output=output, bus=bus)
        await output.start()
        with pytest.raises(ComponentSystemFault) as playback:
            await speaker.execute(
                "session", 1, 1, {"text": "這是播放錯誤驗證。"},
            )
        assert playback.value.code == "AUDIO_PLAYBACK_FAILED"
        assert playback.value.backend is BackendDisposition.UNPROVEN
        assert playback.value.recovery_keys == ("core.audio.output",)
        assert len(events) == 1 and "M4_ERR_INJECTED_ALSA_DRAIN" not in repr(events)
        with pytest.raises(RecoveryContractViolation):
            ResourceManager(config, EventBus()).begin_recovery(
                playback.value.recovery_keys
            )
        await _assert_product_exit4(events[0])
    finally:
        if output is not None:
            await output.stop()
        await rm.stop_all()
