"""M3 physical conversation-button product-semantics acceptance cards."""

from __future__ import annotations

import asyncio

import pytest

from sbd.core.events import ButtonPressed, ShutdownRequested, StateChanged
from sbd.core.gpio import make_gpio
from sbd.core.state_manager.manager import _PendingConvergence
from sbd.core.state_manager.notices import _WakeAckElapsed
from sbd.input_events.button import ButtonInputSource
from tests.rpi_support import interaction_timeout, record_result, rpi_config
from tests.test_state_manager import make_sm, wait


pytestmark = pytest.mark.rpi


async def _source(config, bus):
    pin = config.core.gpio.pins[config.input_sources.button.conversation_pin]
    gpio = make_gpio(config.core.gpio)
    source = ButtonInputSource(
        gpio=gpio, bus=bus, config=config.input_sources.button, pin_config=pin,
    )
    await gpio.start()
    await source.start()
    await source.arm()
    return gpio, source


def test_m3_btn_001() -> None:
    config = rpi_config("M3-BTN-001")

    async def scenario() -> tuple[int, tuple[str, ...]]:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        states: list[str] = []
        pressed: asyncio.Queue[ButtonPressed] = asyncio.Queue()

        async def on_state(event: StateChanged) -> None:
            states.append(event.new)

        async def on_press(event: ButtonPressed) -> None:
            pressed.put_nowait(event)

        bus.subscribe(StateChanged, on_state, name="m3.btn001.states")
        bus.subscribe(ButtonPressed, on_press, name="m3.btn001.signal")
        await sm.start()
        gpio, source = await _source(config, bus)
        try:
            event = await asyncio.wait_for(pressed.get(), interaction_timeout())
            assert config.input_sources.button.short_press_min_ms <= event.duration_ms
            assert event.duration_ms < config.input_sources.button.long_press_min_ms
            await sm._inbox.join()
            assert sm.state == "WAKE"
            assert sm._session is not None
            sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
            await wait(listen.started)
            assert sm.state == "PERCEPTION"
            assert states[:2] == ["WAKE", "PERCEPTION"]
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            assert sm._in_flight == {}
            await sm.stop()
            return event.duration_ms, tuple(states)
        finally:
            await source.stop()
            await gpio.stop()

    duration, states = asyncio.run(scenario())
    record_result(
        "M3-BTN-001",
        expected="physical short press publishes ButtonPressed and drives IDLE→WAKE→PERCEPTION",
        actual=f"duration_ms={duration}; states={states}; no task remained after shutdown",
        fixture={"name": "physical conversation button short press", "sha256": "physical-fixture"},
        operation="Short-press once only after pytest prints this card name",
    )


def test_m3_btn_002() -> None:
    config = rpi_config("M3-BTN-002")

    async def scenario() -> tuple[int, tuple[str, ...]]:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        states: list[str] = []
        physical: asyncio.Queue[ButtonPressed] = asyncio.Queue()

        async def on_state(event: StateChanged) -> None:
            states.append(event.new)

        bus.subscribe(StateChanged, on_state, name="m3.btn002.states")
        await sm.start()
        await bus.publish(ButtonPressed("setup", config.input_sources.button.short_press_min_ms))
        await sm._inbox.join()
        assert sm._session is not None
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(listen.started)
        assert sm.state == "PERCEPTION" and sm._in_flight

        async def on_physical(event: ButtonPressed) -> None:
            if event.pin == config.input_sources.button.conversation_pin:
                physical.put_nowait(event)

        bus.subscribe(ButtonPressed, on_physical, name="m3.btn002.physical")
        gpio, source = await _source(config, bus)
        try:
            event = await asyncio.wait_for(physical.get(), interaction_timeout())
            await sm._inbox.join()
            assert sm.state == "IDLE" and sm._session is None and sm._in_flight == {}
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await sm.stop()
            return event.duration_ms, tuple(states)
        finally:
            await source.stop()
            await gpio.stop()

    duration, states = asyncio.run(scenario())
    record_result(
        "M3-BTN-002",
        expected="short press during PERCEPTION executes interrupt convergence and returns IDLE",
        actual=f"duration_ms={duration}; state trace={states}; session and tasks drained",
        fixture={"name": "physical button during held perception", "sha256": "physical-fixture"},
        operation="Wait for the test to enter PERCEPTION, then short-press once",
    )


def test_m3_btn_003() -> None:
    config = rpi_config("M3-BTN-003")

    async def scenario() -> None:
        bus, sm, *_ = make_sm()
        shutdowns: asyncio.Queue[ShutdownRequested] = asyncio.Queue()

        async def observe(event: ShutdownRequested) -> None:
            shutdowns.put_nowait(event)

        bus.subscribe(ShutdownRequested, observe, name="m3.btn003.shutdown")
        await sm.start()
        gpio, source = await _source(config, bus)
        try:
            await asyncio.wait_for(shutdowns.get(), interaction_timeout())
            await sm.wait_stopped()
            assert sm._loop_task is not None and sm._loop_task.done()
            assert sm._session is None and sm._in_flight == {}
            await sm.stop()
        finally:
            await source.stop()
            await gpio.stop()

    asyncio.run(scenario())
    record_result(
        "M3-BTN-003",
        expected="physical long press publishes ShutdownRequested and completes graceful lifecycle",
        actual="SM dispatch stopped cleanly with no session/tasks; card exit code 0",
        fixture={"name": "physical conversation button long press", "sha256": "physical-fixture"},
        operation="Hold the button beyond long_press_min_ms, then release",
    )


def test_m3_btn_004() -> None:
    config = rpi_config("M3-BTN-004")

    async def scenario() -> tuple[int, str]:
        bus, sm, *_ = make_sm()
        await sm.start()
        sm._state = "ERROR"
        sm._pending = None  # accepted precondition: recovery complete or absent
        pressed: asyncio.Queue[ButtonPressed] = asyncio.Queue()

        async def observe(event: ButtonPressed) -> None:
            pressed.put_nowait(event)

        bus.subscribe(ButtonPressed, observe, name="m3.btn004.signal")
        gpio, source = await _source(config, bus)
        try:
            event = await asyncio.wait_for(pressed.get(), interaction_timeout())
            await sm._inbox.join()
            assert sm.state == "WAKE"
            assert sm._session is not None and sm._session.wake_source == "button"
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await sm.stop()
            return event.duration_ms, "ERROR→WAKE"
        finally:
            await source.stop()
            await gpio.stop()

    duration, trace = asyncio.run(scenario())
    record_result(
        "M3-BTN-004",
        expected="short press in recovered ERROR enters WAKE directly",
        actual=f"duration_ms={duration}; trace={trace}; new button session created",
        fixture={"name": "physical button with recovered ERROR precondition", "sha256": "state-fixture"},
        operation="Short-press once after the card enters recovered ERROR",
    )


def test_m3_btn_005() -> None:
    config = rpi_config("M3-BTN-005")

    async def scenario() -> tuple[int, int]:
        bus, sm, *_ = make_sm()
        await sm.start()
        sm._state = "ERROR"
        sm._pending = _PendingConvergence("error", "discard", recovery_generation=1)
        pressed: asyncio.Queue[ButtonPressed] = asyncio.Queue()

        async def observe(event: ButtonPressed) -> None:
            pressed.put_nowait(event)

        bus.subscribe(ButtonPressed, observe, name="m3.btn005.signal")
        gpio, source = await _source(config, bus)
        try:
            ignored = await asyncio.wait_for(pressed.get(), interaction_timeout())
            await sm._inbox.join()
            assert sm.state == "ERROR"
            assert sm._pending is not None and sm._pending.recovery_generation == 1
            assert sm._session is None

            sm._pending = None  # deterministic recovery-complete boundary
            accepted = await asyncio.wait_for(pressed.get(), interaction_timeout())
            await sm._inbox.join()
            assert sm.state == "WAKE"
            assert sm._session is not None and sm._session.wake_source == "button"
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await sm.stop()
            return ignored.duration_ms, accepted.duration_ms
        finally:
            await source.stop()
            await gpio.stop()

    ignored, accepted = asyncio.run(scenario())
    record_result(
        "M3-BTN-005",
        expected="recovery-active short press is ignored; post-recovery short press starts WAKE",
        actual=f"first duration={ignored} stayed ERROR; second duration={accepted} entered WAKE",
        fixture={"name": "two physical presses across recovery barrier", "sha256": "state-fixture"},
        operation="Short-press once during recovery; after prompt/state boundary, short-press again",
    )
