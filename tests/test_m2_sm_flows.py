"""M2-FLOW-003 through 006 StateManager integration boundaries."""

from __future__ import annotations

import asyncio

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool import RegisteredTool, ToolRegistry
from sbd.core.audio.mock import MockAudioInput
from sbd.core.config.models import AudioConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ButtonPressed,
    ErrorOccurred,
    InterruptRequested,
    ShutdownRequested,
    StateChanged,
)
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.notices import _WakeAckElapsed
from sbd.perception.listen import Listen, MockASRAdapter
from tests.test_state_manager import (
    EarlyConverger,
    ExternalControl,
    Worker,
    make_sm,
    start_perception,
    state_barrier,
    wait,
)


def _validator(*, with_tool: bool = False) -> ActionPayloadValidator:
    registry = ToolRegistry()
    if with_tool:
        async def handler(arguments: dict) -> dict:
            return {}

        registry.register(RegisteredTool(
            name="fixture.run",
            description="fixture tool",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            validate=lambda arguments: None,
            handler=handler,
        ))
    registry.seal()
    return ActionPayloadValidator(tools=registry)


def test_m2_flow_003_speak_tool_dedupe_and_rest_ignores_next() -> None:
    async def action_case(kind: str) -> None:
        payload = (
            {"text": "ok"}
            if kind == "speak"
            else {"name": "fixture.run", "arguments": {}}
        )
        bus, sm, listen, _, _, _, speak = make_sm(
            action_kind=kind,
            action_payload=payload,
            next_perceptions=("missing", "read", "read", "listen"),
            action_validator=_validator(with_tool=kind == "tool"),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        errors: list[ErrorOccurred] = []

        async def error(event: ErrorOccurred) -> None:
            errors.append(event)

        bus.subscribe(ErrorOccurred, error)
        await start_perception(bus, sm, listen)
        target = speak if kind == "speak" else sm._workers.action("tool")
        await wait(target.started)
        assert sm.state == "ACTION"
        assert sm._session is not None
        assert sm._session.next_perceptions == ("read", "listen")
        active = [
            record.kind for record in sm._in_flight.values()
            if record.phase == "action"
        ]
        assert active == [kind]
        assert errors == []
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def rest_case(next_perceptions: tuple[str, ...]) -> None:
        bus, sm, listen, _, _, rest, _ = make_sm(
            action_kind="rest",
            action_payload={},
            next_perceptions=next_perceptions,
            action_validator=_validator(),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        await wait(idled)
        assert rest.started.is_set() and rest.fact_sent.is_set()
        assert sm.state == "IDLE" and sm._in_flight == {}
        assert external.flushed == 1
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def run() -> None:
        await action_case("speak")
        await action_case("tool")
        for value in ((), ("missing",), ("read", "read", "missing")):
            await rest_case(value)

    asyncio.run(run())


def test_m2_flow_004_action_error_uses_default_perceptions() -> None:
    async def run() -> None:
        bus, sm, listen, _, _, _, speak = make_sm(
            action_kind="speak",
            action_payload={"text": "ok"},
            next_perceptions=("read",),
            action_validator=_validator(),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        speak.action_status = "error"
        await start_perception(bus, sm, listen)
        await wait(speak.fact_sent)
        listen.started = asyncio.Event()
        listen.fact_sent = asyncio.Event()
        listen.hold_after_fact = True
        speak.release.set()
        await wait(listen.started)
        assert sm.state == "PERCEPTION"
        assert sm._session is not None
        assert sm._session.turn_id == 2
        assert sm._session.selected_perceptions == ("listen",)
        assert len([
            record for record in sm._in_flight.values()
            if record.kind == "listen"
        ]) == 1
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    asyncio.run(run())


def test_m2_flow_005_worker_error_precedes_error_state_and_self_check_does_not() -> None:
    async def worker_case() -> None:
        bus = EventBus()
        listen = Listen(
            audio_input=MockAudioInput(AudioConfig(driver="mock")),
            asr=MockASRAdapter((RuntimeError("raw-secret"),)),
            bus=bus,
        )
        reasoner = Worker(bus, "reasoner", "think")
        rest = Worker(bus, "rest", "action")
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("rest", rest)
        catalog.seal()
        sm = StateManager(
            bus=bus,
            workers=catalog,
            wake_ack_seconds=60,
            action_validator=_validator(),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        order: list[str] = []

        async def error(event: ErrorOccurred) -> None:
            order.append("ErrorOccurred")

        async def state(event: StateChanged) -> None:
            if event.new in {"ERROR", "IDLE"}:
                order.append(event.new)

        idled = state_barrier(bus, "IDLE")
        bus.subscribe(ErrorOccurred, error)
        bus.subscribe(StateChanged, state)
        await sm.start()
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        assert sm._session is not None
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await asyncio.wait_for(sm._inbox.join(), 2.0)
        await wait(idled)
        assert order == ["ErrorOccurred", "ERROR", "IDLE"]
        assert external.discarded == 1
        assert sm._in_flight == {}
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def self_check_case() -> None:
        bus, sm, listen, *_ = make_sm(
            action_kind="speak",
            action_payload={"text": ""},
            next_perceptions=("listen",),
            action_validator=_validator(),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        order: list[str] = []

        async def error(event: ErrorOccurred) -> None:
            order.append("ErrorOccurred")

        async def state(event: StateChanged) -> None:
            if event.new in {"ERROR", "IDLE"}:
                order.append(event.new)

        bus.subscribe(ErrorOccurred, error)
        idled = state_barrier(bus, "IDLE")
        bus.subscribe(StateChanged, state)
        await start_perception(bus, sm, listen)
        await wait(idled)
        await asyncio.wait_for(sm._inbox.join(), 2.0)
        assert order == ["ERROR", "IDLE"]
        assert external.discarded == 1
        assert sm._loop_task is not None and not sm._loop_task.done()
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def run() -> None:
        await worker_case()
        await self_check_case()

    asyncio.run(run())


def test_m2_flow_006_notice_barrier_and_exit_buffer_policies() -> None:
    async def rest_case() -> None:
        bus, sm, listen, _, _, rest, _ = make_sm(
            hold_action=True,
            action_kind="rest",
            action_payload={},
            action_validator=_validator(),
            converger=EarlyConverger(),
        )
        order: list[str] = []

        class OrderedExternal(ExternalControl):
            async def flush_to_wake(self) -> None:
                order.append("flush")
                await super().flush_to_wake()

        external = OrderedExternal()
        sm.set_external_message_control(external)

        async def state(event: StateChanged) -> None:
            if event.new == "IDLE":
                order.append("IDLE")

        bus.subscribe(StateChanged, state)
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        await wait(rest.fact_sent)
        await sm._inbox.join()
        assert sm.state == "ACTION"
        assert sm._in_flight and order == []
        rest.release.set()
        await asyncio.wait_for(sm._inbox.join(), 2.0)
        await wait(idled)
        assert order == ["IDLE", "flush"]
        assert sm._in_flight == {} and sm._session is None
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def interrupt_case() -> None:
        bus, sm, listen, *_ = make_sm(
            hold_perception=True,
            converger=EarlyConverger(),
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        await start_perception(bus, sm, listen)
        await bus.publish(InterruptRequested())
        await sm._inbox.join()
        assert sm.state == "PERCEPTION" and sm._in_flight
        idled = state_barrier(bus, "IDLE")
        listen.release.set()
        await asyncio.wait_for(sm._inbox.join(), 2.0)
        await wait(idled)
        assert sm.state == "IDLE"
        assert external.discarded == 1 and external.flushed == 0
        assert sm._in_flight == {} and sm._session is None
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    async def shutdown_case() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        external = ExternalControl()
        sm.set_external_message_control(external)
        await start_perception(bus, sm, listen)
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        assert external.discarded == 1
        assert sm._in_flight == {} and sm._session is None
        await sm.stop()

    async def run() -> None:
        await rest_case()
        await interrupt_case()
        await shutdown_case()

    asyncio.run(run())
