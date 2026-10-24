"""Executable coverage for the M4B foundation revision."""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import inspect
from pathlib import Path

import pytest

from sbd.core.event_bus import EventBus
from sbd.core.events import (
    ActionCompleted, ButtonPressed, ErrorOccurred, InterruptRequested,
    LLMResponse, ShutdownRequested, StateChanged,
)
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.state_manager.convergence import (
    CancelTimeoutPolicy, ConvergenceFatalError, DefaultSessionConverger,
)
from sbd.core.state_manager.exceptions import (
    StateManagerInvariantViolation, StateManagerWiringError,
)
from sbd.core.state_manager.inflight import InFlightRecord
from sbd.core.state_manager.notices import (
    _ConversationLifecycleCompleted, _WakeAckElapsed,
)
from sbd.core.state_manager.ports import (
    ConversationCloseProof, ConversationOpenRejected, ConversationReady,
)
from sbd.core.state_manager.session import SessionContext
from tests.test_state_manager import (
    ConversationControl, ExternalControl, RecoveryPort, make_sm, start_perception,
    state_barrier, wait,
)


pytestmark = pytest.mark.m4b_foundation


class ControlledLifecycle:
    def __init__(self) -> None:
        self.open_release = asyncio.Event()
        self.close_release = asyncio.Event()
        self.open_calls: list[tuple[str, int]] = []
        self.close_calls: list[tuple[str, int, str]] = []
        self.open_results: list[object] = []
        self.close_results: list[object] = []
        self.abort_calls = 0
        self.force_abort_calls = 0
        self.abort_error: Exception | None = None
        self.force_abort_error: Exception | None = None
        self.abort_release = asyncio.Event()
        self.force_abort_release = asyncio.Event()
        self.block_abort = False
        self.block_force_abort = False
        self.force_abort_report = ForceAbortReport()

    async def open_conversation(self, session_id: str, generation: int):
        self.open_calls.append((session_id, generation))
        await self.open_release.wait()
        if self.open_results:
            result = self.open_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return ConversationReady(session_id, generation)

    async def close_conversation(self, session_id: str, generation: int, reason: str):
        self.close_calls.append((session_id, generation, reason))
        await self.close_release.wait()
        if self.close_results:
            result = self.close_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return ConversationCloseProof(session_id, generation, True, True, True)

    async def abort(self) -> None:
        self.abort_calls += 1
        if self.abort_error is not None:
            raise self.abort_error
        if self.block_abort:
            await self.abort_release.wait()
        self.open_release.set()
        self.close_release.set()

    async def force_abort(self) -> ForceAbortReport:
        self.force_abort_calls += 1
        if self.force_abort_error is not None:
            raise self.force_abort_error
        if self.block_force_abort:
            await self.force_abort_release.wait()
        self.open_release.set()
        self.close_release.set()
        return self.force_abort_report


async def _start_wake(sm, bus: EventBus, control: ControlledLifecycle) -> str:
    await sm.start()
    sm.set_conversation_lifecycle(control)
    woke = state_barrier(bus, "WAKE")
    await bus.publish(ButtonPressed("conversation", 1))
    await wait(woke)
    assert sm._session is not None
    return sm._session.session_id


async def _stop(sm, bus: EventBus) -> None:
    control = sm._conversation_control
    for name in ("open_release", "close_release"):
        barrier = getattr(control, name, None)
        if isinstance(barrier, asyncio.Event):
            barrier.set()
    if hasattr(control, "abort_release"):
        control.abort_release.set()
    if hasattr(control, "force_abort_release"):
        control.force_abort_release.set()
    if sm._loop_task is not None and not sm._loop_task.done():
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
    await sm.stop()


def test_m4b_foundation_fnd_evt_001_schema_is_required_frozen_and_ordered() -> None:
    fields = [field.name for field in dataclasses.fields(LLMResponse)]
    assert fields[:4] == [
        "action_kind", "action_payload", "post_action_route", "next_perceptions",
    ]
    with pytest.raises(TypeError):
        inspect.signature(LLMResponse).bind("speak", {}, ("listen",))
    with pytest.raises(TypeError):
        inspect.signature(LLMResponse).bind(
            action_kind="speak", action_payload={}, next_perceptions=("listen",)
        )
    response = LLMResponse(
        action_kind="speak", action_payload={}, post_action_route="KEEP_NEXT",
        next_perceptions=("listen",),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        response.post_action_route = "END_SESSION"  # type: ignore[misc]
    assert [field.name for field in dataclasses.fields(ActionCompleted)] == [
        "kind", "status", "result", "session_id", "turn_id", "correlation_id",
    ]
    canonical = (
        ("normal answer", "speak", "KEEP_NEXT", ("listen",)),
        ("application retry", "speak", "KEEP_NEXT", ("listen",)),
        ("replacement", "speak", "REPLACE_NEXT", ("listen",)),
        ("final speech", "speak", "END_SESSION", ()),
        ("empty end", "rest", "END_SESSION", ()),
        ("tool end", "tool", "END_SESSION", ()),
    )
    for _, action_kind, route, perceptions in canonical:
        outcome = LLMResponse(
            action_kind=action_kind,  # type: ignore[arg-type]
            action_payload={}, post_action_route=route,  # type: ignore[arg-type]
            next_perceptions=perceptions,
        )
        assert outcome.post_action_route == route


def test_m4b_foundation_fnd_evt_002_think_validation_and_normalization() -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        sm._session = SessionContext("s", "button", turn_id=1)
        valid = LLMResponse(
            action_kind="speak", action_payload={}, post_action_route="KEEP_NEXT",
            next_perceptions=("missing", "read", "read", "listen"),
        )
        await sm._validate_response(valid)
        assert sm._session.normalized_next_perceptions == ("read", "listen")
        assert valid.next_perceptions == ("missing", "read", "read", "listen")
        for response in (
            LLMResponse(action_kind="rest", action_payload={}, post_action_route="KEEP_NEXT", next_perceptions=()),
            LLMResponse(action_kind="speak", action_payload={}, post_action_route="REPLACE_NEXT", next_perceptions=()),
        ):
            with pytest.raises(Exception):
                await sm._validate_response(response)
        ending = LLMResponse(
            action_kind="speak", action_payload={}, post_action_route="END_SESSION",
            next_perceptions=("listen",),
        )
        await sm._validate_response(ending)
        assert sm._session.normalized_next_perceptions == ()
    asyncio.run(run())


@pytest.mark.parametrize(
    ("action_kind", "route", "perceptions"),
    [
        ("unknown", "KEEP_NEXT", ("listen",)),
        ("speak", "RESTART", ("listen",)),
        ("rest", "KEEP_NEXT", ("listen",)),
        ("rest", "REPLACE_NEXT", ("listen",)),
        ("speak", "KEEP_NEXT", ()),
        ("speak", "REPLACE_NEXT", ("missing",)),
    ],
)
def test_m4b_foundation_cr_m4b_002_invalid_think_fact_enters_e1(
    action_kind: str, route: str, perceptions: tuple[str, ...],
) -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(
            action_kind=action_kind, post_action_route=route,
            next_perceptions=perceptions,
        )
        errors: list[ErrorOccurred] = []
        bus.subscribe(ErrorOccurred, lambda event: collect(errors, event))
        errored = state_barrier(bus, "ERROR")
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        await wait(errored)
        assert errors == []
        await wait(idled)
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_002_payload_validator_does_not_mutate() -> None:
    payload = {"nested": {"value": 1}}
    observed: list[dict] = []

    class IdentityValidator:
        def validate(self, kind: str, candidate: dict) -> None:
            assert kind == "speak" and candidate is payload
            observed.append(candidate)

    async def run() -> None:
        bus, sm, *_ = make_sm(action_validator=IdentityValidator())
        sm._session = SessionContext("s", "button")
        response = LLMResponse(
            action_kind="speak", action_payload=payload,
            post_action_route="KEEP_NEXT", next_perceptions=("listen",),
        )
        await sm._validate_response(response)
        assert observed == [payload]
        assert response.action_payload is payload
        assert payload == {"nested": {"value": 1}}
    asyncio.run(run())


@pytest.mark.parametrize("ack_first", [True, False])
def test_m4b_foundation_fnd_wake_001_ack_and_open_join(ack_first: bool) -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        control = ControlledLifecycle()
        session_id = await _start_wake(sm, bus, control)
        await wait_until(lambda: bool(control.open_calls))
        if ack_first:
            sm._inbox.put_nowait(_WakeAckElapsed(session_id))
            await sm._inbox.join()
            assert sm.state == "WAKE" and not listen.started.is_set()
            control.open_release.set()
        else:
            control.open_release.set()
            await sm._inbox.join()
            assert sm.state == "WAKE" and not listen.started.is_set()
            sm._inbox.put_nowait(_WakeAckElapsed(session_id))
        await wait(listen.started)
        assert sm.state == "PERCEPTION"
        assert sm._session is not None
        assert sm._session.conversation_generation == 1
        assert sm._session.conversation_state == "ready"
        await _stop(sm, bus)
    asyncio.run(run())


async def wait_until(predicate) -> None:
    for _ in range(100):
        if predicate():
            return
        barrier = asyncio.Event()
        asyncio.get_running_loop().call_soon(barrier.set)
        await barrier.wait()
    raise AssertionError("barrier predicate was not reached")


def test_m4b_foundation_fnd_wake_002_clean_rejection_retries_generation() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        control = ControlledLifecycle()
        await sm.start()
        sm.set_conversation_lifecycle(control)
        woke = state_barrier(bus, "WAKE")
        await bus.publish(ButtonPressed("conversation", 1))
        await wait(woke)
        assert sm._session is not None
        sid = sm._session.session_id
        control.open_results.extend([
            ConversationOpenRejected(sid, 1, True, True),
            ConversationReady(sid, 2),
        ])
        control.open_release.set()
        sm._inbox.put_nowait(_WakeAckElapsed(sid))
        await wait(listen.started)
        assert control.open_calls == [(sid, 1), (sid, 2)]
        assert sm._session.conversation_generation == 2
        assert sm._session.turn_id == 1
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("engine_usable", [True, False])
def test_m4b_foundation_fnd_wake_002_unproven_rejection_is_e1(
    engine_usable: bool,
) -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        sid = await _start_wake(sm, bus, control)
        if not engine_usable:
            control.force_abort_report = ForceAbortReport(
                ("backend.cognition.reasoner.llm",)
            )
            recovery = RecoveryPort()
            sm._recovery = recovery
        control.open_results.append(
            ConversationOpenRejected(sid, 1, False, engine_usable)
        )
        errored = state_barrier(bus, "ERROR")
        control.open_release.set()
        await wait(errored)
        if not engine_usable:
            await wait_until(lambda: bool(recovery.begun))
            recovery.release.set()
        await sm._inbox.join()
        assert sm.state in {"ERROR", "IDLE"}
        assert control.abort_calls == 1
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("wrong_identity", ["session", "generation"])
def test_m4b_foundation_cr_m4b_002_open_ready_identity_mismatch_is_e1(
    wrong_identity: str,
) -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        sid = await _start_wake(sm, bus, control)
        control.open_results.append(ConversationReady(
            "other" if wrong_identity == "session" else sid,
            2 if wrong_identity == "generation" else 1,
        ))
        errored = state_barrier(bus, "ERROR")
        control.open_release.set()
        await wait(errored)
        await wait_until(lambda: control.abort_calls == 1)
        assert control.abort_calls == 1
        await sm._inbox.join()
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_wake_002_unusable_engine_waits_for_recovery() -> None:
    async def run() -> None:
        recovery = RecoveryPort()
        bus, sm, *_ = make_sm(recovery=recovery)
        control = ControlledLifecycle()
        control.force_abort_report = ForceAbortReport(("backend.cognition.reasoner.llm",))
        sid = await _start_wake(sm, bus, control)
        control.open_results.append(ConversationOpenRejected(sid, 1, True, False))
        errored = state_barrier(bus, "ERROR")
        idled = state_barrier(bus, "IDLE")
        control.open_release.set()
        await wait(errored)
        await wait_until(lambda: bool(recovery.begun))
        assert recovery.begun == [("backend.cognition.reasoner.llm",)]
        assert control.abort_calls == 1 and control.force_abort_calls == 1
        assert sm.state == "ERROR" and sm._session is not None
        assert sm._pending is not None and sm._pending.recovery_generation == 1
        recovery.release.set()
        await wait(idled)
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("result", [RuntimeError("open failed"), "wrong-result"])
def test_m4b_foundation_fnd_wake_002_open_exception_or_wrong_type_is_e1(result: object) -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        await _start_wake(sm, bus, control)
        control.open_results.append(result)
        errored = state_barrier(bus, "ERROR")
        control.open_release.set()
        await wait(errored)
        await sm._inbox.join()
        assert control.abort_calls == 1
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("signal", [InterruptRequested(), ErrorOccurred("test", "wake"), ShutdownRequested()])
def test_m4b_foundation_fnd_wake_002_open_interruption_converges(signal: object) -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        await _start_wake(sm, bus, control)
        await wait_until(lambda: bool(control.open_calls))
        await bus.publish(signal)  # type: ignore[arg-type]
        if isinstance(signal, ShutdownRequested):
            await sm.wait_stopped()
        else:
            await sm._inbox.join()
        assert control.abort_calls == 1
        assert sm._wake_timer is None
        assert sm._session is None
        await sm.stop()
    asyncio.run(run())


@pytest.mark.parametrize("route", ["KEEP_NEXT", "REPLACE_NEXT"])
def test_m4b_foundation_fnd_act_001_002_and_rep_001(route: str) -> None:
    async def run() -> None:
        bus, sm, listen, _, _, _, speak = make_sm(
            hold_perception=True, action_kind="speak",
            post_action_route=route, next_perceptions=("listen",),
        )
        control = ControlledLifecycle()
        control.open_release.set()
        sm._test_conversation_control = control
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        listen.release.set()
        await wait(speak.fact_sent)
        listen.started = asyncio.Event()
        listen.fact_sent = asyncio.Event()
        listen.release = asyncio.Event()
        sid = sm._session.session_id  # type: ignore[union-attr]
        generation = sm._session.conversation_generation  # type: ignore[union-attr]
        speak.release.set()
        if route == "KEEP_NEXT":
            await wait_until(lambda: sm._session is not None and sm._session.turn_id == 2)
            assert control.close_calls == []
            assert sm._session.conversation_generation == generation
        else:
            await wait_until(lambda: bool(control.close_calls))
            assert control.close_calls == [(sid, generation, "replacement")]
            assert len(control.open_calls) == 1
            control.close_release.set()
            await wait_until(lambda: len(control.open_calls) == 2)
            assert control.open_calls[1] == (sid, generation + 1)
            await wait_until(lambda: sm._session is not None and sm._session.turn_id == 2)
            assert sm._session.conversation_generation == generation + 1
            assert sm._session.session_id == sid
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_rep_002_repeated_replacement_preserves_session() -> None:
    async def run() -> None:
        bus, sm, listen, _, _, _, speak = make_sm(
            action_kind="speak", post_action_route="REPLACE_NEXT",
            next_perceptions=("listen",),
        )
        control = ControlledLifecycle()
        control.open_release.set()
        control.close_release.set()
        sm._test_conversation_control = control
        speak.release.set()
        reached = asyncio.Event()

        async def observe(event: StateChanged) -> None:
            if (
                event.new == "PERCEPTION"
                and sm._session is not None
                and sm._session.conversation_generation >= 3
            ):
                reached.set()

        bus.subscribe(StateChanged, observe)
        await start_perception(bus, sm, listen)
        assert sm._session is not None
        sid = sm._session.session_id
        await wait(reached)
        assert sm._session is not None
        assert sm._session.session_id == sid
        assert sm._session.conversation_generation >= 3
        assert sm._session.turn_id >= 3
        assert len(control.close_calls) >= 2
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_act_003_final_primary_then_one_rest() -> None:
    async def run() -> None:
        bus, sm, listen, _, _, rest, speak = make_sm(
            action_kind="speak", post_action_route="END_SESSION",
            next_perceptions=("listen",),
        )
        control = ControlledLifecycle()
        control.open_release.set()
        control.close_release.set()
        sm._test_conversation_control = control
        facts: list[ActionCompleted] = []
        bus.subscribe(ActionCompleted, lambda event: collect(facts, event))
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        await wait(speak.fact_sent)
        assert not rest.started.is_set()
        speak.release.set()
        await wait(idled)
        assert [fact.kind for fact in facts] == ["speak", "rest"]
        assert facts[0].correlation_id != facts[1].correlation_id
        assert len(control.close_calls) == 1
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("route", ["KEEP_NEXT", "REPLACE_NEXT"])
@pytest.mark.parametrize("action_kind", ["speak", "tool"])
@pytest.mark.parametrize("status", ["ok", "error"])
def test_m4b_foundation_cr_m4b_002_continuing_action_matrix(
    route: str, action_kind: str, status: str,
) -> None:
    async def run() -> None:
        bus, sm, listen, read, *_ = make_sm(
            hold_perception=True, action_kind=action_kind,
            post_action_route=route, next_perceptions=("read", "read", "missing"),
        )
        action = sm._workers.action(action_kind)
        action.action_status = status
        rest = sm._workers.action("rest")
        control = ControlledLifecycle()
        control.open_release.set()
        sm._test_conversation_control = control
        sm.set_external_message_control(ExternalControl())
        read.hold_after_fact = True
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        first_release = listen.release
        listen.started = asyncio.Event()
        listen.fact_sent = asyncio.Event()
        listen.release = asyncio.Event()
        first_release.set()
        await wait(action.fact_sent)
        assert sm._session is not None
        sid = sm._session.session_id
        generation = sm._session.conversation_generation
        expected = ("read",) if status == "ok" else ("listen",)
        action.release.set()
        if route == "REPLACE_NEXT":
            await wait_until(lambda: bool(control.close_calls))
            assert sm._session is not None
            assert sm._session.selected_perceptions == expected
            assert sm._session.model_admission_blocked
            assert control.open_calls == [(sid, generation)]
            control.close_release.set()
        target = read if status == "ok" else listen
        await wait(target.started)
        assert sm._session is not None
        assert sm._session.session_id == sid and sm._session.turn_id == 2
        assert sm._session.conversation_generation == generation + (route == "REPLACE_NEXT")
        assert not rest.started.is_set()
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize(
    ("action_kind", "status", "expected_kinds"),
    [
        ("speak", "ok", ["speak", "rest"]),
        ("speak", "error", ["speak", "rest"]),
        ("tool", "ok", ["tool", "rest"]),
        ("tool", "error", ["tool", "rest"]),
        ("rest", "ok", ["rest"]),
    ],
)
def test_m4b_foundation_cr_m4b_002_end_session_action_matrix(
    action_kind: str, status: str, expected_kinds: list[str],
) -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(
            action_kind=action_kind, post_action_route="END_SESSION",
            next_perceptions=("listen",),
        )
        primary = sm._workers.action(action_kind)
        primary.action_status = status
        if action_kind != "rest":
            sm._workers.action("rest").release.set()
        control = ControlledLifecycle()
        control.open_release.set()
        control.close_release.set()
        sm._test_conversation_control = control
        facts: list[ActionCompleted] = []
        states: list[StateChanged] = []
        bus.subscribe(ActionCompleted, lambda event: collect(facts, event))
        bus.subscribe(StateChanged, lambda event: collect(states, event))
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        if action_kind != "rest":
            await wait(primary.fact_sent)
            primary.release.set()
        await wait(idled)
        assert [fact.kind for fact in facts] == expected_kinds
        assert len({fact.correlation_id for fact in facts}) == len(facts)
        assert all(not (event.old == "ACTION" and event.new == "ACTION") for event in states)
        assert control.close_calls and control.close_calls[0][2] == "session_rest"
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_001_incomplete_session_close_advances() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(action_kind="rest")
        control = ControlledLifecycle()
        control.open_release.set()
        sm._test_conversation_control = control
        external = ExternalControl()
        sm.set_external_message_control(external)
        errored = state_barrier(bus, "ERROR")
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        await wait_until(lambda: bool(control.close_calls))
        sid = control.close_calls[0][0]
        control.close_results.append(
            ConversationCloseProof(sid, 1, False, False, True)
        )
        control.close_release.set()
        await wait(errored)
        await wait(idled)
        assert control.abort_calls == 1 and control.force_abort_calls == 0
        assert sm._pending is None and sm._session is None
        assert external.discarded == 1 and external.flushed == 0
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize(
    "proof_flags",
    [(False, True, True), (True, False, True)],
)
def test_m4b_foundation_cr_m4b_001_incomplete_replacement_never_opens_new_generation(
    proof_flags: tuple[bool, bool, bool],
) -> None:
    async def run() -> None:
        bus, sm, listen, _, _, _, speak = make_sm(
            hold_perception=True, action_kind="speak",
            post_action_route="REPLACE_NEXT", next_perceptions=("listen",),
        )
        control = ControlledLifecycle()
        control.open_release.set()
        sm._test_conversation_control = control
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        listen.release.set()
        await wait(speak.fact_sent)
        sid = sm._session.session_id  # type: ignore[union-attr]
        control.close_results.append(
            ConversationCloseProof(sid, 1, *proof_flags)
        )
        control.close_release.set()
        errored = state_barrier(bus, "ERROR")
        speak.release.set()
        await wait(errored)
        await sm._inbox.join()
        assert control.open_calls == [(sid, 1)]
        assert control.abort_calls == 1
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize("session_end", [False, True])
def test_m4b_foundation_cr_m4b_001_unusable_close_waits_for_recovery(
    session_end: bool,
) -> None:
    async def run() -> None:
        recovery = RecoveryPort()
        if session_end:
            bus, sm, listen, *_ = make_sm(action_kind="rest", recovery=recovery)
            action = None
        else:
            bus, sm, listen, _, _, _, action = make_sm(
                hold_perception=True, action_kind="speak",
                post_action_route="REPLACE_NEXT", next_perceptions=("listen",),
                recovery=recovery,
            )
        control = ControlledLifecycle()
        control.open_release.set()
        control.force_abort_report = ForceAbortReport(("backend.cognition.reasoner.llm",))
        sm._test_conversation_control = control
        await start_perception(bus, sm, listen)
        if action is not None:
            await wait(listen.fact_sent)
            listen.release.set()
            await wait(action.fact_sent)
            action.release.set()
        await wait_until(lambda: bool(control.close_calls))
        sid = control.close_calls[0][0]
        control.close_results.append(ConversationCloseProof(sid, 1, True, True, False))
        errored = state_barrier(bus, "ERROR")
        idled = state_barrier(bus, "IDLE")
        control.close_release.set()
        await wait(errored)
        await wait_until(lambda: bool(recovery.begun))
        assert control.force_abort_calls == 1
        assert recovery.begun == [("backend.cognition.reasoner.llm",)]
        assert sm.state == "ERROR" and sm._session is not None
        assert len(control.open_calls) == 1
        recovery.release.set()
        await wait(idled)
        assert sm._session is None
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_conv_001_002_interrupt_closes_then_discards() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(hold_perception=True)
        control = ControlledLifecycle()
        control.open_release.set()
        control.close_release.set()
        sm._test_conversation_control = control
        external = ExternalControl()
        sm.set_external_message_control(external)
        idled = state_barrier(bus, "IDLE")
        await start_perception(bus, sm, listen)
        sid = sm._session.session_id  # type: ignore[union-attr]
        await bus.publish(__import__("sbd.core.events", fromlist=["InterruptRequested"]).InterruptRequested())
        await wait(idled)
        assert control.close_calls == [(sid, 1, "session_interrupt")]
        assert external.discarded == 1
        assert sm._session is None and sm._in_flight == {}
        await _stop(sm, bus)
    asyncio.run(run())


async def collect(items: list, item) -> None:
    items.append(item)


def _invalid_llm_response_constructor_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    response_aliases = {"LLMResponse"}
    module_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if node.module == "sbd.core.events" and alias.name == "LLMResponse":
                    response_aliases.add(alias.asname or alias.name)
                elif node.module == "sbd.core" and alias.name == "events":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sbd.core.events":
                    module_aliases.add(alias.asname or alias.name)

    def dotted_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = dotted_name(node.value)
            return f"{prefix}.{node.attr}" if prefix is not None else None
        return None

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = dotted_name(node.value) if node.value is not None else None
            is_response = value in response_aliases or any(
                value == f"{module}.LLMResponse" for module in module_aliases
            )
            if not is_response:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in response_aliases:
                    response_aliases.add(target.id)
                    changed = True

    invalid: list[int] = []
    required = {
        "action_kind", "action_payload", "post_action_route", "next_perceptions",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = dotted_name(node.func)
        if not (
            called in response_aliases
            or any(called == f"{module}.LLMResponse" for module in module_aliases)
        ):
            continue
        names = {keyword.arg for keyword in node.keywords}
        if node.args or None in names or not required <= names:
            invalid.append(node.lineno)
    return sorted(invalid)


def test_m4b_foundation_fnd_life_001_wiring_fails_closed() -> None:
    async def run() -> None:
        sm = __import__("sbd.core.state_manager.manager", fromlist=["StateManager"]).StateManager(wake_ack_seconds=1)
        with pytest.raises(StateManagerWiringError):
            sm.set_conversation_lifecycle(ConversationControl())
        await sm.start()
        with pytest.raises(StateManagerWiringError):
            sm.set_conversation_lifecycle(None)
        sm.set_conversation_lifecycle(ConversationControl())
        with pytest.raises(StateManagerWiringError):
            sm.set_conversation_lifecycle(ConversationControl())
        sm.mark_input_producers_armed()
        with pytest.raises(StateManagerWiringError):
            sm.set_conversation_lifecycle(ConversationControl())
        sm._shutting_down = True
        await sm.stop()
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_002_missing_and_invalid_lifecycle_wiring() -> None:
    async def run() -> None:
        from sbd.core.state_manager.manager import StateManager

        missing = StateManager(wake_ack_seconds=1)
        await missing.start()
        with pytest.raises(StateManagerWiringError):
            missing.mark_input_producers_armed()
        with pytest.raises(StateManagerWiringError):
            missing.set_conversation_lifecycle(object())  # type: ignore[arg-type]
        missing._shutting_down = True
        await missing.stop()
    asyncio.run(run())


def test_m4b_foundation_fnd_rm_001_m2_late_fill_precedes_arm() -> None:
    async def run() -> None:
        from tests.test_m2_flows import _generation, _start_app

        app = await _start_app((_generation("rest", {}, []),))
        try:
            assert app.sm._conversation_set is True
            assert app.sm._conversation_control is not None
            assert app.sm._producers_armed is True
        finally:
            await app.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize("stale_field", ["session", "generation", "correlation", "task"])
def test_m4b_foundation_fnd_life_002_stale_notice_is_dropped(stale_field: str) -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        sid = await _start_wake(sm, bus, control)
        record = next(iter(sm._in_flight.values()))
        other_task = asyncio.create_task(asyncio.Event().wait())
        stale = _ConversationLifecycleCompleted(
            "open",
            "other" if stale_field == "session" else sid,
            record.conversation_generation + (stale_field == "generation"),
            record.correlation_id + (stale_field == "correlation"),
            other_task if stale_field == "task" else record.task,
        )
        await sm._handle_item(stale)
        assert sm._session is not None
        assert sm._session.conversation_generation == 1
        assert sm._session.conversation_state == "opening"
        assert record.correlation_id in sm._in_flight
        other_task.cancel()
        await asyncio.gather(other_task, return_exceptions=True)
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_002_premature_lifecycle_notice_is_dropped() -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        sid = await _start_wake(sm, bus, control)
        record = next(iter(sm._in_flight.values()))
        await sm._handle_item(_ConversationLifecycleCompleted(
            "open", sid, 1, record.correlation_id, record.task,
        ))
        assert not record.task.done()
        assert record.correlation_id in sm._in_flight
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_life_003_done_unproven_is_converged() -> None:
    async def run() -> None:
        control = ControlledLifecycle()
        control.open_release.set()
        task = asyncio.create_task(control.open_conversation("s", 1))
        await task
        record = InFlightRecord(
            1, "s", 0, "conversation_open", "conversation.open", control, task,
            conversation_generation=1, completion_mode="private_result",
        )
        result = await DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy()
        ).converge((record,), "error")
        assert result.destroyed_backends == ()
        assert control.abort_calls == 1
        assert record.cleanup_proven is True
    asyncio.run(run())


@pytest.mark.parametrize("level1_failure", ["timeout", "exception"])
def test_m4b_foundation_cr_m4b_001_level1_escalates_to_level2(
    level1_failure: str,
) -> None:
    async def run() -> None:
        control = ControlledLifecycle()
        control.force_abort_report = ForceAbortReport(("backend.cognition.reasoner.llm",))
        if level1_failure == "timeout":
            control.block_abort = True
        else:
            control.abort_error = RuntimeError("abort failed")
        task = asyncio.create_task(control.open_conversation("s", 1))
        await wait_until(lambda: bool(control.open_calls))
        record = InFlightRecord(
            7, "s", 0, "conversation_open", "conversation.open", control, task,
            conversation_generation=1, completion_mode="private_result",
        )
        result = await DefaultSessionConverger(
            timeouts=CancelTimeoutPolicy(
                abort_default_seconds=0.001, force_abort_default_seconds=0.1,
            )
        ).converge((record,), "error")
        assert result.destroyed_backends == ("backend.cognition.reasoner.llm",)
        assert control.abort_calls == 1 and control.force_abort_calls == 1
        assert record.request_terminal_proven and record.cleanup_proven
        assert record.force_abort_proven
    asyncio.run(run())


@pytest.mark.parametrize(
    ("level2_failure", "expected_stage"),
    [("timeout", "force_abort_timeout"), ("exception", "force_abort_error")],
)
def test_m4b_foundation_cr_m4b_001_level2_failure_is_level3_fatal(
    level2_failure: str, expected_stage: str,
) -> None:
    async def run() -> None:
        control = ControlledLifecycle()
        control.abort_error = RuntimeError("force escalation")
        if level2_failure == "timeout":
            control.block_force_abort = True
        else:
            control.force_abort_error = RuntimeError("force abort failed")
        task = asyncio.create_task(control.open_conversation("s", 1))
        await wait_until(lambda: bool(control.open_calls))
        record = InFlightRecord(
            8, "s", 0, "conversation_open", "conversation.open", control, task,
            conversation_generation=1, completion_mode="private_result",
        )
        with pytest.raises(ConvergenceFatalError) as caught:
            await DefaultSessionConverger(
                timeouts=CancelTimeoutPolicy(
                    abort_default_seconds=0.1, force_abort_default_seconds=0.001,
                )
            ).converge((record,), "error")
        assert caught.value.stage == expected_stage
        control.open_release.set()
        control.force_abort_release.set()
        await task
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_001_unusable_engine_requires_backend_identity() -> None:
    async def run() -> None:
        control = ControlledLifecycle()
        control.open_release.set()
        task = asyncio.create_task(control.open_conversation("s", 1))
        await task
        record = InFlightRecord(
            9, "s", 0, "conversation_open", "conversation.open", control, task,
            conversation_generation=1, completion_mode="private_result",
            request_terminal_proven=True, cleanup_proven=True, engine_usable=False,
        )
        with pytest.raises(ConvergenceFatalError) as caught:
            await DefaultSessionConverger(
                timeouts=CancelTimeoutPolicy()
            ).converge((record,), "error")
        assert caught.value.stage == "unusable_backend_unidentified"
        assert control.abort_calls == 1 and control.force_abort_calls == 1
    asyncio.run(run())


def test_m4b_foundation_fnd_phase_001_and_sm_001_models() -> None:
    context = SessionContext("", "button")
    assert (
        context.conversation_generation,
        context.conversation_state,
        context.wake_ack_ready,
        context.model_admission_blocked,
        context.post_action_route,
        context.normalized_next_perceptions,
        context.action_phase,
    ) == (0, "none", False, True, None, (), "none")
    assert InFlightRecord.__dataclass_fields__["completion_mode"].default == "worker_fact"
    assert InFlightRecord.__dataclass_fields__["request_terminal_proven"].default is False
    assert InFlightRecord.__dataclass_fields__["cleanup_proven"].default is False
    assert InFlightRecord.__dataclass_fields__["engine_usable"].default is None
    assert InFlightRecord.__dataclass_fields__["force_abort_proven"].default is False


def test_m4b_foundation_fnd_r1_001_clean_retry_is_canonical_keep() -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(
            hold_perception=True, action_kind="speak",
            post_action_route="KEEP_NEXT", next_perceptions=("listen",),
        )
        control = ControlledLifecycle()
        control.open_release.set()
        sm._test_conversation_control = control
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        listen.release.set()
        speak = sm._workers.action("speak")
        await wait(speak.fact_sent)
        assert sm._session is not None
        response = sm._session.llm_response
        assert response is not None
        assert (
            response.action_kind, response.post_action_route,
            response.next_perceptions,
        ) == ("speak", "KEEP_NEXT", ("listen",))
        generation = sm._session.conversation_generation
        listen.started = asyncio.Event()
        listen.fact_sent = asyncio.Event()
        listen.release = asyncio.Event()
        speak.release.set()
        await wait_until(lambda: sm._session is not None and sm._session.turn_id == 2)
        assert sm._session is not None
        assert sm._session.conversation_generation == generation
        assert control.close_calls == []
        await _stop(sm, bus)
    asyncio.run(run())


@pytest.mark.parametrize(
    "non_r1_kind", ["UNSUPPORTED_INPUT", "WIRING_FAILURE", "MUTATION_UNPROVEN"],
)
def test_m4b_foundation_fnd_r1_001_noncanonical_retry_claim_is_e1(
    non_r1_kind: str,
) -> None:
    async def run() -> None:
        bus, sm, listen, *_ = make_sm(
            action_kind=non_r1_kind, post_action_route="KEEP_NEXT",
            next_perceptions=("listen",),
        )
        errored = state_barrier(bus, "ERROR")
        await start_perception(bus, sm, listen)
        await wait(errored)
        assert sm.state == "ERROR"
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_002_reasoner_generation_and_admission_gate() -> None:
    async def run() -> None:
        bus, sm, listen, _, reasoner, *_ = make_sm(hold_perception=True)
        seen_generations: list[int] = []
        original_reason = reasoner.reason

        async def capture_reason(*args, conversation_generation: int):
            seen_generations.append(conversation_generation)
            await original_reason(*args, conversation_generation=conversation_generation)

        reasoner.reason = capture_reason
        await start_perception(bus, sm, listen)
        await wait(listen.fact_sent)
        listen.release.set()
        await wait(reasoner.started)
        assert seen_generations == [1]
        gated_bus, gated_sm, *_ = make_sm()
        gated_sm._session = SessionContext("gated", "button", conversation_generation=1)
        with pytest.raises(StateManagerInvariantViolation):
            await gated_sm._enter_think()
        assert not gated_sm._workers.reasoner().started.is_set()
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_cr_m4b_002_concurrent_lifecycle_is_rejected() -> None:
    async def run() -> None:
        bus, sm, *_ = make_sm()
        control = ControlledLifecycle()
        await _start_wake(sm, bus, control)
        with pytest.raises(StateManagerInvariantViolation):
            sm._start_conversation_close("replacement")
        assert len(sm._in_flight) == 1
        await _stop(sm, bus)
    asyncio.run(run())


def test_m4b_foundation_fnd_reg_001_structural_anti_weakening() -> None:
    root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for path in sorted((*root.joinpath("src").rglob("*.py"), *root.joinpath("tests").rglob("*.py"))):
        source = path.read_text(encoding="utf-8")
        for lineno in _invalid_llm_response_constructor_lines(source):
            violations.append(f"{path.relative_to(root)}:{lineno}")
    baseline_files = {
        Path(line.split("::", 1)[0])
        for line in root.joinpath(
            "docs/test_spec/baselines/m4b_foundation_node_ids.txt"
        ).read_text(encoding="utf-8").splitlines()
    }
    forbidden = {"skip", "xfail"}
    for relative in baseline_files:
        tree = ast.parse(root.joinpath(relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in forbidden:
                violations.append(f"{relative}:{node.lineno}")
    assert violations == []


def test_m4b_foundation_cr_m4b_002_ast_guard_resolves_alias_forms() -> None:
    source = """
from sbd.core.events import LLMResponse as Direct
import sbd.core.events as event_module
import sbd.core.events
from sbd.core import events as package_alias
Assigned = Direct
AssignedAgain = Assigned
Direct('speak', {}, 'KEEP_NEXT', ())
event_module.LLMResponse(action_kind='speak')
sbd.core.events.LLMResponse(action_kind='speak')
package_alias.LLMResponse(action_kind='speak')
AssignedAgain(action_kind='speak')
Direct(action_kind='speak', action_payload={}, post_action_route='KEEP_NEXT', next_perceptions=())
"""
    assert _invalid_llm_response_constructor_lines(source) == [8, 9, 10, 11, 12]
