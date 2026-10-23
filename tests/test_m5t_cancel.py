"""M5T-CAN-001: interrupt of a waiting mock dispatch cannot start feedback."""

import asyncio

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool.action import Tool
from sbd.action.tool.mock_send import MockSend
from sbd.action.tool.registry import ToolRegistry
from sbd.core.event_bus import EventBus
from sbd.core.events import (ActionCompleted, ButtonPressed, InterruptRequested,
                             ShutdownRequested)
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.notices import _WakeAckElapsed
from tests.test_state_manager import ConversationControl, Worker, state_barrier, wait


def test_interrupt_waiting_mock_dispatch_has_no_late_success_or_feedback():
    async def run():
        bus = EventBus()
        send = MockSend(blocked=True)
        registry = ToolRegistry()
        registry.register(send.registered_tool())
        registry.seal()
        listen = Worker(bus, "listen", "perception")
        reasoner = Worker(bus, "reasoner", "think", action_kind="tool",
            next_perceptions=("listen",),
            action_payload={"name": "mock.send", "arguments": {"message": "買牛奶"}})
        original_reason = reasoner.reason
        async def reason(*args, last_dispatch_status=None, **kwargs):
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        speak = Worker(bus, "speak", "action")
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("tool", Tool(registry=registry, bus=bus))
        catalog.register_action("speak", speak)
        catalog.register_action("rest", Worker(bus, "rest", "action"))
        catalog.seal()
        sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=60,
            action_validator=ActionPayloadValidator(tools=registry),
            tool_feedback={"ok": "已送出。", "error": "未能確認送出，請稍後再試。"})
        tool_facts = []
        async def on_action(fact: ActionCompleted):
            if fact.kind == "tool":
                tool_facts.append(fact.status)
        bus.subscribe(ActionCompleted, on_action)
        idled = state_barrier(bus, "IDLE")
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(send.entered)
        await bus.publish(InterruptRequested())
        await wait(idled)
        send.release.set()
        await sm._inbox.join()
        assert send.calls == ["買牛奶"]
        assert tool_facts == []
        assert speak.started.is_set() is False
        assert sm._session is None
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())
