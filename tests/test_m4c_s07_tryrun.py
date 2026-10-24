"""Workstation vertical regression for M4C S07 Display degradation."""

from __future__ import annotations

import asyncio

from sbd.action.rest import Rest
from sbd.action.speak import Speak
from sbd.action.speak.tts import MockTTSAdapter
from sbd.cognition.prompt_builder import ListenProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.display import DisplayArbiter, DisplayHint
from sbd.core.display.session import SessionDisplay
from sbd.core.display.status_bar import StatusBar
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, StateChanged,
)
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager import StateManager
from tests.test_m2_wrk_003 import _validator
from tests.test_m4c_s02_tryrun import _Listen, _ProductLLM


class _DisplayLogger:
    def __init__(self) -> None:
        self.errors: list[tuple[str, dict]] = []

    def error(self, message: str, *, extra: dict) -> None:
        self.errors.append((message, extra))

    def warning(self, *args) -> None:
        pass

    def debug(self, *args) -> None:
        pass


class _FailingDisplay:
    def __init__(self) -> None:
        self.model = None
        self.calls: list[str] = []
        self.failed = False
        self.call_count_at_failure: int | None = None

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def clear(self) -> None:
        self.calls.append("clear")

    def write_pixels(self, value: bytes) -> None:
        assert len(value) == 128 * 128 * 2
        self.calls.append("write_pixels")

    def show(self) -> None:
        self.calls.append("show")
        main = None if self.model is None else self.model.main
        if (
            not self.failed
            and main is not None
            and main.template == "main.text"
            and main.data.get("text") == "天空為什麼是藍色的？"
        ):
            self.failed = True
            self.call_count_at_failure = len(self.calls)
            raise RuntimeError("PRIVATE_DISPLAY_SHOW_FAILURE")

    def size(self) -> tuple[int, int]:
        return (128, 128)


class _Renderer:
    def __init__(self, display: _FailingDisplay) -> None:
        self._display = display

    def validate(self, hint: DisplayHint) -> None:
        assert hint.template in {"status.state", "main.text"}

    def render(self, *, size, model) -> bytes:
        assert size == (128, 128)
        self._display.model = model
        return bytes(128 * 128 * 2)


def test_m4c_display_001_d01_failure_isolated_from_voice_path() -> None:
    async def run() -> None:
        bus = EventBus()
        llm = _ProductLLM()
        audio = MockAudioOutput()
        speak = Speak(
            tts=MockTTSAdapter(), audio_output=audio, bus=bus
        )
        reasoner = Reasoner(
            llm,
            ListenProjector(),
            bus,
            {"listen", "speak"}.__contains__,
            _validator(),
            control=llm,
            streaming_speak=speak,
        )
        catalog = WorkerCatalog()
        catalog.register_perception("listen", _Listen(bus))
        catalog.set_reasoner(reasoner)
        catalog.register_action("speak", speak)
        catalog.register_action("rest", Rest(bus=bus))
        catalog.seal()
        sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=0.001)

        device = _FailingDisplay()
        display_log = _DisplayLogger()
        arbiter = DisplayArbiter(
            device, _Renderer(device), logger=display_log
        )
        status = StatusBar(arbiter, bus)
        session_display = SessionDisplay(arbiter, bus, sm)
        states: list[str] = []
        errors: list[ErrorOccurred] = []
        actions: list[ActionCompleted] = []
        idle = asyncio.Event()

        async def on_state(event: StateChanged) -> None:
            states.append(event.new)
            if event.new == "IDLE":
                idle.set()

        async def on_error(event: ErrorOccurred) -> None:
            errors.append(event)

        async def on_action(event: ActionCompleted) -> None:
            actions.append(event)

        bus.subscribe(StateChanged, on_state, name="m4c.s07.state")
        bus.subscribe(ErrorOccurred, on_error, name="m4c.s07.error")
        bus.subscribe(ActionCompleted, on_action, name="m4c.s07.action")

        await arbiter.start()
        await status.start()
        await session_display.start()
        await sm.start()
        sm.set_conversation_lifecycle(llm)
        try:
            await bus.publish(ButtonPressed("conversation", 50))
            await asyncio.wait_for(idle.wait(), 2)
            await asyncio.wait_for(sm._inbox.join(), 2)

            assert device.failed is True
            assert device.call_count_at_failure is not None
            assert len(device.calls) == device.call_count_at_failure
            assert arbiter._rendering_enabled is False
            assert len(display_log.errors) == 1
            assert display_log.errors[0][1]["code"] == "DISPLAY_RENDER_DISABLED"
            assert errors == []
            assert "ERROR" not in states
            assert llm.generated == [
                "天空為什麼是藍色的?", "請結束對話。"
            ]
            assert [item.kind for item in actions] == ["speak", "speak", "rest"]
            assert all(item.status == "ok" for item in actions)
            assert len(audio.frames_played) == 2
            assert states[-1] == "IDLE"
            assert sm._session is None and sm._in_flight == {}
            assert arbiter.snapshot().main is None
        finally:
            await sm.stop()
            await session_display.stop()
            await status.stop()
            await arbiter.stop()

    asyncio.run(run())
