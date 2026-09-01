"""M4B-HIST-001 — semantic projection is turn-local and payload-free."""

from __future__ import annotations

import threading

import pytest

from scripts.m4b_target_metrics import MetricsError, validate_current_semantic_binding
from sbd.cognition.llm_child_protocol import encode_reasoning_input
from sbd.cognition.litert_lm.worker import LiteRTRuntime
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.core.events import PerceptionResult


def test_m4b_hist_001_second_turn_contains_no_first_turn_canary_or_pending_identity() -> None:
    builder = PromptBuilder()
    first = builder.build(
        perceptions=(PerceptionResult("listen", "ok", "PRIVATE_PRIOR_CANARY"),),
        pending_message_count=2, available_perceptions=("listen",), available_actions=("speak",),
    )
    second = builder.build(
        perceptions=(PerceptionResult("listen", "ok", "CURRENT_SEMANTIC_INPUT"),),
        pending_message_count=0, available_perceptions=("listen",), available_actions=("speak",),
    )
    assert "PRIVATE_PRIOR_CANARY" in str(encode_reasoning_input(first))
    encoded = encode_reasoning_input(second)
    assert "PRIVATE_PRIOR_CANARY" not in str(encoded)
    assert encoded["pending_message_count"] == 0 and "pending_message_ids" not in encoded


@pytest.mark.parametrize("prior_value", [
    "PRIOR_PERCEPTION_SENTINEL",
    "prior.tool.intent.arguments",
    "PRIOR_SPEAK_CONTENT",
    "PRIOR_NEXT_PERCEPTION",
    "PREFILLED_CONVERSATION_CANARY",
])
def test_m4b_hist_001_each_isolation_dimension_is_absent_from_current_projection(
    prior_value: str,
) -> None:
    builder = PromptBuilder()
    prior = builder.build(
        perceptions=(PerceptionResult("listen", "ok", prior_value),),
        pending_message_count=1, available_perceptions=("listen",),
        available_actions=("speak",),
    )
    current = builder.build(
        perceptions=(PerceptionResult("listen", "ok", "CURRENT_SEMANTIC_INPUT"),),
        pending_message_count=0, available_perceptions=("listen",),
        available_actions=("speak",),
    )
    assert prior_value in str(encode_reasoning_input(prior))
    encoded = encode_reasoning_input(current)
    assert prior_value not in str(encoded)
    assert "conversation" not in str(encoded).lower()


def test_m4b_hist_001_five_runtime_turns_use_fresh_closed_conversations() -> None:
    class Info:
        init_time_in_second = 0.0
        time_to_first_token_in_second = 0.001
        last_prefill_token_count = 1
        last_prefill_tokens_per_second = 1.0
        last_decode_token_count = 1
        last_decode_tokens_per_second = 1.0

    class Conversation:
        token_count = 1

        def __init__(self) -> None:
            self.closed = 0

        def render_message_to_string(self, prompt):
            return prompt

        def send_message(self, *args, **kwargs):
            return {"action_kind": "rest", "action_payload": {}, "next_perceptions": []}

        def get_benchmark_info(self):
            return Info()

        def close(self):
            self.closed += 1

    class Engine:
        def __init__(self) -> None:
            self.conversations: list[Conversation] = []

        def create_conversation(self, **kwargs):
            conversation = Conversation()
            self.conversations.append(conversation)
            return conversation

        def tokenize(self, rendered):
            return [1]

    engine = Engine()
    runtime = LiteRTRuntime.__new__(LiteRTRuntime)
    runtime._engine = engine
    runtime._response_format = type("Format", (), {"json": staticmethod(lambda schema: schema)})
    runtime._constraint = object()
    runtime._cancelled_error = type("Cancelled", (RuntimeError,), {})
    runtime._active = None
    runtime._pending_cancel = False
    runtime._cancel_requested = False
    runtime._lock = threading.Lock()
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {"perceptions": [], "actions": ["rest"], "tools": []},
    }
    for _ in range(5):
        response, _ = runtime.generate(value)
        validate_current_semantic_binding(response, {
            "expected_kind": "rest", "expected_tool_name": None,
            "expected_next_perceptions": [],
        })
    assert len({id(item) for item in engine.conversations}) == 5
    assert [item.closed for item in engine.conversations] == [1] * 5


def test_m4b_hist_001_schema_only_prior_state_cannot_false_pass_current_semantics() -> None:
    prior = {
        "action_kind": "tool",
        "action_payload": {"name": "prior.device.tool", "arguments": {}},
        "next_perceptions": ["look"],
    }
    current = {
        "expected_kind": "speak", "expected_tool_name": None,
        "expected_next_perceptions": ["listen"],
    }
    with pytest.raises(MetricsError, match="semantic binding"):
        validate_current_semantic_binding(prior, current)
