"""Barrier-based M1-SM-001 through M1-SM-006 acceptance checks."""
from __future__ import annotations

import asyncio
import logging
import pytest

from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, ExternalMessageArrived,
    LLMResponse, PerceptionResult, StateChanged, ShutdownRequested,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.resource_manager.models import RecoveryTicket
from sbd.core.state_manager.convergence import ConvergenceResult
from sbd.core.state_manager.exceptions import StateManagerInvariantViolation, WorkerContractViolation
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.session import SessionContext
from sbd.core.state_manager.inflight import InFlightRecord
from sbd.core.state_manager.notices import _TaskCompleted, _WakeAckElapsed


async def wait(event: asyncio.Event) -> None:
    await asyncio.wait_for(event.wait(), timeout=1)


class Worker:
    def __init__(
        self,
        bus: EventBus,
        kind: str,
        phase: str,
        *,
        hold_after_fact: bool = False,
        invalid_response: bool = False,
        action_kind: str = "rest",
        next_perceptions: tuple[str, ...] = (),
        publish_fact: bool = True,
        action_payload: dict | None = None,
    ):
        self.bus, self.kind, self.phase = bus, kind, phase
        self.hold_after_fact, self.invalid_response = hold_after_fact, invalid_response
        self.action_kind = action_kind
        self.next_perceptions = next_perceptions
        self.publish_fact = publish_fact
        self.started, self.fact_sent, self.release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.action_payload = {"value": 1} if action_payload is None else action_payload

    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def abort(self) -> None: self.release.set()
    async def force_abort(self) -> ForceAbortReport:
        self.release.set()
        return ForceAbortReport()

    async def perceive(self, session_id: str, turn_id: int, correlation_id: int, timeout_seconds: float) -> None:
        self.started.set()
        if self.publish_fact:
            await self.bus.publish(PerceptionResult(self.kind, "ok", self.kind, session_id=session_id, turn_id=turn_id, correlation_id=correlation_id))
            self.fact_sent.set()
        if self.hold_after_fact:
            await self.release.wait()

    async def reason(self, session_id: str, turn_id: int, correlation_id: int, results: tuple, pending: tuple) -> None:
        self.started.set()
        kind = "bogus" if self.invalid_response else self.action_kind
        await self.bus.publish(LLMResponse(kind, self.action_payload, self.next_perceptions, session_id=session_id, turn_id=turn_id, correlation_id=correlation_id))  # type: ignore[arg-type]
        self.fact_sent.set()
        if self.hold_after_fact:
            await self.release.wait()

    async def execute(self, session_id: str, turn_id: int, correlation_id: int, payload: dict) -> None:
        self.started.set()
        await self.bus.publish(ActionCompleted(self.kind, getattr(self, "action_status", "ok"), session_id=session_id, turn_id=turn_id, correlation_id=correlation_id))
        self.fact_sent.set()
        if self.hold_after_fact:
            await self.release.wait()


class ExternalControl:
    def __init__(self) -> None:
        self.assigned: list[str] = []
        self.read_started = asyncio.Event()
        self.discarded = 0
        self.flushed = 0
        self.closed: list[tuple[str, int]] = []
        self.pending: list[str] = []

    async def assign_to_session(self, message_id: str, session_id: str) -> None:
        self.assigned.append(session_id)
    async def assign_to_turn(self, message_id: str, session_id: str, turn_id: int) -> None:
        self.pending.append(message_id)
    async def mark_pending(self, message_id: str, session_id: str) -> None:
        self.pending.append(message_id)
    async def begin_read(self, session_id: str, turn_id: int) -> tuple[str, ...]:
        self.read_started.set()
        return ()
    async def close_read(self, session_id: str, turn_id: int) -> None:
        self.closed.append((session_id, turn_id))
    async def pending_ids(self, session_id: str) -> tuple[str, ...]:
        return tuple(self.pending)
    async def flush_to_wake(self) -> None: self.flushed += 1
    async def discard(self) -> None: self.discarded += 1


def make_sm(
    *,
    hold_action: bool = False,
    hold_perception: bool = False,
    hold_reasoner: bool = False,
    invalid_response: bool = False,
    action_kind: str = "rest",
    next_perceptions: tuple[str, ...] = (),
    converger=None,
    action_payload: dict | None = None,
    action_validator=None,
    recovery=None,
):
    bus = EventBus()
    listen = Worker(bus, "listen", "perception", hold_after_fact=hold_perception)
    read = Worker(bus, "read", "perception")
    reasoner = Worker(
        bus,
        "reasoner",
        "think",
        hold_after_fact=hold_reasoner,
        invalid_response=invalid_response,
        action_kind=action_kind,
        next_perceptions=next_perceptions,
        action_payload=action_payload,
    )
    rest = Worker(bus, "rest", "action", hold_after_fact=hold_action)
    speak = Worker(bus, "speak", "action", hold_after_fact=True)
    catalog = WorkerCatalog()
    catalog.register_perception("listen", listen)
    catalog.register_perception("read", read)
    catalog.set_reasoner(reasoner)
    catalog.register_action("rest", rest)
    catalog.register_action("speak", speak)
    tool = Worker(bus, "tool", "action", hold_after_fact=True)
    catalog.register_action("tool", tool)
    catalog.seal()
    sm = StateManager(
        bus=bus,
        workers=catalog,
        wake_ack_seconds=60,
        converger=converger,
        action_validator=action_validator,
        recovery=recovery,
    )
    return bus, sm, listen, read, reasoner, rest, speak


def state_barrier(bus: EventBus, target: str) -> asyncio.Event:
    reached = asyncio.Event()
    async def on_state(event: StateChanged) -> None:
        if event.new == target:
            reached.set()
    bus.subscribe(StateChanged, on_state)
    return reached


async def start_perception(bus: EventBus, sm: StateManager, listen: Worker) -> None:
    woke = state_barrier(bus, "WAKE")
    await sm.start()
    await bus.publish(ButtonPressed("conversation", 1))
    await wait(woke)
    wake = sm._session
    assert wake is not None and sm.state == "WAKE"
    sm._inbox.put_nowait(_WakeAckElapsed(wake.session_id))
    await wait(listen.started)


def test_m1_sm_001_subscriptions_enqueue_and_transitions_are_serial() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        states: list[str] = []
        bus.subscribe(StateChanged, lambda event: capture(states, event))
        await start_perception(bus, sm, listen)
        await bus.publish(ButtonPressed("conversation", 1))
        assert sm.state == "PERCEPTION"
        assert states[:2] == ["WAKE", "PERCEPTION"]
        await bus.publish(__import__("sbd.core.events", fromlist=["ShutdownRequested"]).ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


async def capture(states: list[str], event: StateChanged) -> None:
    states.append(event.new)


def test_m1_sm_002_fact_and_task_done_form_a_join_barrier() -> None:
    async def run() -> None:
        bus, sm, listen, _, reasoner, _, _ = make_sm(hold_perception=True)
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        assert sm.state == "PERCEPTION"  # Fact alone cannot advance the phase.
        listen.release.set()
        await wait(reasoner.started)
        await sm._inbox.join()
        await sm._inbox.join()
        assert sm.state == "ACTION"
        sm._session = None
        await sm.stop()
    asyncio.run(run())


def test_m1_sm_003_stale_and_duplicate_facts_do_not_pollute_turn() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        assert sm._session is not None
        await bus.publish(PerceptionResult("listen", "ok", "stale", session_id="other", turn_id=1, correlation_id=999))
        await bus.publish(PerceptionResult("listen", "ok", "duplicate", session_id=sm._session.session_id, turn_id=sm._session.turn_id, correlation_id=1))
        await sm._inbox.join()
        assert [item.text for item in sm._session.perception_results] == ["listen"]
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_m1_sm_004_external_wake_maps_to_read_before_worker_starts() -> None:
    async def run() -> None:
        bus, sm, _, read, *_ = make_sm()
        external = ExternalControl()
        sm.set_external_message_control(external)
        await sm.start()
        woke = state_barrier(bus, "WAKE")
        await bus.publish(ExternalMessageArrived("test", 0.0, "message-1"))
        await wait(woke)
        assert external.assigned and sm._session is not None
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(read.started)
        assert external.read_started.is_set()
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_m1_sm_005_invalid_reasoner_response_enters_error_without_error_event() -> None:
    async def run() -> None:
        bus, sm, listen, _, reasoner, _, _ = make_sm(invalid_response=True, hold_reasoner=True)
        errors: list[ErrorOccurred] = []
        states: list[str] = []
        bus.subscribe(ErrorOccurred, lambda event: collect(errors, event))
        bus.subscribe(StateChanged, lambda event: capture(states, event))
        await start_perception(bus, sm, listen)
        await wait(reasoner.fact_sent)
        assert sm.state == "THINK"
        errored = state_barrier(bus, "ERROR")
        reasoner.release.set()
        await wait(errored)
        assert sm.state in {"ERROR", "IDLE"}
        assert "ACTION" not in states
        assert errors == []
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


async def collect(items: list, event) -> None:
    items.append(event)


class EarlyConverger:
    async def converge(self, records, trigger: str) -> ConvergenceResult:
        return ConvergenceResult()


def test_m1_sm_006_convergence_waits_for_inflight_handles_before_idle() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True, converger=EarlyConverger())
        states: list[str] = []
        bus.subscribe(StateChanged, lambda event: capture(states, event))
        await start_perception(bus, sm, listen)
        await bus.publish(__import__("sbd.core.events", fromlist=["InterruptRequested"]).InterruptRequested())
        await sm._inbox.join()
        assert sm.state == "PERCEPTION"
        assert "ERROR" not in states
        await bus.publish(ButtonPressed("conversation", 1))
        assert sm.state == "PERCEPTION"
        idled = state_barrier(bus, "IDLE")
        listen.release.set()
        await wait(idled)
        assert sm.state == "IDLE"
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_m1_sm_003_worker_return_without_fact_is_runtime_fatal() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm()
        listen.publish_fact = False
        await start_perception(bus, sm, listen)
        with pytest.raises(StateManagerInvariantViolation):
            await sm.wait_stopped()

        # Fatal dispatch deliberately preserves the active session for
        # supervision diagnostics; only clean up SM-owned subscriptions here.
        sm._session = None
        sm._shutting_down = True
        await sm.stop()

    asyncio.run(run())


def test_m1_sm_004_early_error_cancels_timer_and_stale_notice_is_ignored() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm()
        await sm.start()
        woke = state_barrier(bus, "WAKE")
        await bus.publish(ButtonPressed("conversation", 1))
        await wait(woke)
        assert sm._session is not None
        stale_session = sm._session.session_id

        idled = state_barrier(bus, "IDLE")
        await bus.publish(ErrorOccurred("test", "leave wake early"))
        await wait(idled)
        assert sm._wake_timer is None
        sm._inbox.put_nowait(_WakeAckElapsed(stale_session))
        await sm._inbox.join()
        assert sm.state == "IDLE"
        assert listen.started.is_set() is False

        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    asyncio.run(run())


def test_m1_sm_005_validator_rejection_is_nonfatal_error_without_bus_error() -> None:
    async def run() -> None:
        calls: list[tuple[str, dict]] = []

        class RejectingValidator:
            def validate(self, kind: str, payload: dict) -> None:
                calls.append((kind, payload))
                raise ValueError("rejected")

        bus, sm, listen, *_ = make_sm(
            action_kind="speak",
            next_perceptions=("listen",),
            action_validator=RejectingValidator(),
        )
        errors: list[ErrorOccurred] = []
        bus.subscribe(ErrorOccurred, lambda event: collect(errors, event))
        errored = state_barrier(bus, "ERROR")
        await start_perception(bus, sm, listen)
        await wait(errored)
        assert calls == [("speak", {"value": 1})]
        assert errors == []
        dispatch = sm._loop_task
        assert dispatch is not None and not dispatch.done()

        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    asyncio.run(run())


def test_m1_sm_005_speak_normalizes_next_perceptions_and_starts_action() -> None:
    async def run() -> None:
        bus, sm, listen, _, _, _, speak = make_sm(
            action_kind="speak",
            next_perceptions=("missing", "read", "read"),
        )
        await start_perception(bus, sm, listen)
        await wait(speak.started)
        assert sm.state == "ACTION"
        assert sm._session is not None
        assert sm._session.next_perceptions == ("read",)
        action_records = [
            record for record in sm._in_flight.values()
            if record.phase == "action"
        ]
        assert [record.kind for record in action_records] == ["speak"]

        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    asyncio.run(run())


class DestroyedConverger:
    async def converge(self, records, trigger: str) -> ConvergenceResult:
        return ConvergenceResult(("backend.a",))


class RecoveryPort:
    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.begun: list[tuple[str, ...]] = []
        self.prepared = 0

    def begin_recovery(self, keys: tuple[str, ...]) -> RecoveryTicket:
        self.begun.append(keys)
        return RecoveryTicket(1, keys)  # type: ignore[arg-type]

    async def wait_recovery(self, ticket: RecoveryTicket) -> None:
        await self.release.wait()

    def recovery_ready(self) -> bool:
        return self.release.is_set()

    async def prepare_shutdown(self) -> None:
        self.prepared += 1
        self.release.set()


def test_m1_sm_006_error_exit_waits_for_handles_and_recovery() -> None:
    async def run() -> None:
        recovery = RecoveryPort()
        bus, sm, listen, *_ = make_sm(
            hold_perception=True,
            converger=DestroyedConverger(),
            recovery=recovery,
        )
        external = ExternalControl()
        sm.set_external_message_control(external)
        await start_perception(bus, sm, listen)
        errored = state_barrier(bus, "ERROR")
        await bus.publish(__import__("sbd.core.events", fromlist=["InterruptRequested"]).InterruptRequested())
        await wait(errored)
        assert recovery.begun == [("backend.a",)]

        outer = next(iter(sm._in_flight.values())).task
        listen.release.set()
        await outer
        await sm._inbox.join()
        assert sm.state == "ERROR"
        assert sm._in_flight == {}
        assert external.discarded == 0

        idled = state_barrier(bus, "IDLE")
        recovery.release.set()
        await wait(idled)
        assert external.discarded == 1

        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()

    asyncio.run(run())


def test_sm_regression_cancellation_whitelist_and_p5_logging(caplog) -> None:
    async def run() -> None:
        sm = StateManager(wake_ack_seconds=1)
        session = SessionContext("session", "button", turn_id=1)
        sm._session = session
        sm._state = "PERCEPTION"
        for fact in (
            LLMResponse("rest", {}, (), "session", 1, 1),
            ActionCompleted("rest", "ok", session_id="session", turn_id=1, correlation_id=1),
        ):
            await sm._handle_item(fact)
        assert session.llm_response is None and session.action_completed is None

        cancelled = asyncio.create_task(asyncio.sleep(60))
        cancelled.cancel()
        await asyncio.gather(cancelled, return_exceptions=True)
        for requested in (False, True):
            sm._in_flight = {9: InFlightRecord(9, "session", 1, "perception", "listen", object(), cancelled, cancel_requested=requested)}
            notice = _TaskCompleted("listen", 9, cancelled)
            if requested:
                await sm._handle_task_completed(notice)
            else:
                with pytest.raises(WorkerContractViolation):
                    await sm._handle_task_completed(notice)

        completed = asyncio.create_task(asyncio.sleep(60))
        sm._in_flight = {10: InFlightRecord(10, "session", 1, "perception", "listen", object(), completed)}
        with caplog.at_level(logging.WARNING):
            sm._handle_fact(PerceptionResult("listen", "error", "SENSITIVE_SENTINEL", session_id="session", turn_id=1, correlation_id=10))
        assert "P5 terminal fact status=error" in caplog.text
        assert "SENSITIVE_SENTINEL" not in caplog.text
        completed.cancel()
        await asyncio.gather(completed, return_exceptions=True)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("state", "fact"),
    [
        ("PERCEPTION", LLMResponse("rest", {}, (), "s", 1, 1)),
        ("THINK", PerceptionResult("listen", "ok", None, session_id="s", turn_id=1, correlation_id=1)),
        ("ACTION", LLMResponse("rest", {}, (), "s", 1, 1)),
        ("ERROR", ActionCompleted("rest", "ok", session_id="s", turn_id=1, correlation_id=1)),
    ],
)
def test_sm_regression_wrong_phase_and_late_facts_drop(
    state: str, fact: PerceptionResult | LLMResponse | ActionCompleted, caplog
) -> None:
    async def run() -> None:
        sm = StateManager(wake_ack_seconds=1)
        sm._state = state  # type: ignore[assignment]
        sm._session = SessionContext("s", "button", turn_id=1)
        with caplog.at_level(logging.WARNING):
            await sm._handle_item(fact)
        assert f"Dropping {type(fact).__name__} while state is {state}" in caplog.text
        assert sm._session.perception_results == []
        assert sm._session.llm_response is None
        assert sm._session.action_completed is None
    asyncio.run(run())
