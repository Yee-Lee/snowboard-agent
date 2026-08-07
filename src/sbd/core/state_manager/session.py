from dataclasses import dataclass, field
from typing import Literal
from sbd.core.events import SessionId, TurnId, CorrelationId, PerceptionResult, LLMResponse, ActionCompleted

@dataclass
class SessionContext:
    session_id: str
    wake_source: Literal["button", "wake_word", "external_message"]
    turn_id: int = 0
    selected_perceptions: tuple[str, ...] = ()
    perception_results: list[PerceptionResult] = field(default_factory=list)
    llm_response: LLMResponse | None = None
    action_completed: ActionCompleted | None = None
    next_perceptions: tuple[str, ...] = ()
    buffer_exit_policy: Literal["none", "flush_to_wake", "discard"] = "none"
