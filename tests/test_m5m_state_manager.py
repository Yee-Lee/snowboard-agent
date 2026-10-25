"""M5M-SM-002 / M5M-CAN-001: opaque pending messages schedule read-only."""

import asyncio

from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, ButtonPressed, InterruptRequested, LLMResponse, PerceptionResult, ShutdownRequested
from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool.action import Tool
from sbd.action.tool.mqtt_command import MQTTCommandTool
from sbd.action.tool.registry import ToolRegistry
from sbd.input_events.mqtt import MQTTSendError
from sbd.input_events.external_message import ExternalMessageSource
from sbd.perception.read import Read
from tests.test_state_manager import ConversationControl, make_sm, start_perception, wait
from tests.test_m5t_look_state import make_look_sm


async def _until(predicate, timeout=2.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


def test_m5m_sm_002_pending_does_not_preempt_listen_and_drains_one_per_read():
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            hold_perception=True, action_kind="speak", action_payload={"text": "完成。"},
            next_perceptions=("listen",))
        sm._mqtt_read_only = True
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        facts = []
        async def record(fact):
            facts.append(fact)
        bus.subscribe(PerceptionResult, record)
        await source.start()
        await start_perception(bus, sm, listen)
        listen.publish_fact = False
        first = await source.ingest(channel="mqtt", text="結果一", metadata={
            "kind": "application_result", "status": "success"})
        second = await source.ingest(channel="mqtt", text="通知二", metadata={
            "kind": "notification", "status": "notice"})
        await _until(lambda: len(sm._external_control._items) == 2)
        await _until(lambda: len(sm._external_control._order) == 2)
        assert sm._session.selected_perceptions == ("listen",)
        assert len([fact for fact in facts if fact.kind == "read"]) == 0
        listen.release.set()
        await wait(speak.started)
        assert sm._session.selected_perceptions == ("listen",)
        listen.release.clear()
        speak.release.set()
        await _until(lambda: len([fact for fact in facts if fact.kind == "read"]) == 2)
        reads = [fact for fact in facts if fact.kind == "read"]
        assert [fact.extra["message_ids"] for fact in reads] == [(first,), (second,)]
        assert [fact.extra["messages"][0]["status"] for fact in reads] == ["success", "notice"]
        await _until(lambda: sm._session.selected_perceptions == ("listen",) and
                     sm._session.turn_id >= 4)
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
        await source.stop()
    asyncio.run(run())


def test_m5m_can_001_interrupt_discards_read_generation_without_late_speech():
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            hold_reasoner=True, action_kind="speak", action_payload={"text": "遲到回答"},
            next_perceptions=("listen",))
        sm._mqtt_read_only = True
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        await source.start()
        await sm.start()
        sm.set_conversation_lifecycle(sm._test_conversation_control)
        message_id = await source.ingest(channel="mqtt", text="通知", metadata={
            "kind": "notification", "status": "notice"})
        await _until(lambda: sm._session is not None)
        from sbd.core.state_manager.notices import _WakeAckElapsed
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(reasoner.started)
        assert sm._session.selected_perceptions == ("read",)
        assert sm.state == "THINK"
        await bus.publish(InterruptRequested())
        await _until(lambda: sm._session is None)
        assert not speak.started.is_set()
        assert not source.control._items
        listen.publish_fact = False
        listen.hold_after_fact = True
        await bus.publish(ButtonPressed("conversation", 1))
        await _until(lambda: sm._session is not None)
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(listen.started)
        assert sm._session.selected_perceptions == ("listen",)
        assert not speak.started.is_set()
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
        await source.stop()
    asyncio.run(run())


def test_m5m_sm_001_local_send_status_and_feedback_before_pending_read():
    async def scenario(outcome, with_pending):
        class Client:
            calls = 0
            async def publish_command(self):
                self.calls += 1
                if outcome == "error":
                    raise MQTTSendError("MQTT_SEND_NOT_CONNECTED")
                return "request"

        client = Client()
        registry = ToolRegistry()
        registry.register(MQTTCommandTool(client).registered_tool())
        registry.seal()
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="tool", action_payload={"name": "mock.send",
                "arguments": {"message": "啟用遠端連線"}},
            next_perceptions=("listen",), action_validator=ActionPayloadValidator(tools=registry))
        sm._mqtt_read_only = True
        sm._tool_feedback = {"ok": "已送出。", "error": "未能確認送出，請稍後再試。"}
        sm._workers._actions["tool"] = Tool(registry=registry, bus=bus)
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        statuses = []
        async def record(completed):
            if completed.kind == "tool":
                statuses.append(completed.status)
        bus.subscribe(ActionCompleted, record)
        spoken = []
        original_speak = speak.execute
        async def speak_execute(*args):
            spoken.append(args[-1]["text"])
            await original_speak(*args)
        speak.execute = speak_execute
        original_reason = reasoner.reason
        calls = 0
        async def reason(*args, last_dispatch_status=None, **kwargs):
            nonlocal calls
            calls += 1
            if calls > 1:
                reasoner.action_kind = "speak"
                reasoner.action_payload = {"text": "外部訊息：結果已收到。"}
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        await source.start()
        await start_perception(bus, sm, listen)
        listen.publish_fact = False
        await _until(lambda: len(spoken) == 1)
        listen.hold_after_fact = True
        expected = "已送出。" if outcome == "ok" else "未能確認送出，請稍後再試。"
        assert spoken == [expected]
        assert client.calls == 1 and statuses == [outcome]
        if with_pending:
            await source.ingest(channel="mqtt", text="外部結果", metadata={
                "kind": "application_result", "status": "success"})
            await _until(lambda: len(sm._external_control._items) == 1)
        speak.release.set()
        if with_pending:
            await _until(lambda: len(spoken) == 2)
            assert spoken == [expected, "外部訊息：結果已收到。"]
            assert client.calls == 1
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
        await source.stop()

    asyncio.run(scenario("ok", True))
    asyncio.run(scenario("error", False))


def test_m5m_sm_002_idle_notification_starts_read_before_listen():
    async def run():
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="speak", action_payload={"text": "外部通知：服務維護。"},
            next_perceptions=("listen",))
        sm._mqtt_read_only = True
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        facts = []
        async def record(fact):
            facts.append(fact)
        bus.subscribe(PerceptionResult, record)
        listen.publish_fact = False
        listen.hold_after_fact = True
        await source.start()
        await sm.start()
        sm.set_conversation_lifecycle(sm._test_conversation_control)
        await source.ingest(channel="mqtt", text="服務維護", metadata={
            "kind": "notification", "status": "notice"})
        await _until(lambda: sm._session is not None)
        from sbd.core.state_manager.notices import _WakeAckElapsed
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.started)
        assert [fact.kind for fact in facts] == ["read"]
        assert not listen.started.is_set()
        assert facts[0].extra["messages"][0]["status"] == "notice"
        speak.release.set()
        await wait(listen.started)
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
        await source.stop()
    asyncio.run(run())


def test_m5m_sm_002_look_finishes_before_pending_read():
    async def run():
        bus, sm, listen, look, reasoner, speak = make_look_sm()
        sm._mqtt_read_only = True
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        facts = []
        async def record(fact):
            facts.append(fact)
        bus.subscribe(PerceptionResult, record)
        async def delayed_look(session_id, turn_id, correlation_id, timeout_seconds):
            look.started.set()
            await look.release.wait()
            await bus.publish(PerceptionResult("look", "ok", "一本書", {},
                session_id, turn_id, correlation_id))
        look.perceive = delayed_look
        original_reason = reasoner.reason
        async def route_read(session_id, turn_id, correlation_id, results, pending,
                             *, conversation_generation, last_dispatch_status=None):
            if results[0].kind == "read":
                reasoner.calls.append((turn_id, ("read",), conversation_generation,
                                       last_dispatch_status))
                await bus.publish(LLMResponse(action_kind="speak",
                    action_payload={"text": "外部通知：已收到。"},
                    post_action_route="KEEP_NEXT", next_perceptions=("listen",),
                    session_id=session_id, turn_id=turn_id, correlation_id=correlation_id))
                return
            await original_reason(session_id, turn_id, correlation_id, results, pending,
                conversation_generation=conversation_generation,
                last_dispatch_status=last_dispatch_status)
        reasoner.reason = route_read
        await source.start()
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await _until(lambda: sm._session is not None)
        from sbd.core.state_manager.notices import _WakeAckElapsed
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.started)
        listen.publish_fact = False
        listen.hold_after_fact = True
        speak.release.set()
        await wait(look.started)
        await source.ingest(channel="mqtt", text="系統通知", metadata={
            "kind": "notification", "status": "notice"})
        await _until(lambda: bool(sm._external_control._items))
        assert [fact.kind for fact in facts] == ["listen"]
        look.release.set()
        await _until(lambda: [fact.kind for fact in facts] == ["listen", "look", "read"])
        await _until(lambda: len(reasoner.calls) == 3)
        assert [call[1] for call in reasoner.calls] == [("listen",), ("look",), ("read",)]
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
        await source.stop()
    asyncio.run(run())
