"""M2-WRK-001/002/004 execution, perception, and action worker tests."""

from __future__ import annotations

import asyncio

import pytest

from sbd.action.rest import Rest
from sbd.action.speak import MockTTSAdapter, Speak
from sbd.action.tool import RegisteredTool, Tool, ToolRegistry
from sbd.adaptor.errors import AdapterUnavailable
from sbd.core.audio.mock import MockAudioInput, MockAudioOutput
from sbd.core.camera.mock import MockCamera
from sbd.core.config.models import AudioConfig, CameraConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ErrorOccurred, ExternalMessageArrived, PerceptionResult
from sbd.input_events.external_message import ExternalMessageSource
from sbd.perception.listen import ASRResult, Listen, MockASRAdapter
from sbd.perception.look import Look, MockVisionAdapter, VisionResult
from sbd.perception.read import Read


def _record_bus():
    bus = EventBus()
    facts: list[PerceptionResult | ActionCompleted] = []
    errors: list[ErrorOccurred] = []
    async def fact(event):
        facts.append(event)
    async def error(event):
        errors.append(event)
    bus.subscribe(PerceptionResult, fact)
    bus.subscribe(ActionCompleted, fact)
    bus.subscribe(ErrorOccurred, error)
    return bus, facts, errors


def test_m2_wrk_001_nonreentry_cancel_force_and_exception_cardinality() -> None:
    async def run() -> None:
        bus, facts, errors = _record_bus()
        audio = MockAudioInput(AudioConfig(driver="mock"))
        blocked = MockASRAdapter(blocked=True)
        listen = Listen(audio_input=audio, asr=blocked, bus=bus)
        task = asyncio.create_task(listen.perceive("s", 1, 1, 60.0))
        await blocked.entered.wait()
        with pytest.raises(RuntimeError, match="active call"):
            await listen.perceive("s", 1, 2, 1.0)
        await listen.abort()
        await task
        assert task.done() and not task.cancelled()
        assert facts == [] and errors == []
        assert (await listen.force_abort()).destroyed_backends == ()
        reopened = audio.frames()
        await reopened.aclose()

        blocked_vision = MockVisionAdapter(blocked=True)
        look = Look(
            camera=MockCamera(CameraConfig(driver="mock", width=2, height=2)),
            vision=blocked_vision,
            bus=bus,
        )
        force_task = asyncio.create_task(look.perceive("s", 2, 4, 60.0))
        await blocked_vision.entered.wait()
        assert (await look.force_abort()).destroyed_backends == ()
        await force_task

        failing = Listen(
            audio_input=audio,
            asr=MockASRAdapter((RuntimeError("raw-secret"),)),
            bus=bus,
        )
        with pytest.raises(RuntimeError):
            await failing.perceive("s", 2, 3, 1.0)
        assert facts == []
        assert len(errors) == 1
        assert errors[0].exception_type == "RuntimeError"
        assert "raw-secret" not in errors[0].error

    asyncio.run(run())


def test_m2_wrk_001_fact_is_published_only_after_audio_cleanup() -> None:
    async def run() -> None:
        bus = EventBus()
        audio = MockAudioInput(AudioConfig(driver="mock"))
        facts: list[PerceptionResult] = []
        async def verify_cleanup(event: PerceptionResult) -> None:
            reopened = audio.frames()
            await reopened.aclose()
            facts.append(event)
        bus.subscribe(PerceptionResult, verify_cleanup)
        bus.subscribe(ErrorOccurred, lambda event: asyncio.sleep(0))
        listen = Listen(
            audio_input=audio,
            asr=MockASRAdapter((ASRResult("hello", 0.9, "en"),)),
            bus=bus,
        )
        await listen.perceive("s", 1, 1, 1.0)
        assert len(facts) == 1
        assert facts[0].status == "ok"
        assert facts[0].extra == {"confidence": 0.9, "language": "en"}

    asyncio.run(run())


def test_m2_wrk_002_listen_read_look_success_and_at_most_once() -> None:
    async def run() -> None:
        bus, facts, _ = _record_bus()
        bus.subscribe(ExternalMessageArrived, lambda event: asyncio.sleep(0))
        listen = Listen(
            audio_input=MockAudioInput(AudioConfig(driver="mock")),
            asr=MockASRAdapter((ASRResult("heard"),)),
            bus=bus,
        )
        look = Look(
            camera=MockCamera(CameraConfig(driver="mock", width=2, height=2)),
            vision=MockVisionAdapter((VisionResult("seen", {"objects": 1}),)),
            bus=bus,
        )
        source = ExternalMessageSource(bus=bus)
        await source.start()
        first = await source.ingest(channel="fixture", text="one")
        second = await source.ingest(channel="fixture", text="two")
        await source.control.assign_to_session(first, "s")
        await source.control.mark_pending(first, "s")
        await source.control.assign_to_session(second, "s")
        await source.control.begin_read("s", 1)
        read = Read(consumer=source.consumer, bus=bus)

        await listen.perceive("s", 1, 1, 1.0)
        await read.perceive("s", 1, 2, 1.0)
        await look.perceive("s", 1, 3, 1.0)
        assert tuple(fact.kind for fact in facts) == ("listen", "read", "look")
        assert facts[1].text == "one\ntwo"
        assert facts[1].extra["message_ids"] == (first, second)
        assert await source.control.pending_ids("s") == ()
        await source.stop()

    asyncio.run(run())


def test_m2_wrk_002_timeout_and_adapter_errors_translate_to_facts() -> None:
    async def run() -> None:
        bus, facts, errors = _record_bus()
        timeout = Listen(
            audio_input=MockAudioInput(AudioConfig(driver="mock")),
            asr=MockASRAdapter(blocked=True),
            bus=bus,
        )
        await timeout.perceive("s", 1, 1, 0.01)
        failed = Look(
            camera=MockCamera(CameraConfig(driver="mock", width=2, height=2)),
            vision=MockVisionAdapter((AdapterUnavailable("unavailable"),)),
            bus=bus,
        )
        await failed.perceive("s", 1, 2, 1.0)
        assert tuple((fact.kind, fact.status) for fact in facts) == (
            ("listen", "timeout"),
            ("look", "error"),
        )
        assert errors == []

    asyncio.run(run())


def _tool_registry(calls: list[dict]) -> ToolRegistry:
    def validate(arguments: dict) -> None:
        if set(arguments) != {"on"}:
            raise ValueError("invalid")
    async def handler(arguments: dict) -> dict:
        calls.append(dict(arguments))
        return {"accepted": True}
    registry = ToolRegistry()
    registry.register(RegisteredTool(
        name="light.set",
        description="fixture",
        input_schema={"type": "object", "properties": {"on": {"type": "boolean"}}, "additionalProperties": False},
        validate=validate,
        handler=handler,
    ))
    registry.seal()
    return registry


def test_m2_wrk_004_speak_tool_rest_success_and_p5_error() -> None:
    async def run() -> None:
        bus, facts, errors = _record_bus()
        output = MockAudioOutput()
        speak = Speak(
            tts=MockTTSAdapter((b"a", b"b")),
            audio_output=output,
            bus=bus,
        )
        calls: list[dict] = []
        tool = Tool(registry=_tool_registry(calls), bus=bus)
        rest = Rest(bus=bus)
        await speak.execute("s", 1, 1, {"text": "hello"})
        await tool.execute("s", 1, 2, {"name": "light.set", "arguments": {"on": True}})
        await rest.execute("s", 1, 3, {})
        assert output.frames_played == [b"a", b"b"]
        assert calls == [{"on": True}]
        assert tuple((fact.kind, fact.status) for fact in facts) == (
            ("speak", "ok"), ("tool", "ok"), ("rest", "ok")
        )

        p5 = Speak(
            tts=MockTTSAdapter(error=AdapterUnavailable("tts unavailable")),
            audio_output=MockAudioOutput(),
            bus=bus,
        )
        await p5.execute("s", 2, 4, {"text": "hello"})
        assert (facts[-1].kind, facts[-1].status) == ("speak", "error")
        assert errors == []

    asyncio.run(run())


def test_m2_wrk_004_cancelled_speak_publishes_no_normal_fact() -> None:
    async def run() -> None:
        bus, facts, errors = _record_bus()
        tts = MockTTSAdapter(blocked=True)
        speak = Speak(tts=tts, audio_output=MockAudioOutput(), bus=bus)
        task = asyncio.create_task(speak.execute("s", 1, 1, {"text": "hello"}))
        await tts.entered.wait()
        await speak.abort()
        await task
        assert facts == [] and errors == []
        assert (await speak.force_abort()).destroyed_backends == ()

    asyncio.run(run())
