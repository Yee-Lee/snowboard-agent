"""M4-ERR WP7 deterministic actual-backend injection seam regressions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sbd.action.speak.matcha.adapter import MatchaTTSAdapter, TTS_KEY
from sbd.adaptor.errors import AdapterUnavailable
from sbd.adaptor.framed_child import ChildState
from sbd.cognition.llm import LLMBackendError, LLMCleanupUnprovenError
from sbd.cognition.litert_lm.adapter import AdapterState
from sbd.core.audio.alsa.input import AlsaAudioInput
from sbd.core.config.models import GPIOConfig
from sbd.core.fault_injection import (
    DeterministicFaultInjector,
    FaultInjectionError,
)
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.gpio.gpiod.driver import GpiodGPIO
from sbd.perception.listen.whispercpp.adapter import ASR_KEY, WhisperCppASRAdapter
from tests.fakes.m4a import ScriptedChild
from tests.fakes.m4b_llm_child import adapter_fixture
from tests.test_m3_aud_001_002_003_004 import _RawSource, _StreamingDecimator, _alsa_config
from tests.test_m3_gpiod_backend import FakeLoop, _module
from tests.test_m4a_asr_003 import CONFIG as ASR_CONFIG, LOCK as AUDIO_LOCK, _frames
from tests.test_m4a_tts_002 import CONFIG as TTS_CONFIG


def test_m4_err_fault_injector_is_closed_identity_bound_and_one_shot() -> None:
    with pytest.raises(ValueError, match="closed set"):
        DeterministicFaultInjector("private.point", expected_identity={"backend": "x"})
    injector = DeterministicFaultInjector(
        "alsa.capture.read",
        expected_identity={"backend": "alsa.capture", "device": "hw:0,0"},
    )
    assert injector.fire("alsa.playback.drain", {"live": True}) is False
    with pytest.raises(FaultInjectionError, match="differs"):
        injector.fire("alsa.capture.read", {
            "backend": "alsa.capture", "device": "wrong", "live": True,
        })
    actual = {"backend": "alsa.capture", "device": "hw:0,0", "live": True}
    assert injector.fire("alsa.capture.read", actual) is True
    assert dict(injector.evidence.backend_identity) == actual
    assert injector.fire("alsa.capture.read", actual) is False
    assert dict(injector.evidence.backend_identity) == actual


@pytest.mark.asyncio
async def test_m4_err_pv_001_seam_targets_live_alsa_capture() -> None:
    injector = DeterministicFaultInjector(
        "alsa.capture.read",
        expected_identity={"backend": "alsa.capture", "device": "hw:0,0"},
    )
    source = _RawSource([bytes(960 * 8)])
    owner = AlsaAudioInput(
        _alsa_config(),
        source_factory=lambda: source,
        resampler_factory=_StreamingDecimator,
        fault_injector=injector,
    )
    await owner.start()
    with pytest.raises(OSError, match="M4_ERR_INJECTED_ALSA_CAPTURE"):
        await anext(owner.frames())
    assert injector.evidence.backend_identity["live"] is True
    assert source.close_calls == 1
    await owner.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("point", "code", "disposition"),
    (
        ("gpio.button.callback", "BUTTON_CALLBACK_FAILED", "reusable"),
        ("gpio.edge.read", "GPIO_EVENT_READ_FAILED", "unproven"),
    ),
)
async def test_m4_err_pv_002_seam_targets_registered_gpiod_line(
    point: str, code: str, disposition: str,
) -> None:
    requests = []
    injector = DeterministicFaultInjector(
        point,
        expected_identity={"backend": "gpiod", "chip": "/dev/gpiochip0", "pin": 5},
    )
    gpio = GpiodGPIO(
        GPIOConfig(driver="gpiod"),
        gpiod_module=_module(requests),
        fault_injector=injector,
    )
    await gpio.start()
    gpio._loop = FakeLoop(gpio._loop)
    events = []

    async def publish(event) -> None:
        events.append(event)

    gpio.set_fault_publisher(publish)

    async def callback(event) -> None:
        del event

    await gpio.register_input(5, "both", callback)
    await gpio.inject_verification_fault(5)
    assert [(event.code, event.backend_disposition) for event in events] == [
        (code, disposition)
    ]
    assert injector.evidence.backend_identity["request_fd"] >= 0
    assert "M4_ERR_INJECTED" not in repr(events)
    await gpio.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("point", "code"),
    (
        ("asr.inference.rejected", "ASR_INFERENCE_FAILED"),
        ("asr.child.exit", "ASR_PROTOCOL_FAILED"),
    ),
)
async def test_m4_err_pv_003_actual_child_boundary_fault_is_typed(
    point: str, code: str,
) -> None:
    child = ScriptedChild()
    child.pid = 301
    injector = DeterministicFaultInjector(
        point,
        expected_identity={
            "backend": "whispercpp",
            "driver": "whispercpp",
            "artifact_lock_sha256": AUDIO_LOCK.digest,
        },
    )
    adapter = WhisperCppASRAdapter(
        ASR_CONFIG,
        lock=AUDIO_LOCK,
        child_factory=lambda: child,
        fault_injector=injector,
    )
    await adapter.start()
    with pytest.raises(ComponentSystemFault) as raised:
        await adapter.transcribe(_frames())
    assert raised.value.code == code
    assert raised.value.backend is BackendDisposition.REBUILD_REQUIRED
    assert raised.value.recovery_keys == (ASR_KEY,)
    assert child.state is ChildState.DESTROYED
    with pytest.raises(AdapterUnavailable, match="not ready"):
        await adapter.transcribe(_frames())


@pytest.mark.asyncio
async def test_m4_err_pv_004_live_llm_child_exit_reaches_backend_failure() -> None:
    injector = DeterministicFaultInjector(
        "llm.child.exit",
        expected_identity={"backend": "litert_lm"},
    )
    adapter, children, _, _ = adapter_fixture(fault_injector=injector)
    await adapter.start()
    await adapter.open_conversation("session", 1)
    snapshot = await adapter.measure("session", 1, "你好")
    with pytest.raises(LLMBackendError, match="M4_ERR_INJECTED_LLM_CHILD_EXIT"):
        await adapter.generate(snapshot, "你好")
    assert children[0].terminated >= 1
    assert adapter.state is AdapterState.DESTROYED
    assert injector.evidence.backend_identity["pid"] == 101


@pytest.mark.asyncio
async def test_m4_err_pv_004_cleanup_proof_failure_is_typed_unproven() -> None:
    injector = DeterministicFaultInjector(
        "llm.cleanup.unproven",
        expected_identity={"backend": "litert_lm"},
    )
    adapter, _, _, _ = adapter_fixture(fault_injector=injector)
    await adapter.start()
    await adapter.open_conversation("session", 1)
    with pytest.raises(ComponentSystemFault) as raised:
        await adapter.control.close_conversation("session", 1, "session_end")
    assert raised.value.code == "LLM_CLEANUP_UNPROVEN"
    assert raised.value.backend is BackendDisposition.UNPROVEN
    assert raised.value.recovery_keys == ("backend.cognition.reasoner.llm",)
    assert isinstance(raised.value.__cause__, LLMCleanupUnprovenError)
    assert adapter.state is AdapterState.DESTROYED


@pytest.mark.asyncio
async def test_m4_err_pv_005_live_tts_child_exit_is_typed_and_blocks_admission() -> None:
    child = ScriptedChild()
    child.pid = 501
    injector = DeterministicFaultInjector(
        "tts.child.exit",
        expected_identity={
            "backend": "matcha",
            "driver": "sherpa_matcha",
            "artifact_lock_sha256": AUDIO_LOCK.digest,
        },
    )
    adapter = MatchaTTSAdapter(
        TTS_CONFIG,
        lock=AUDIO_LOCK,
        child_factory=lambda: child,
        fault_injector=injector,
    )
    await adapter.start()
    with pytest.raises(ComponentSystemFault) as raised:
        _ = [chunk async for chunk in adapter.synthesize("測試")]
    assert raised.value.code == "TTS_PROTOCOL_FAILED"
    assert raised.value.backend is BackendDisposition.REBUILD_REQUIRED
    assert raised.value.recovery_keys == (TTS_KEY,)
    assert child.state is ChildState.DESTROYED
    with pytest.raises(AdapterUnavailable, match="not ready"):
        _ = [chunk async for chunk in adapter.synthesize("下一次")]
