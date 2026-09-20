"""M4-ERR WP3-WP6 component fault-matrix regressions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.speak import MockTTSAdapter, Speak
from sbd.action.tool import ToolRegistry
from sbd.cognition.llm import (
    LLMBackendError,
    LLMCleanupUnprovenError,
    LLMObservationError,
    LLMProtocolError,
    LLMFatalError,
    ReplaceableGenerationFailure,
)
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.config.models import GPIOConfig
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.display.arbiter import DisplayArbiter
from sbd.core.display.hints import DisplayHint
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.faults import BackendDisposition, ComponentSystemFault
from sbd.core.gpio.gpiod.driver import GpiodGPIO
from sbd.core.logger import render_public_fatal
from sbd.perception.listen import ASRResult, Listen, MockASRAdapter
from tests.test_m3_gpiod_backend import FakeLoop, _module
from tests.test_m4b_outcome_001 import ProductLLM, fact


def _validator() -> ActionPayloadValidator:
    tools = ToolRegistry()
    tools.seal()
    return ActionPayloadValidator(tools=tools)


def _record(bus: EventBus, kind, target: list) -> None:
    async def append(event) -> None:
        target.append(event)

    bus.subscribe(kind, append)


class _Audio:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def frames(self):
        error = self.error

        async def generate():
            if error is not None:
                raise error
            yield b"\0" * 640

        return generate()


def _asr_fault(code: str, disposition: BackendDisposition) -> ComponentSystemFault:
    return ComponentSystemFault.create(
        where="perception.listen.asr",
        code=code,
        backend=disposition,
        recovery_keys=("backend.perception.listen.asr",),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fault", "code", "disposition"),
    (
        (_asr_fault("ASR_FRAME_CONTRACT_VIOLATION", BackendDisposition.UNPROVEN),
         "ASR_FRAME_CONTRACT_VIOLATION", "unproven"),
        (_asr_fault("ASR_INFERENCE_FAILED", BackendDisposition.REBUILD_REQUIRED),
         "ASR_INFERENCE_FAILED", "rebuild_required"),
        (_asr_fault("ASR_PROTOCOL_FAILED", BackendDisposition.REBUILD_REQUIRED),
         "ASR_PROTOCOL_FAILED", "rebuild_required"),
    ),
)
async def test_m4_err_pi_005_asr_system_faults_are_not_facts(
    fault: ComponentSystemFault, code: str, disposition: str
) -> None:
    bus = EventBus()
    facts: list[PerceptionResult] = []
    errors: list[ErrorOccurred] = []
    _record(bus, PerceptionResult, facts)
    _record(bus, ErrorOccurred, errors)
    worker = Listen(
        audio_input=_Audio(),
        asr=MockASRAdapter((fault,)),
        bus=bus,
    )
    with pytest.raises(ComponentSystemFault) as raised:
        await worker.perceive("session", 1, 1, 1.0)
    assert raised.value is fault
    assert facts == []
    assert [(event.code, event.backend_disposition) for event in errors] == [
        (code, disposition)
    ]


@pytest.mark.asyncio
async def test_m4_err_pi_005_audio_capture_failure_is_unproven() -> None:
    bus = EventBus()
    errors: list[ErrorOccurred] = []
    _record(bus, ErrorOccurred, errors)
    worker = Listen(audio_input=_Audio(RuntimeError("PRIVATE_ALSA")),
                    asr=MockASRAdapter(), bus=bus)
    with pytest.raises(ComponentSystemFault) as raised:
        await worker.perceive("session", 1, 1, 1.0)
    assert raised.value.code == "AUDIO_CAPTURE_FAILED"
    assert raised.value.__cause__.__cause__.args == ("PRIVATE_ALSA",)
    assert [event.code for event in errors] == ["AUDIO_CAPTURE_FAILED"]
    assert "PRIVATE_ALSA" not in repr(errors)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "code", "disposition"),
    (
        (LLMProtocolError("protocol"), "LLM_PROTOCOL_FAILED", "unproven"),
        (LLMBackendError("backend"), "LLM_BACKEND_FAILED", "rebuild_required"),
        (LLMCleanupUnprovenError("cleanup"), "LLM_CLEANUP_UNPROVEN", "unproven"),
        (LLMObservationError("observer"), "LLM_OBSERVATION_FAILED", "unproven"),
    ),
)
async def test_m4_err_pi_006_llm_typed_fault_matrix(
    error: Exception, code: str, disposition: str
) -> None:
    bus = EventBus()
    responses = []
    faults: list[ErrorOccurred] = []
    from sbd.core.events import LLMResponse

    _record(bus, LLMResponse, responses)
    _record(bus, ErrorOccurred, faults)
    reasoner = Reasoner(
        ProductLLM(result=error),
        ListenProjector(),
        bus,
        {"listen", "speak"}.__contains__,
        _validator(),
    )
    with pytest.raises(ComponentSystemFault) as raised:
        await reasoner.reason(
            "session", 1, 1, (fact(),), (), conversation_generation=1
        )
    assert raised.value.code == code
    assert raised.value.__cause__ is error
    assert responses == []
    assert [(event.code, event.backend_disposition) for event in faults] == [
        (code, disposition)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "problem",
    ("untyped", "fatal", "proof", "semantic", "capability", "unsupported", "generation"),
)
async def test_m4_err_pi_012_executable_reasoner_cause_rows(problem: str) -> None:
    llm = ProductLLM()
    capabilities = {"listen", "speak"}
    perceptions = (fact(),)
    generation = 1
    original: BaseException | None = None
    if problem == "untyped":
        original = ValueError("PRIVATE-OUTPUT-CANARY")
        llm.result = original
    elif problem == "fatal":
        original = LLMFatalError("PRIVATE-OUTPUT-CANARY")
        llm.result = original
    elif problem == "proof":
        original = ReplaceableGenerationFailure("INVALID_SEMANTIC")
        original.request_terminal_proven = False
        llm.result = original
    elif problem == "semantic":
        llm.result = replace(llm.result, text="", end=False, safe_fragments=())
    elif problem == "capability":
        capabilities = {"listen"}
    elif problem == "unsupported":
        perceptions = (fact(kind="look"),)
    else:
        generation = 2

    bus = EventBus()
    responses = []
    faults: list[ErrorOccurred] = []
    from sbd.core.events import LLMResponse
    _record(bus, LLMResponse, responses)
    _record(bus, ErrorOccurred, faults)
    reasoner = Reasoner(
        llm, ListenProjector(), bus, capabilities.__contains__, _validator(),
    )
    with pytest.raises(LLMFatalError) as caught:
        await reasoner.reason(
            "session", 1, 1, perceptions, (), conversation_generation=generation,
        )
    if original is None:
        assert caught.value.__cause__ is None
    else:
        assert caught.value.__cause__ is original
    assert "PRIVATE-OUTPUT-CANARY" not in render_public_fatal(caught.value)
    assert responses == [] and len(faults) == 1
    if problem in {"capability", "unsupported", "generation"}:
        assert llm.measures == llm.native_sends == []


@pytest.mark.asyncio
async def test_m4_err_pi_007_tts_audio_and_cancellation_paths() -> None:
    from sbd.core.events import ActionCompleted

    bus = EventBus()
    facts: list[ActionCompleted] = []
    faults: list[ErrorOccurred] = []
    _record(bus, ActionCompleted, facts)
    _record(bus, ErrorOccurred, faults)

    tts_fault = ComponentSystemFault.create(
        where="action.speak.tts",
        code="TTS_GENERATION_FAILED",
        backend=BackendDisposition.REBUILD_REQUIRED,
        recovery_keys=("backend.action.speak.tts",),
    )
    tts_failure = Speak(
        tts=MockTTSAdapter(error=tts_fault),
        audio_output=MockAudioOutput(),
        bus=bus,
    )
    with pytest.raises(ComponentSystemFault) as raised:
        await tts_failure.execute("session", 1, 1, {"text": "valid"})
    assert raised.value.code == "TTS_GENERATION_FAILED"

    class BrokenOutput(MockAudioOutput):
        async def play(self, pcm) -> None:
            raise RuntimeError("PRIVATE_ALSA")

    playback_failure = Speak(
        tts=MockTTSAdapter(), audio_output=BrokenOutput(), bus=bus
    )
    with pytest.raises(ComponentSystemFault) as raised:
        await playback_failure.execute("session", 1, 2, {"text": "valid"})
    assert raised.value.code == "AUDIO_PLAYBACK_FAILED"
    assert facts == []
    assert [event.code for event in faults] == [
        "TTS_GENERATION_FAILED", "AUDIO_PLAYBACK_FAILED"
    ]
    assert "PRIVATE_" not in repr(faults)

    blocked_tts = MockTTSAdapter(blocked=True)
    cancelled = Speak(tts=blocked_tts, audio_output=MockAudioOutput(), bus=bus)
    operation = asyncio.create_task(
        cancelled.execute("session", 1, 3, {"text": "valid"})
    )
    await blocked_tts.entered.wait()
    await cancelled.abort()
    await operation
    assert facts == []
    assert len(faults) == 2


@pytest.mark.asyncio
async def test_m4_err_pu_005_success_and_system_fault_never_dual_publish() -> None:
    from sbd.core.events import ActionCompleted, LLMResponse

    bus = EventBus()
    facts: list[object] = []
    faults: list[ErrorOccurred] = []
    for kind in (PerceptionResult, LLMResponse, ActionCompleted):
        _record(bus, kind, facts)
    _record(bus, ErrorOccurred, faults)

    success = Listen(
        audio_input=_Audio(),
        asr=MockASRAdapter((ASRResult("ok"),)),
        bus=bus,
    )
    await success.perceive("session", 1, 1, 1.0)
    assert len(facts) == 1 and faults == []

    fault = _asr_fault("ASR_PROTOCOL_FAILED", BackendDisposition.REBUILD_REQUIRED)
    failed = Listen(
        audio_input=_Audio(),
        asr=MockASRAdapter((fault,)),
        bus=bus,
    )
    with pytest.raises(ComponentSystemFault):
        await failed.perceive("session", 1, 2, 1.0)
    assert len(facts) == 1 and len(faults) == 1
    assert not any(isinstance(event, ActionCompleted) and event.status == "error"
                   for event in facts)


@pytest.mark.asyncio
async def test_m4_err_pi_008_gpio_callback_and_read_faults_are_observable() -> None:
    requests = []
    gpio = GpiodGPIO(GPIOConfig(driver="gpiod"), gpiod_module=_module(requests))
    await gpio.start()
    gpio._loop = FakeLoop(gpio._loop)
    bus = EventBus()
    faults: list[ErrorOccurred] = []
    _record(bus, ErrorOccurred, faults)
    gpio.set_fault_publisher(bus.publish)

    async def broken_callback(event) -> None:
        raise RuntimeError("PRIVATE_CALLBACK")

    await gpio.register_input(5, "both", broken_callback)
    request = requests[-1]
    request.events.append(
        SimpleNamespace(event_type=1, line_offset=5, timestamp_ns=1_000_000_000)
    )
    callback, args = gpio._loop.readers[request.fd]
    callback(*args)
    await asyncio.gather(*tuple(gpio._callback_tasks))
    assert [fault.code for fault in faults] == ["BUTTON_CALLBACK_FAILED"]
    assert "PRIVATE_CALLBACK" not in repr(faults)

    def fail_read():
        raise RuntimeError("PRIVATE_GPIO")

    request.read_edge_events = fail_read
    callback(*args)
    await asyncio.gather(*tuple(gpio._callback_tasks))
    assert [fault.code for fault in faults] == [
        "BUTTON_CALLBACK_FAILED", "GPIO_EVENT_READ_FAILED"
    ]
    await gpio.stop()


@pytest.mark.asyncio
async def test_m4_err_pi_009_display_disables_once_and_subsequent_writes_noop() -> None:
    class Device:
        def __init__(self) -> None:
            self.show_calls = 0

        def size(self):
            return (1, 1)

        def clear(self):
            pass

        def write_pixels(self, pixels):
            pass

        def show(self):
            self.show_calls += 1
            raise RuntimeError("PRIVATE_DISPLAY")

    class Renderer:
        def validate(self, hint):
            pass

        def render(self, *, size, model):
            return b"\0\0"

    class Logger:
        def __init__(self) -> None:
            self.errors = []

        def error(self, message, *, extra):
            self.errors.append((message, extra))

        def debug(self, *args):
            pass

    device, logger = Device(), Logger()
    arbiter = DisplayArbiter(device, Renderer(), logger=logger)
    await arbiter.start()
    assert device.show_calls == 1
    assert logger.errors == [("Display rendering disabled", {
        "where": "core.display",
        "code": "DISPLAY_RENDER_DISABLED",
        "backend_disposition": "not_applicable",
        "recovery_keys": (),
        "safe_category": "internal",
    })]
    arbiter.write_main(DisplayHint("main.text", {"text": "ignored"}))
    await arbiter.stop()
    assert device.show_calls == 1
    assert len(logger.errors) == 1
