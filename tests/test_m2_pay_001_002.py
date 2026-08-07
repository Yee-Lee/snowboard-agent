"""M2-PAY-001/002 action payload and ToolRegistry contract tests."""

from __future__ import annotations

import asyncio
import copy
import math

import pytest

from sbd.action.payload_validator import (
    ActionPayloadValidationError,
    ActionPayloadValidator,
)
from sbd.action.tool.registry import (
    DuplicateToolName,
    RegisteredTool,
    ToolRegistry,
    ToolRegistrySealed,
    UnknownTool,
)


def _closed_object_schema() -> dict:
    return {
        "type": "object",
        "properties": {"on": {"type": "boolean"}},
        "additionalProperties": False,
    }


def _registered_tool(name: str, calls: list[dict]) -> RegisteredTool:
    dispatch_calls = calls if calls is not None else []

    def validate(arguments: dict) -> None:
        if set(arguments) != {"on"} or type(arguments["on"]) is not bool:
            raise ValueError("secret-payload-must-not-leak")

    async def handler(arguments: dict) -> dict:
        dispatch_calls.append(copy.deepcopy(arguments))
        return {"accepted": True}

    return RegisteredTool(
        name=name,
        description="Set a deterministic fixture light",
        input_schema=_closed_object_schema(),
        validate=validate,
        handler=handler,
    )


def _make_registry(
    calls: list[dict] | None = None,
    *,
    name: str = "light.set",
) -> ToolRegistry:
    dispatch_calls = calls if calls is not None else []
    registry = ToolRegistry()
    registry.register(_registered_tool(name, dispatch_calls))
    return registry


def test_m2_pay_001_exact_action_schemas_do_not_mutate_inputs() -> None:
    registry = _make_registry()
    registry.seal()
    validator = ActionPayloadValidator(tools=registry)
    valid = (
        ("speak", {"text": "  hello  "}),
        ("tool", {"name": "light.set", "arguments": {"on": True}}),
        ("rest", {}),
    )
    for kind, payload in valid:
        before = copy.deepcopy(payload)
        validator.validate(kind, payload)
        assert payload == before

    invalid = (
        ("speak", {}),
        ("speak", {"text": ""}),
        ("speak", {"text": " ", "speed": 1}),
        ("speak", {"text": 1}),
        ("tool", {"name": "short", "arguments": {}}),
        ("tool", {"name": "light.set", "arguments": []}),
        ("tool", {"name": "light.set", "arguments": {"on": "yes"}}),
        ("rest", {"farewell": True}),
    )
    for kind, payload in invalid:
        before = copy.deepcopy(payload)
        with pytest.raises(ActionPayloadValidationError):
            validator.validate(kind, payload)
        assert payload == before


def test_m2_pay_001_rejects_non_json_depth_and_sanitizes_errors() -> None:
    registry = _make_registry()
    registry.seal()
    validator = ActionPayloadValidator(tools=registry)
    sentinel = "secret-payload-must-not-leak"
    invalid_values = (
        b"bytes",
        ("tuple",),
        {"set"},
        object(),
        math.nan,
        math.inf,
        {1: "non-string-key"},
    )
    for value in invalid_values:
        payload = {"text": value}
        with pytest.raises(ActionPayloadValidationError) as captured:
            validator.validate("speak", payload)
        assert sentinel not in str(captured.value)
        assert repr(payload) not in str(captured.value)

    nested: object = "leaf"
    for _ in range(34):
        nested = [nested]
    with pytest.raises(ActionPayloadValidationError, match="maximum JSON depth"):
        validator.validate("speak", {"text": nested})

    with pytest.raises(ActionPayloadValidationError) as captured:
        validator.validate(
            "tool",
            {"name": "light.set", "arguments": {"secret": sentinel}},
        )
    assert sentinel not in str(captured.value)
    assert "$.arguments" in str(captured.value)


def test_m2_pay_002_registry_seal_schema_view_and_pure_validation() -> None:
    calls: list[dict] = []
    registry = _make_registry(calls, name="zeta.set")
    second = _registered_tool("alpha.set", [])
    registry.register(second)

    with pytest.raises(DuplicateToolName):
        registry.register(second)
    registry.seal()
    with pytest.raises(ToolRegistrySealed):
        registry.register(second)

    registry.validate("zeta.set", {"on": True})
    assert calls == []
    schemas = registry.schemas()
    assert tuple(schema["name"] for schema in schemas) == ("alpha.set", "zeta.set")
    assert set(schemas[0]) == {"name", "description", "input_schema"}
    schemas[0]["input_schema"]["properties"].clear()
    assert registry.schemas()[0]["input_schema"]["properties"] == {
        "on": {"type": "boolean"}
    }


def test_m2_pay_002_dispatches_once_and_rejects_unknown_before_handler() -> None:
    calls: list[dict] = []
    registry = _make_registry(calls)
    registry.seal()

    result = asyncio.run(registry.dispatch("light.set", {"on": True}))
    assert result == {"accepted": True}
    assert calls == [{"on": True}]

    with pytest.raises(UnknownTool):
        asyncio.run(registry.dispatch("missing.tool", {"on": True}))
    assert calls == [{"on": True}]
