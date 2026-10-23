"""M5T-LOG-001: tool and Look projection keep private payloads off Display."""

import asyncio
from types import SimpleNamespace

from sbd.core.display.session import SessionDisplay
from sbd.core.event_bus import EventBus
from sbd.core.events import StateChanged


class Arbiter:
    def __init__(self):
        self.hints = []

    def write_main(self, hint):
        self.hints.append(hint)


class Manager:
    def __init__(self):
        self.state = "ACTION"
        self._session = SimpleNamespace(
            selected_perceptions=("listen",),
            action_phase="primary",
            llm_response=SimpleNamespace(action_kind="tool", action_payload={
                "name": "mock.send", "arguments": {"message": "SECRET_MSG_99"}}),
            perception_results=[],
        )
        self._pending = None
        self._shutting_down = False
        self.feedback = None

    def set_feedback_display(self, callback):
        self.feedback = callback


def test_display_projects_safe_tool_feedback_and_look_state():
    async def run():
        arbiter = Arbiter()
        manager = Manager()
        display = SessionDisplay(arbiter, EventBus(), manager)
        await display.start()
        await display._on_state_changed(StateChanged("THINK", "ACTION"))
        assert arbiter.hints[-1].data["text"] == "傳送中"
        manager._session.action_phase = "tool_feedback"
        manager.feedback("已送出。")
        assert arbiter.hints[-1].data["text"] == "已送出。"
        manager.state = "PERCEPTION"
        manager._session.selected_perceptions = ("look",)
        await display._on_state_changed(StateChanged("ACTION", "PERCEPTION"))
        assert arbiter.hints[-1].data["text"] == "查看中"
        assert "SECRET_MSG_99" not in repr(arbiter.hints)
        await display.stop()
        assert manager.feedback is None
    asyncio.run(run())
