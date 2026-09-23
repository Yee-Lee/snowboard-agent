"""M4C-SS-CTRL-001 — bounded B2 streaming-speak controller."""
from __future__ import annotations

import asyncio

import pytest

from sbd.action.speak.streaming import StreamingSpeakControl, StreamingSpeakError
from sbd.core.audio.mock import MockAudioOutput
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted
from sbd.core.lifecycle import ForceAbortReport


class TTS:
    def __init__(self, *, blocked: bool = False) -> None:
        self.texts: list[str] = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        if not blocked:
            self.release.set()
        self.aborts = 0

    async def start(self): pass
    async def stop(self): self.release.set()
    async def abort(self):
        self.aborts += 1
        self.release.set()
    async def force_abort(self):
        self.release.set()
        return ForceAbortReport()

    def synthesize(self, text):
        self.texts.append(text)
        async def frames():
            self.entered.set()
            await self.release.wait()
            yield b"\x01\x00"
        return frames()


def _control(tts=None):
    bus = EventBus()
    events = []
    async def capture(event):
        events.append(event)
    bus.subscribe(ActionCompleted, capture)
    tts = tts or TTS()
    control = StreamingSpeakControl(
        session_id="session", turn_id=1, operation_id="operation",
        tts=tts, audio_output=MockAudioOutput(), bus=bus)
    return control, tts, events


def test_m4c_ss_ctrl_001_c01_single_fragment_one_completion() -> None:
    async def run():
        control, tts, events = _control()
        await control.feed("session", 1, 0, "你好。")
        control.start()
        await control.finish("session", 1, "你好。")
        await control.adopt("session", 1, 7, "你好。")
        proof = await control.wait()
        assert tts.texts == ["你好。"]
        assert len(events) == 1 and events[0].correlation_id == 7
        assert proof.fragment_count == 1
        assert proof.queue_high_water == 1
        assert control.queue_depth == 0
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c02_two_available_fragments_coalesce_once() -> None:
    async def run():
        control, tts, events = _control()
        await control.feed("session", 1, 0, "甲")
        await control.feed("session", 1, 1, "乙")
        control.start()
        await control.finish("session", 1, "甲乙")
        await control.adopt("session", 1, 8, "甲乙")
        proof = await control.wait()
        assert tts.texts == ["甲乙"]
        assert proof.queue_high_water == 2
        assert len(events) == 1
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c03_third_fragment_backpressures() -> None:
    async def run():
        tts = TTS(blocked=True)
        control, _, _ = _control(tts)
        await control.feed("session", 1, 0, "甲")
        await control.feed("session", 1, 1, "乙")
        pending = asyncio.create_task(control.feed("session", 1, 2, "丙"))
        await asyncio.sleep(0)
        assert not pending.done()
        control.start()
        await asyncio.wait_for(tts.entered.wait(), 1)
        await asyncio.wait_for(pending, 1)
        assert control.queue_high_water == 2
        tts.release.set()
        await control.finish("session", 1, "甲乙丙")
        await control.adopt("session", 1, 9, "甲乙丙")
        await control.wait()
        assert tts.texts == ["甲乙", "丙"]
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c04_byte_limit_backpressures() -> None:
    async def run():
        tts = TTS(blocked=True)
        control, _, _ = _control(tts)
        await control.feed("session", 1, 0, "a" * 200)
        pending = asyncio.create_task(control.feed("session", 1, 1, "b" * 57))
        await asyncio.sleep(0)
        assert not pending.done()
        control.start()
        await asyncio.wait_for(pending, 1)
        assert control.pending_utf8_bytes <= 256
        await control.cancel()
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c05_does_not_wait_for_future_lookahead() -> None:
    async def run():
        tts = TTS(blocked=True)
        control, _, _ = _control(tts)
        await control.feed("session", 1, 0, "甲")
        control.start()
        await asyncio.wait_for(tts.entered.wait(), 1)
        assert tts.texts == ["甲"]
        await control.feed("session", 1, 1, "乙")
        tts.release.set()
        await control.finish("session", 1, "甲乙")
        await control.adopt("session", 1, 10, "甲乙")
        await control.wait()
        assert tts.texts == ["甲", "乙"]
    asyncio.run(run())


@pytest.mark.parametrize(
    ("case", "feed"),
    [
        ("C08", ("session", 1, 0, "")),
        ("C09", ("session", 1, 0, "duplicate")),
        ("C10", ("session", 1, 2, "gap")),
        ("C11", ("session", 1, 0, "x" * 257)),
        ("C13", ("stale", 1, 0, "stale")),
    ],
)
def test_m4c_ss_ctrl_001_invalid_fragments_fail_closed(case, feed) -> None:
    async def run():
        control, tts, events = _control()
        if case == "C09":
            await control.feed("session", 1, 0, "first")
        with pytest.raises(StreamingSpeakError):
            await control.feed(*feed)
        assert tts.texts == []
        assert events == []
        await control.cancel()
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c07_prefix_mismatch_cancels() -> None:
    async def run():
        control, tts, events = _control()
        await control.feed("session", 1, 0, "甲")
        control.start()
        with pytest.raises(StreamingSpeakError, match="TERMINAL_PREFIX_MISMATCH"):
            await control.finish("session", 1, "乙")
        await asyncio.gather(control.task, return_exceptions=True)
        assert control.state == "FAILED"
        assert events == []
        assert tts.aborts == 1
    asyncio.run(run())


@pytest.mark.parametrize("phase", ["queued", "synthesizing"])
def test_m4c_ss_ctrl_001_c14_c15_interrupt_has_no_success(phase) -> None:
    async def run():
        tts = TTS(blocked=True)
        control, _, events = _control(tts)
        await control.feed("session", 1, 0, "甲")
        if phase == "synthesizing":
            control.start()
            await asyncio.wait_for(tts.entered.wait(), 1)
        await control.cancel()
        assert control.state == "CANCELLED"
        assert control.queue_depth == 0
        assert events == []
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c12_post_terminal_rejected() -> None:
    async def run():
        control, _, _ = _control()
        control.start()
        await control.finish("session", 1, "terminal")
        with pytest.raises(StreamingSpeakError, match="ADMISSION_CLOSED"):
            await control.feed("session", 1, 1, "late")
        await control.cancel()
    asyncio.run(run())


def test_m4c_ss_ctrl_001_c22_empty_terminal_closes_without_owner() -> None:
    async def run():
        control, tts, events = _control()
        control.start()
        await control.close_unused()
        assert tts.texts == []
        assert events == []
        assert control.state == "CANCELLED"
    asyncio.run(run())
