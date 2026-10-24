"""M5T-SM-001: dispatch is joined before fixed feedback and next listen."""

import asyncio

from sbd.core.events import InterruptRequested, PerceptionResult, ShutdownRequested
from tests.test_m2_sm_flows import _validator
from tests.test_state_manager import make_sm, start_perception, state_barrier, wait


def _tool_feedback_flow(status):
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="tool", action_payload={"name": "fixture.run", "arguments": {}},
            next_perceptions=("listen",), action_validator=_validator(with_tool=True))
        tool = sm._workers.action("tool")
        tool.action_status = status
        sm._tool_feedback = {"ok": "已送出。", "error": "未能確認送出，請稍後再試。"}
        displayed = []
        sm.set_feedback_display(displayed.append)
        statuses = []
        original_reason = reasoner.reason
        async def reason(*args, last_dispatch_status=None, **kwargs):
            statuses.append(last_dispatch_status)
            if len(statuses) > 1:
                reasoner.action_kind = "speak"
                reasoner.action_payload = {"text": "ok"}
                reasoner.post_action_route = (
                    "KEEP_NEXT" if len(statuses) == 2 else "END_SESSION"
                )
                reasoner.next_perceptions = ("listen",) if len(statuses) == 2 else ()
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        spoken = []
        original_speak = speak.execute
        async def speak_execute(*args):
            spoken.append(args[-1]["text"])
            await original_speak(*args)
        speak.execute = speak_execute
        await start_perception(bus, sm, listen)
        await wait(tool.started)
        await wait(tool.fact_sent)
        listen.publish_fact = False
        assert sm.state == "ACTION" and spoken == []
        tool.release.set()
        await wait(speak.started)
        await wait(speak.fact_sent)
        feedback = "已送出。" if status == "ok" else "未能確認送出，請稍後再試。"
        assert spoken == [feedback]
        assert displayed == [feedback]
        assert sm.state == "ACTION"
        assert sm._session.action_phase == "tool_feedback"
        assert [record.phase for record in sm._in_flight.values()] == ["action_tool_feedback"]
        first_correlation = sm._session.llm_response.correlation_id
        assert next(iter(sm._in_flight)) != first_correlation
        speak.release.set()

        async def feed_listen(turn_id):
            async def ready():
                while (sm.state != "PERCEPTION" or sm._session is None
                       or sm._session.turn_id != turn_id or not sm._in_flight):
                    await asyncio.sleep(0)
            await asyncio.wait_for(ready(), timeout=1)
            assert sm.state == "PERCEPTION" and sm._session.turn_id == turn_id
            correlation_id = next(iter(sm._in_flight))
            await bus.publish(PerceptionResult(
                "listen", "ok", "listen", session_id=sm._session.session_id,
                turn_id=turn_id, correlation_id=correlation_id))

        await feed_listen(2)
        assert sm._session.turn_id == 2
        assert sm._session.last_dispatch_status == status
        assert sm._session.selected_perceptions == ("listen",)
        idled = state_barrier(bus, "IDLE")
        await feed_listen(3)
        await wait(idled)
        assert statuses == [None, status, None]
        assert spoken == [feedback, "ok", "ok"]
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_tool_feedback_waits_for_primary_and_feedback_joins():
    _tool_feedback_flow("ok")


def test_tool_error_speaks_failure_feedback_and_passes_error_status_once():
    _tool_feedback_flow("error")


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
