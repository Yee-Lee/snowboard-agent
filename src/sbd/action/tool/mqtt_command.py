"""Fixed remote-connection command handler for the M5 MQTT profile."""

from __future__ import annotations

from sbd.action.tool.registry import RegisteredTool, ToolArgumentsInvalid
from sbd.core.lifecycle import ForceAbortReport
from sbd.input_events.mqtt.client import MQTTClient


class MQTTCommandTool:
    def __init__(self, client: MQTTClient) -> None:
        self._client = client

    @staticmethod
    def validate(arguments: dict) -> None:
        if type(arguments) is not dict or arguments != {"message": "啟用遠端連線"}:
            raise ToolArgumentsInvalid("INVALID_TOOL_ARGUMENTS")

    async def handle(self, arguments: dict) -> dict:
        self.validate(arguments)
        await self._client.publish_command()
        return {}

    async def abort(self) -> None:
        return None

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    def registered_tool(self) -> RegisteredTool:
        return RegisteredTool(
            name="mock.send",
            description="派發固定遠端連線命令；成功只表示本地送出，不表示外部已完成",
            input_schema={"type": "object", "properties": {
                "message": {"type": "string", "maxLength": 40}},
                "required": ["message"], "additionalProperties": False},
            validate=self.validate,
            handler=self.handle,
            execution_control=self,
        )
