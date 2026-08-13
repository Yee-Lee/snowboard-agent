"""M3 DisplayArbiter contract tests."""

from __future__ import annotations

import asyncio
import threading

import pytest

from sbd.core.config.models import DisplayConfig
from sbd.core.display import DisplayArbiter, DisplayHint, RenderModel, UnknownDisplaySlot
from sbd.core.display.mock import MockDisplay
from sbd.core.display.null import NullDisplay
from sbd.core.display.status_bar import StatusBar
from sbd.core.event_bus import EventBus


class RendererSpy:
    def __init__(self) -> None:
        self.models: list[RenderModel] = []

    def validate(self, hint: DisplayHint) -> None:
        if hint.template == "unknown":
            raise ValueError("unknown")

    def render(self, *, size, model) -> bytes:
        self.models.append(model)
        return bytes(size[0] * size[1] * 2)


def _run(coro):
    return asyncio.run(coro)


def test_m3_arb_001() -> None:
    async def scenario():
        device, renderer = MockDisplay(DisplayConfig()), RendererSpy()
        arbiter = DisplayArbiter(device, renderer)
        await arbiter.start()
        device.calls.clear()
        arbiter.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
        assert device.calls == ["clear", "write_pixels", "show"]
        arbiter.write_main(DisplayHint("main.text", {"text": "before"}))
        assert arbiter.request_fullscreen("owner", DisplayHint("fullscreen.blank"))
        shows = device.calls.count("show")
        arbiter.write_main(DisplayHint("main.text", {"text": "during"}))
        assert device.calls.count("show") == shows
        assert arbiter.snapshot().main.data["text"] == "during"
    _run(scenario())


def test_m3_arb_002() -> None:
    async def scenario():
        arbiter = DisplayArbiter(MockDisplay(DisplayConfig()), RendererSpy())
        await arbiter.start()
        assert arbiter.request_fullscreen("a", DisplayHint("fullscreen.blank"))
        assert not arbiter.request_fullscreen("b", DisplayHint("fullscreen.blank"))
        arbiter.release_fullscreen("b")
        assert arbiter.snapshot().fullscreen is not None
        assert arbiter.request_fullscreen("a", DisplayHint("fullscreen.blank"))
        arbiter.release_fullscreen("a")
        assert arbiter.snapshot().fullscreen is None
        assert arbiter.request_fullscreen("b", DisplayHint("fullscreen.blank"))
    _run(scenario())


def test_m3_arb_003() -> None:
    async def scenario():
        renderer = RendererSpy()
        arbiter = DisplayArbiter(NullDisplay(), renderer)
        await arbiter.start()
        arbiter.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
        assert arbiter.request_fullscreen("a", DisplayHint("fullscreen.blank"))
        arbiter.release_fullscreen("b")
        assert arbiter.request_fullscreen("a", DisplayHint("fullscreen.blank"))
        assert renderer.models == []
    _run(scenario())


def test_m3_arb_004() -> None:
    class FailingDisplay(MockDisplay):
        def show(self):
            super().show()
            raise OSError("fixture failure")
    async def scenario():
        device = FailingDisplay(DisplayConfig())
        arbiter = DisplayArbiter(device, RendererSpy())
        await arbiter.start()
        count = device.calls.count("show")
        arbiter.write_main(DisplayHint("main.text", {"text": "still saved"}))
        assert device.calls.count("show") == count
        assert arbiter.snapshot().main.data["text"] == "still saved"
    _run(scenario())


def test_m3_arb_005() -> None:
    async def scenario():
        device = MockDisplay(DisplayConfig())
        arbiter = DisplayArbiter(device, RendererSpy())
        await arbiter.start()
        await arbiter.stop()
        calls = tuple(device.calls)
        await arbiter.stop()
        arbiter.write_main(DisplayHint("main.text", {"text": "late"}))
        assert tuple(device.calls) == calls
        assert device._started is False
    _run(scenario())


def test_m3_arb_006() -> None:
    async def scenario():
        arbiter = DisplayArbiter(MockDisplay(DisplayConfig()), RendererSpy())
        await arbiter.start()
        with pytest.raises(UnknownDisplaySlot):
            arbiter.write_status_slot("unknown", None)
        status = StatusBar(arbiter, EventBus())
        await status.start()
        assert arbiter.snapshot().status_slots[0][1].data["state"] == "IDLE"
        await status.stop()
    _run(scenario())


def test_m3_arb_007() -> None:
    async def scenario():
        arbiter = DisplayArbiter(MockDisplay(DisplayConfig()), RendererSpy())
        await arbiter.start()
        errors = []
        thread = threading.Thread(
            target=lambda: _capture(errors, lambda: arbiter.write_main(None))
        )
        thread.start()
        thread.join()
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)
    _run(scenario())


def _capture(errors, callback):
    try:
        callback()
    except Exception as exc:
        errors.append(exc)
