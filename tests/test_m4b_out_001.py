"""M4B-OUT-001 — deterministic winner renderer and constrained schema."""

from __future__ import annotations

import asyncio
import hashlib

import pytest

from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.tool import RegisteredTool, ToolRegistry
from sbd.cognition.llm import MockLLMEngineAdapter
from sbd.cognition.litert_lm.worker import (
    _build_response_schema, _litert_constraint_schema, _prewarm, _render_prompt,
    _validate_product_response,
)
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from tests.test_m2_wrk_003 import _bus_records, _response, _validator


def test_m4b_out_001_prewarm_prompt_matches_accepted_digest() -> None:
    value = {
        "perceptions": [{"kind": "listen", "status": "ok", "text": "Say ready."}],
        "pending_message_count": 0,
        "capabilities": {"perceptions": ["listen"], "actions": ["speak"], "tools": []},
    }
    prompt = _render_prompt(value)
    assert hashlib.sha256(prompt.encode()).hexdigest() == "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d"
    assert "Say ready." in prompt and "history" not in prompt.lower()


def test_m4b_out_001_branch_order_and_tool_schema_are_deterministic() -> None:
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen"], "actions": ["speak", "tool", "rest"],
            "tools": [
                {"name": "z.last", "description": "z", "input_schema": {}},
                {"name": "a.first", "description": "a", "input_schema": {}},
            ],
        },
    }
    branches = _build_response_schema(value)["oneOf"]
    assert [branch["properties"]["action_kind"]["const"] for branch in branches] == ["speak", "tool", "tool", "rest"]
    assert [branches[index]["properties"]["action_payload"]["properties"]["name"]["const"] for index in (1, 2)] == ["a.first", "z.last"]
    assert branches[1]["properties"]["action_payload"]["properties"]["arguments"] == {
        "type": "object",
    }
    assert all(branch["additionalProperties"] is False for branch in branches)


def test_m4b_out_001_litert_projection_only_removes_unsupported_unique_items() -> None:
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen", "look"],
            "actions": ["speak", "rest"], "tools": [],
        },
    }
    exact = _build_response_schema(value)
    projected = _litert_constraint_schema(exact)

    next_perceptions = exact["oneOf"][0]["properties"]["next_perceptions"]
    assert next_perceptions["uniqueItems"] is True
    assert "uniqueItems" not in str(projected)
    assert _build_response_schema(value) == exact


@pytest.mark.parametrize("response", [
    {"action_kind": "speak", "action_payload": {"text": ""}, "next_perceptions": ["listen"]},
    {"action_kind": "speak", "action_payload": {"text": "ok"}, "next_perceptions": ["look"]},
    {"action_kind": "rest", "action_payload": {}, "next_perceptions": ["listen"]},
])
def test_m4b_out_001_worker_rejects_semantically_invalid_constrained_output(response) -> None:
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {"perceptions": ["listen"], "actions": ["speak", "rest"], "tools": []},
    }
    with pytest.raises(ValueError, match="runtime"):
        _validate_product_response(response, value)


def test_m4b_out_001_tool_schema_is_object_only_and_reasoner_keeps_authority() -> None:
    value = {
        "perceptions": [], "pending_message_count": 0,
        "capabilities": {
            "perceptions": ["listen"], "actions": ["tool", "rest"],
            "tools": [{
                "name": "device.light.on", "description": "Turn on light",
                "input_schema": {
                    "type": "object",
                    "properties": {"level": {"type": "integer"}},
                    "required": ["level"],
                    "additionalProperties": False,
                },
            }],
        },
    }
    tool_branch = _build_response_schema(value)["oneOf"][0]
    assert tool_branch["properties"]["action_payload"]["properties"]["arguments"] == {
        "type": "object",
    }
    valid = {
        "action_kind": "tool",
        "action_payload": {"name": "device.light.on", "arguments": {"level": 1}},
        "next_perceptions": ["listen"],
    }
    _validate_product_response(valid, value)
    invalid = {
        **valid,
        "action_payload": {"name": "device.light.on", "arguments": {}},
    }
    _validate_product_response(invalid, value)

    handler_calls = 0
    async def handler(arguments):
        nonlocal handler_calls
        handler_calls += 1
        return {}
    def validate(arguments):
        if set(arguments) != {"level"} or type(arguments["level"]) is not int:
            raise ValueError("invalid level")
    tools = ToolRegistry()
    tools.register(RegisteredTool(
        name="device.light.on", description="Turn on light",
        input_schema=value["capabilities"]["tools"][0]["input_schema"],
        validate=validate, handler=handler,
    ))
    tools.seal()

    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(
            MockLLMEngineAdapter((_response("tool", invalid["action_payload"], ["listen"]),)),
            PromptBuilder(tools.schemas()), bus,
            {"listen", "speak", "tool"}.__contains__,
            ActionPayloadValidator(tools=tools),
        )
        await reasoner.reason("s", 1, 1, (), ())
        assert errors == [] and len(responses) == 1
        assert responses[0].action_kind == "speak"
        assert handler_calls == 0

    asyncio.run(scenario())


def test_m4b_out_001_prewarm_requires_schema_valid_nonempty_decode() -> None:
    class Runtime:
        def generate(self, value):
            return (
                {"action_kind": "speak", "action_payload": {"text": ""}, "next_perceptions": ["listen"]},
                {"decode_tokens": 1},
            )

    with pytest.raises(ValueError, match="runtime"):
        _prewarm(Runtime())


@pytest.mark.parametrize("response", [
    _response("speak", {"text": "ok"}, ["listen", "listen"]),
    _response("speak", {"text": "ok"}, ["listen", "look"]),
    _response("rest", {}, ["listen"]),
])
def test_m4b_out_001_reasoner_rejects_duplicate_unavailable_or_rest_perception(
    response,
) -> None:
    async def scenario() -> None:
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(
            MockLLMEngineAdapter((response,)), PromptBuilder(), bus,
            {"listen", "speak"}.__contains__, _validator(),
        )
        await reasoner.reason("session", 1, 1, (), ())
        assert errors == []
        assert len(responses) == 1
        assert responses[0].action_kind == "speak"
        assert responses[0].action_payload == {
            "text": "抱歉，我現在無法完成回應，請再試一次。",
        }
        assert responses[0].next_perceptions == ("listen",)

    asyncio.run(scenario())
