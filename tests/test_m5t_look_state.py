"""M5T-SM-002: Look follows preparation without another microphone turn."""

import asyncio

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool.registry import ToolRegistry
from sbd.core.event_bus import EventBus
from sbd.core.events import (ActionCompleted, ButtonPressed, LLMResponse,
                             PerceptionResult, InterruptRequested, ShutdownRequested)
from sbd.core.resource_manager.catalog import WorkerCatalog
from sbd.core.state_manager.manager import StateManager
from sbd.core.state_manager.notices import _WakeAckElapsed
from tests.test_state_manager import ConversationControl, Worker, state_barrier, wait


class LookReasoner(Worker):
    _product = True

    def __init__(self, bus):
        super().__init__(bus, "reasoner", "think")
        self.calls = []

    async def reason(self, session_id, turn_id, correlation_id, results, pending,
                     *, conversation_generation, last_dispatch_status=None):
        self.calls.append((turn_id, tuple(item.kind for item in results),
                           conversation_generation, last_dispatch_status))
        is_look = results[0].kind == "look"
        response = LLMResponse(
            action_kind="speak",
            action_payload={"text": "一本書。" if is_look else "我看一下。"},
            post_action_route="KEEP_NEXT",
            next_perceptions=("listen",) if is_look else ("look",),
            session_id=session_id, turn_id=turn_id, correlation_id=correlation_id,
        )
        await self.bus.publish(response)


def make_look_sm(*, look_status="ok"):
    bus = EventBus()
    listen = Worker(bus, "listen", "perception")
    look = Worker(bus, "look", "perception")
    async def perceive(session_id, turn_id, correlation_id, timeout_seconds):
        look.started.set()
        await bus.publish(PerceptionResult("look", look_status,
            "偵測到一本書。" if look_status == "ok" else None, {},
            session_id, turn_id, correlation_id))
        look.fact_sent.set()
    look.perceive = perceive
    reasoner = LookReasoner(bus)
    speak = Worker(bus, "speak", "action", hold_after_fact=True)
    rest = Worker(bus, "rest", "action")
    registry = ToolRegistry()
    registry.seal()
    catalog = WorkerCatalog()
    catalog.register_perception("listen", listen)
    catalog.register_perception("look", look)
    catalog.set_reasoner(reasoner)
    catalog.register_action("speak", speak)
    catalog.register_action("rest", rest)
    catalog.seal()
    sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=60,
        action_validator=ActionPayloadValidator(tools=registry),
        tool_feedback={"ok": "已送出。", "error": "未能確認送出，請稍後再試。"})
    return bus, sm, listen, look, reasoner, speak


def test_look_starts_next_perception_in_same_conversation():
    async def run():
        bus, sm, listen, look, reasoner, speak = make_look_sm()
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.started)
        assert sm._session.look_generation == 1
        speak.release.set()
        await wait(look.started)
        for _ in range(20):
            await asyncio.sleep(0)
            if len(reasoner.calls) == 2:
                break
        assert reasoner.calls == [(1, ("listen",), 1, None), (2, ("look",), 1, None)]
        assert sm._session.turn_id == 2
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_look_error_uses_fixed_speech_without_second_llm_call():
    async def run():
        bus, sm, listen, look, reasoner, speak = make_look_sm(look_status="error")
        spoken = []
        original = speak.execute
        async def execute(*args):
            spoken.append(args[-1]["text"])
            await original(*args)
        speak.execute = execute
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.fact_sent)
        speak.release.set()
        await wait(look.fact_sent)
        for _ in range(20):
            await asyncio.sleep(0)
            if len(spoken) == 2:
                break
        assert spoken == ["我看一下。", "這次無法取得影像，請再試一次。"]
        assert len(reasoner.calls) == 1
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_look_generation_change_discards_observation_and_replaces_conversation():
    async def run():
        bus, sm, listen, look, reasoner, speak = make_look_sm()
        spoken = []
        original = speak.execute
        async def execute(*args):
            spoken.append(args[-1]["text"])
            await original(*args)
        speak.execute = execute
        async def delayed_look(session_id, turn_id, correlation_id, timeout_seconds):
            look.started.set()
            await look.release.wait()
            await bus.publish(PerceptionResult("look", "ok", "SECRET_VISION_FACT_88", {},
                session_id, turn_id, correlation_id))
            look.fact_sent.set()
        look.perceive = delayed_look
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.fact_sent)
        speak.release.set()
        await wait(look.started)
        sm._session.conversation_generation += 1
        look.release.set()
        await wait(look.fact_sent)
        for _ in range(40):
            await asyncio.sleep(0)
            if len(spoken) == 2:
                break
        assert spoken == ["我看一下。", "這次無法接續原問題，請再說一次。"]
        assert len(reasoner.calls) == 1
        assert sm._session.perception_results == []
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())


def test_interrupt_waiting_look_discards_old_observation():
    async def run():
        bus, sm, listen, look, reasoner, speak = make_look_sm()
        async def delayed_look(session_id, turn_id, correlation_id, timeout_seconds):
            look.started.set()
            await look.release.wait()
        look.perceive = delayed_look
        idle = state_barrier(bus, "IDLE")
        await sm.start()
        sm.set_conversation_lifecycle(ConversationControl())
        await bus.publish(ButtonPressed("conversation", 1))
        await sm._inbox.join()
        sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
        await wait(speak.fact_sent)
        speak.release.set()
        await wait(look.started)
        await bus.publish(InterruptRequested())
        await wait(idle)
        assert sm._session is None
        assert look.release.is_set()
        assert len(reasoner.calls) == 1
        await bus.publish(ShutdownRequested())
        await sm.wait_stopped()
        await sm.stop()
    asyncio.run(run())
