"""Bounded, side-effect-free M5.tool send handler."""

from __future__ import annotations

import asyncio

from sbd.action.tool.registry import RegisteredTool, ToolArgumentsInvalid
from sbd.cognition.semantic import SemanticError, normalize_text


class MockSend:
    def __init__(self, *, outcome: str = "ok", blocked: bool = False) -> None:
        if outcome not in {"ok", "error"}:
            raise ValueError("invalid mock send outcome")
        self.outcome = outcome
        self.calls: list[str] = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        if not blocked:
            self.release.set()

    def validate(self, arguments: dict) -> None:
        try:
            if type(arguments) is not dict or set(arguments) != {"message"}:
                raise ToolArgumentsInvalid("INVALID_TOOL_ARGUMENTS")
            message = normalize_text(arguments["message"])
            if not message or len(message) > 40:
                raise ToolArgumentsInvalid("INVALID_TOOL_ARGUMENTS")
        except (SemanticError, TypeError):
            raise ToolArgumentsInvalid("INVALID_TOOL_ARGUMENTS") from None

    async def handle(self, arguments: dict) -> dict:
        self.validate(arguments)
        self.calls.append(normalize_text(arguments["message"]))
        self.entered.set()
        await self.release.wait()
        if self.outcome == "error":
            raise ToolArgumentsInvalid("MOCK_SEND_FAILED")
        return {}

    async def abort(self) -> None:
        self.release.set()

    async def force_abort(self):
        from sbd.core.lifecycle import ForceAbortReport
        self.release.set()
        return ForceAbortReport()

    def registered_tool(self) -> RegisteredTool:
        return RegisteredTool(
            name="mock.send",
            description="模擬送出使用者指定訊息；只記錄一次派發，沒有外部設備副作用",
            input_schema={"type": "object", "properties": {
                "message": {"type": "string", "maxLength": 40}},
                "required": ["message"], "additionalProperties": False},
            validate=self.validate,
            handler=self.handle,
            execution_control=self,
        )
