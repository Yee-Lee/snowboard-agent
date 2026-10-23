"""M5T-PAY-001: model semantic routes are validated before Tool execution."""

import asyncio
from contextlib import asynccontextmanager

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool.mock_send import MockSend
from sbd.action.tool.registry import ToolRegistry
from sbd.cognition.llm import AdmissionSnapshot, GenerationMetrics, ToolSemanticGeneration
from sbd.cognition.prompt_builder import ToolProjector
from sbd.cognition.reasoner import Reasoner
from sbd.core.event_bus import EventBus
from sbd.core.events import PerceptionResult


class FakeV4:
    def __init__(self, semantic, *, prefill=40, revision=0):
        self.control = object()
        self.conversation_revision = revision
        self.semantic = semantic
        self.prefill = prefill
        self.measured = []
        self.generated = []

    @asynccontextmanager
    async def serialized(self):
        yield

    def assert_conversation(self, session, generation):
        assert (session, generation) == ("session", 1)

    async def measure(self, session, generation, text, **extra):
        self.measured.append((text, extra))
        return AdmissionSnapshot("a" * 32, session, generation, "", 8,
                                 0 if self.conversation_revision == 0 else 10,
                                 self.prefill - (1 if self.conversation_revision == 0 else 0),
                                 self.prefill, 128, 1024)

    async def generate(self, snapshot, text, on_safe_text=None):
        self.generated.append(text)
        return ToolSemanticGeneration(self.semantic, (), GenerationMetrics(8, 0, 40, 40, 8, 50, 1, None, 2))


def test_tool_and_look_mapping_execute_no_handler_in_reasoner():
    async def run():
        send = MockSend()
        registry = ToolRegistry()
        registry.register(send.registered_tool())
        registry.seal()
        cases = (
            ({"intent": "tool", "text": "", "tool_name": "mock.send",
              "arguments": {"message": "買牛奶"}}, "tool", ("listen",)),
            ({"intent": "look", "text": "", "tool_name": "",
              "arguments": {"message": ""}}, "speak", ("look",)),
            ({"intent": "tool", "text": "", "tool_name": "unknown.send",
              "arguments": {"message": "買牛奶"}}, "speak", ("listen",)),
        )
        for semantic, kind, next_source in cases:
            llm = FakeV4(semantic)
            reasoner = Reasoner(llm, ToolProjector(), EventBus(),
                lambda capability: capability in {"listen", "look", "speak", "tool"},
                ActionPayloadValidator(tools=registry))
            fact = PerceptionResult("listen", "ok", "請幫我送出", {}, "session", 1, 2)
            response = await reasoner._tool_turn("session", 1, 3, (fact,), (), 1, None)
            assert response.action_kind == kind
            assert response.next_perceptions == next_source
            assert len(llm.generated) == 1
            assert send.calls == []
            if semantic["intent"] == "look":
                assert response.action_payload == {"text": "我看一下。"}
            if semantic["tool_name"] == "unknown.send":
                assert response.post_action_route == "REPLACE_NEXT"
    asyncio.run(run())


def test_first_turn_prefill_guard_blocks_generate_but_later_turn_can_continue():
    async def run():
        semantic = {"intent": "speak", "text": "你好。", "tool_name": "",
                    "arguments": {"message": ""}}
        registry = ToolRegistry()
        registry.seal()
        fact = PerceptionResult("listen", "ok", "你好", {}, "session", 1, 2)
        first = FakeV4(semantic, prefill=129)
        reasoner = Reasoner(first, ToolProjector(), EventBus(),
            lambda capability: capability in {"listen", "speak"},
            ActionPayloadValidator(tools=registry))
        from sbd.cognition.reasoner import _LocalProductFault
        try:
            await reasoner._tool_turn("session", 1, 3, (fact,), (), 1, None)
        except _LocalProductFault as exc:
            assert str(exc) == "INVALID_FRESH_PREFILL"
        else:
            assert False, "first-turn prefill guard was bypassed"
        assert first.generated == []
        later = FakeV4(semantic, prefill=180, revision=1)
        reasoner = Reasoner(later, ToolProjector(), EventBus(),
            lambda capability: capability in {"listen", "speak"},
            ActionPayloadValidator(tools=registry))
        response = await reasoner._tool_turn("session", 1, 3, (fact,), (), 1, None)
        assert response.action_kind == "speak"
        assert len(later.generated) == 1
    asyncio.run(run())


def test_look_bad_fact_returns_fixed_retry_without_llm_admission():
    async def run():
        registry = ToolRegistry()
        registry.seal()
        for facts in ("", "甲" * 513):
            llm = FakeV4({"intent": "speak", "text": "unused", "tool_name": "",
                          "arguments": {"message": ""}})
            reasoner = Reasoner(llm, ToolProjector(), EventBus(),
                lambda capability: capability in {"listen", "look", "speak"},
                ActionPayloadValidator(tools=registry))
            fact = PerceptionResult("look", "ok", facts, {}, "session", 2, 2)
            response = await reasoner._tool_turn("session", 2, 3, (fact,), (), 1, None)
            assert response.action_payload == {"text": "這次無法取得影像，請再試一次。"}
            assert response.next_perceptions == ("listen",)
            assert llm.measured == [] and llm.generated == []
    asyncio.run(run())
