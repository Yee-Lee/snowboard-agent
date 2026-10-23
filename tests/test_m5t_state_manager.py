"""M5T-SM-001: dispatch is joined before fixed feedback and next listen."""

import asyncio

from sbd.core.events import InterruptRequested, ShutdownRequested
from tests.test_m2_sm_flows import _validator
from tests.test_state_manager import make_sm, start_perception, wait


def test_tool_feedback_waits_for_primary_and_feedback_joins():
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="tool", action_payload={"name": "fixture.run", "arguments": {}},
            next_perceptions=("listen",), action_validator=_validator(with_tool=True))
        sm._tool_feedback = {"ok": "已送出。", "error": "未能確認送出，請稍後再試。"}
        displayed = []
        sm.set_feedback_display(displayed.append)
        statuses = []
        original_reason = reasoner.reason
        async def reason(*args, last_dispatch_status=None, **kwargs):
            statuses.append(last_dispatch_status)
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        spoken = []
        original_speak = speak.execute
        async def speak_execute(*args):
            spoken.append(args[-1]["text"])
            await original_speak(*args)
        speak.execute = speak_execute
        await start_perception(bus, sm, listen)
        tool = sm._workers.action("tool")
        await wait(tool.started)
        await wait(tool.fact_sent)
        assert sm.state == "ACTION" and spoken == []
        tool.release.set()
        await wait(speak.started)
        await wait(speak.fact_sent)
        assert spoken == ["已送出。"]
        assert displayed == ["已送出。"]
        assert sm.state == "ACTION"
        assert sm._session.action_phase == "tool_feedback"
        assert [record.phase for record in sm._in_flight.values()] == ["action_tool_feedback"]
        first_correlation = sm._session.llm_response.correlation_id
        assert next(iter(sm._in_flight)) != first_correlation
        speak.release.set()
        for _ in range(20):
            await asyncio.sleep(0)
            if sm._session.turn_id == 2:
                break
        assert sm._session.turn_id == 2
        assert sm._session.last_dispatch_status == "ok"
        assert sm._session.selected_perceptions == ("listen",)
        assert statuses == [None]
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_interrupt_during_feedback_does_not_start_next_listen():
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="tool", action_payload={"name": "fixture.run", "arguments": {}},
            next_perceptions=("listen",), action_validator=_validator(with_tool=True))
        sm._tool_feedback = {"ok": "已送出。", "error": "未能確認送出，請稍後再試。"}
        original_reason = reasoner.reason
        async def reason(*args, last_dispatch_status=None, **kwargs):
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        await start_perception(bus, sm, listen)
        tool = sm._workers.action("tool")
        await wait(tool.fact_sent)
        tool.release.set()
        await wait(speak.fact_sent)
        assert sm._session.action_phase == "tool_feedback"
        await bus.publish(InterruptRequested())
        for _ in range(20):
            await asyncio.sleep(0)
            if sm._session is None:
                break
        assert sm._session is None
        assert speak.release.is_set()
        assert reasoner.started.is_set()
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())
