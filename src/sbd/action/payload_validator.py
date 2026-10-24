"""Exact action-payload validation defined by Ch 9."""

from __future__ import annotations

import math
import re
from typing import Any, TypeAlias

from sbd.action.tool.registry import (
    JsonValue,
    ToolArgumentsInvalid,
    ToolRegistry,
    ToolRegistryError,
    UnknownTool,
)


JsonScalar: TypeAlias = None | bool | int | float | str
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")
_MAX_JSON_DEPTH = 32


class ActionPayloadValidationError(ValueError):
    """Sanitized validation failure without a copy of the rejected payload."""

    def __init__(self, *, action_kind: str, path: str, reason: str) -> None:
        self.action_kind = action_kind
        self.path = path
        self.reason = reason
        super().__init__(
            f"action_kind={action_kind} path={path} reason={reason}"
        )


class _JsonValueError(ValueError):
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(reason)


def validate_json_value(
    value: Any,
    *,
    path: str = "$",
    _depth: int = 0,
) -> None:
    """Validate a value without coercion, copying, or mutation."""
    if _depth > _MAX_JSON_DEPTH:
        raise _JsonValueError(path, "maximum JSON depth exceeded")
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise _JsonValueError(path, "number must be finite")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            validate_json_value(
                item,
                path=f"{path}[{index}]",
                _depth=_depth + 1,
            )
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _JsonValueError(path, "object keys must be strings")
            validate_json_value(
                item,
                path=f"{path}.{key}",
                _depth=_depth + 1,
            )
        return
    raise _JsonValueError(path, "value is not JSON-compatible")


class ActionPayloadValidator:
    """Synchronous, stateless validator shared by Reasoner and SM."""

    def __init__(self, *, tools: ToolRegistry) -> None:
        self._tools = tools

    def validate(self, action_kind: str, payload: dict[str, Any]) -> None:
        if action_kind not in {"speak", "tool", "rest"}:
            self._fail(action_kind, "$", "unknown action kind")
        if type(payload) is not dict:
            self._fail(action_kind, "$", "payload must be a plain object")
        try:
            validate_json_value(payload)
        except _JsonValueError as exc:
            self._fail(action_kind, exc.path, exc.reason)

        if action_kind == "speak":
            self._validate_speak(payload)
        elif action_kind == "tool":
            self._validate_tool(payload)
        else:
            self._validate_rest(payload)

    def _validate_speak(self, payload: dict[str, Any]) -> None:
        if set(payload) != {"text"}:
            self._fail("speak", "$", "expected exactly the text field")
        text = payload["text"]
        if type(text) is not str:
            self._fail("speak", "$.text", "expected string")
        if not text.strip():
            self._fail("speak", "$.text", "text must be non-empty")

    def _validate_tool(self, payload: dict[str, Any]) -> None:
        if set(payload) != {"name", "arguments"}:
            self._fail("tool", "$", "expected exactly name and arguments")
        name = payload["name"]
        if type(name) is not str or not _TOOL_NAME.fullmatch(name):
            self._fail("tool", "$.name", "expected dotted tool name")
        arguments = payload["arguments"]
        if type(arguments) is not dict:
            self._fail("tool", "$.arguments", "expected object")
        try:
            self._tools.validate(name, arguments)
        except UnknownTool:
            self._fail("tool", "$.name", "unknown tool")
        except ToolArgumentsInvalid:
            self._fail("tool", "$.arguments", "tool arguments rejected")
        except ToolRegistryError:
            self._fail("tool", "$.arguments", "tool registry unavailable")

    def _validate_rest(self, payload: dict[str, Any]) -> None:
        if payload:
            self._fail("rest", "$", "rest payload must be empty")

    @staticmethod
    def _fail(action_kind: str, path: str, reason: str) -> None:
        raise ActionPayloadValidationError(
            action_kind=action_kind,
            path=path,
            reason=reason,
        )


__all__ = [
    "ActionPayloadValidationError",
    "ActionPayloadValidator",
    "JsonScalar",
    "JsonValue",
    "validate_json_value",
]
