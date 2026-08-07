"""Sealed tool registry defined by Ch 9."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, TypeAlias

from sbd.core.lifecycle import ForceAbortReport


JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
ToolHandler: TypeAlias = Callable[[dict[str, JsonValue]], Awaitable[dict[str, JsonValue]]]
ToolValidator: TypeAlias = Callable[[dict[str, JsonValue]], None]

_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")


class ToolExecutionControl(Protocol):
    async def abort(self) -> None: ...
    async def force_abort(self) -> ForceAbortReport: ...


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict[str, JsonValue]
    validate: ToolValidator
    handler: ToolHandler
    execution_control: ToolExecutionControl | None = None


class ToolRegistryError(RuntimeError):
    """Base registry error whose text never includes payload data."""


class DuplicateToolName(ToolRegistryError):
    pass


class ToolRegistrySealed(ToolRegistryError):
    pass


class UnknownTool(ToolRegistryError):
    pass


class ToolArgumentsInvalid(ToolRegistryError):
    pass


class ToolRegistry:
    """Startup-mutable, runtime-sealed registry of deterministic tool intents."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._sealed = False

    def register(self, tool: RegisteredTool) -> None:
        if self._sealed:
            raise ToolRegistrySealed("tool registry is sealed")
        if not isinstance(tool, RegisteredTool):
            raise TypeError("tool must be RegisteredTool")
        if not _TOOL_NAME.fullmatch(tool.name):
            raise ValueError("tool name must be a dotted lowercase namespace")
        if not isinstance(tool.description, str) or not tool.description.strip():
            raise ValueError("tool description must be a non-empty string")
        if not callable(tool.validate) or not callable(tool.handler):
            raise TypeError("tool validator and handler must be callable")
        if tool.name in self._tools:
            raise DuplicateToolName(f"duplicate tool name: {tool.name}")

        from sbd.action.payload_validator import validate_json_value

        validate_json_value(tool.input_schema, path="$.input_schema")
        schema = tool.input_schema
        if (
            type(schema) is not dict
            or schema.get("type") != "object"
            or type(schema.get("properties")) is not dict
            or schema.get("additionalProperties") is not False
        ):
            raise ValueError("tool input_schema must define a closed object")

        self._tools[tool.name] = RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_schema=copy.deepcopy(tool.input_schema),
            validate=tool.validate,
            handler=tool.handler,
            execution_control=tool.execution_control,
        )

    def seal(self) -> None:
        self._sealed = True

    def contains(self, name: str) -> bool:
        return name in self._tools

    def validate(self, name: str, arguments: dict[str, JsonValue]) -> None:
        tool = self._runtime_tool(name)
        from sbd.action.payload_validator import validate_json_value

        try:
            validate_json_value(arguments, path="$.arguments")
            tool.validate(arguments)
        except ToolRegistryError:
            raise
        except Exception as exc:
            raise ToolArgumentsInvalid(
                f"arguments rejected for tool: {name}"
            ) from exc

    def schemas(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": copy.deepcopy(tool.input_schema),
            }
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        )

    async def dispatch(
        self,
        name: str,
        arguments: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        tool = self._runtime_tool(name)
        self.validate(name, arguments)
        result = await tool.handler(arguments)
        from sbd.action.payload_validator import validate_json_value

        try:
            validate_json_value(result, path="$.result")
        except Exception as exc:
            raise ToolRegistryError(f"tool returned invalid result: {name}") from exc
        if type(result) is not dict:
            raise ToolRegistryError(f"tool returned non-object result: {name}")
        return result

    def _runtime_tool(self, name: str) -> RegisteredTool:
        if not self._sealed:
            raise ToolRegistryError("tool registry is not sealed")
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownTool(f"unknown tool: {name}") from exc

    def _registered(self, name: str) -> RegisteredTool:
        """Return a sealed entry for the Tool worker's execution control."""
        return self._runtime_tool(name)
