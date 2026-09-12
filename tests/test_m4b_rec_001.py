"""M4B-REC-001: actual SM post-action/close/recovery barriers."""
from __future__ import annotations

import asyncio

import pytest

from sbd.core.events import ButtonPressed, ShutdownRequested
from sbd.core.state_manager.convergence import ConvergenceFatalError
from sbd.core.state_manager.notices import _PlannedRecoveryCompleted
from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
from tests.test_state_manager import ConversationControl, make_sm, start_perception, state_barrier, wait


class PlannedControl(ConversationControl):
    def __init__(self, *, failure: str | None = None):
        self.recovery_pending = True
        self.close_entered = asyncio.Event()
        self.close_release = asyncio.Event()
        self.authorized = asyncio.Event()
        self.ready = asyncio.Event()
        self.authorizations = []
        self.opens = []
        self.ledger = ["mark_pending"]
        self.failure = failure

    async def open_conversation(self, session_id, generation):
        self.opens.append((session_id, generation))
        return ConversationReady(session_id, generation)

    async def close_conversation(self, session_id, generation, reason):
        self.ledger.append("close_entered")
        self.close_entered.set()
        await self.close_release.wait()
        self.ledger.append("close_proven")
        return ConversationCloseProof(session_id, generation, True, True, True)

    async def authorize_recovery(self, session_id, generation, proof):
        assert proof == ConversationCloseProof(session_id, generation, True, True, True)
        self.authorizations.append((session_id, generation, proof))
        self.ledger.append("authorized")
        self.authorized.set()
        await self.ready.wait()
        if self.failure:
            raise RuntimeError(self.failure)
        self.ledger.append("ready")
        self.recovery_pending = False


async def setup_case(failure=None):
    bus, sm, listen, _, reasoner, rest, speak = make_sm(
        hold_perception=True, hold_action=True, action_kind="speak",
        post_action_route="END_SESSION", action_payload={"text": "notice"},
    )
    control = PlannedControl(failure=failure)
    sm._test_conversation_control = control
    await start_perception(bus, sm, listen)
    session = sm._session
    listen.release.set()
    await wait(speak.started)
    return bus, sm, rest, speak, control, session


async def reach_authorization(bus, sm, rest, speak, control, session):
    assert control.authorizations == []
    assert not control.close_entered.is_set()
    speak.release.set()
    await wait(rest.started)
    assert control.authorizations == []
    assert not control.close_entered.is_set()
    rest.release.set()
    await wait(control.close_entered)
    assert control.authorizations == []
    control.close_release.set()
    await wait(control.authorized)
    assert sm._session is session
    assert sm.state != "IDLE"
    assert session.model_admission_blocked
    assert len(control.authorizations) == 1


async def shutdown(bus, sm, control):
    control.close_release.set()
    control.ready.set()
    await bus.publish(ShutdownRequested())
    await asyncio.wait_for(sm.wait_stopped(), 2)
    await sm.stop()


def test_m4b_rec_001_R02_R03_R04_R05_action_rest_close_then_ready():
    async def scenario():
        bus, sm, rest, speak, control, session = await setup_case()
        try:
            await reach_authorization(bus, sm, rest, speak, control, session)
            await bus.publish(ButtonPressed("conversation", 1))
            await asyncio.wait_for(sm._inbox.join(), 1)
            assert sm._session is session
            assert sm.state != "IDLE"
            assert len(control.opens) == 1
            idle = state_barrier(bus, "IDLE")
            control.ready.set()
            await wait(idle)
            assert sm._session is None
            assert len(control.authorizations) == 1
            assert control.ledger == ["mark_pending", "close_entered", "close_proven", "authorized", "ready"]
        finally:
            await shutdown(bus, sm, control)
    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["RM_TIMEOUT", "RM_EXCEPTION", "WRONG_KEY", "UNUSABLE_REPLACEMENT"])
def test_m4b_rec_001_R06_failure_is_supervised_without_next_request(failure):
    async def scenario():
        bus, sm, rest, speak, control, session = await setup_case(failure)
        await reach_authorization(bus, sm, rest, speak, control, session)
        control.ready.set()
        with pytest.raises(ConvergenceFatalError, match="PLANNED_RECOVERY_FAILED") as caught:
            await asyncio.wait_for(sm.wait_stopped(), 2)
        assert failure not in str(caught.value)
        assert sm.state != "IDLE"
        assert sm._session is session
        assert session.model_admission_blocked
        assert len(control.opens) == len(control.authorizations) == 1
        # Fatal dispatch is already stopped; explicit operator cleanup follows.
        sm._shutting_down = True
        await sm.stop()
    asyncio.run(scenario())


def test_m4b_rec_001_R07_stale_completion_cannot_release_barrier():
    async def scenario():
        bus, sm, rest, speak, control, session = await setup_case()
        try:
            await reach_authorization(bus, sm, rest, speak, control, session)
            waiter = sm._recovery_waiter
            assert waiter is not None
            sm._inbox.put_nowait(_PlannedRecoveryCompleted("stale-private-id", session.conversation_generation, waiter))
            sm._inbox.put_nowait(_PlannedRecoveryCompleted(session.session_id, session.conversation_generation + 1, waiter))
            sm._inbox.put_nowait(_PlannedRecoveryCompleted(session.session_id, session.conversation_generation, waiter))
            await asyncio.wait_for(sm._inbox.join(), 1)
            assert sm._recovery_waiter is waiter
            assert sm._session is session
            assert sm.state != "IDLE"
            assert len(control.authorizations) == 1
            idle = state_barrier(bus, "IDLE")
            control.ready.set()
            await wait(idle)
            sm._inbox.put_nowait(_PlannedRecoveryCompleted(session.session_id, session.conversation_generation, waiter))
            await asyncio.wait_for(sm._inbox.join(), 1)
            assert sm.state == "IDLE"
            assert len(control.authorizations) == 1
        finally:
            await shutdown(bus, sm, control)
    asyncio.run(scenario())


def test_m4b_rec_001_R04_shutdown_cancels_held_authorization_without_ready():
    async def scenario():
        bus, sm, rest, speak, control, session = await setup_case()
        await reach_authorization(bus, sm, rest, speak, control, session)
        waiter = sm._recovery_waiter
        assert waiter is not None and not waiter.done()
        await bus.publish(ShutdownRequested())
        await asyncio.wait_for(sm.wait_stopped(), 2)
        assert waiter.cancelled()
        assert not control.ready.is_set()
        assert "ready" not in control.ledger
        assert sm._session is None
        assert sm.state != "IDLE"
        assert len(control.opens) == len(control.authorizations) == 1
        await sm.stop()
    asyncio.run(scenario())


def test_m4b_rec_001_R06_unexpected_authorization_cancellation_is_fatal():
    async def scenario():
        bus, sm, rest, speak, control, session = await setup_case()
        await reach_authorization(bus, sm, rest, speak, control, session)
        waiter = sm._recovery_waiter
        assert waiter is not None and not waiter.done()
        waiter.cancel()
        with pytest.raises(ConvergenceFatalError, match="PLANNED_RECOVERY_FAILED"):
            await asyncio.wait_for(sm.wait_stopped(), 2)
        assert sm._session is session
        assert session.model_admission_blocked
        assert sm.state != "IDLE"
        assert len(control.opens) == len(control.authorizations) == 1
        assert "ready" not in control.ledger
        sm._shutting_down = True
        await sm.stop()
    asyncio.run(scenario())
