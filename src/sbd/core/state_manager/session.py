from dataclasses import dataclass, field
from typing import Literal
from sbd.core.events import (
    ActionCompleted, LLMResponse, PerceptionResult, PostActionRoute, SessionId,
    TurnId,
)

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
    conversation_generation: int = 0
    conversation_state: Literal["none", "opening", "ready", "closing"] = "none"
    wake_ack_ready: bool = False
    model_admission_blocked: bool = True
    post_action_route: PostActionRoute | None = None
    normalized_next_perceptions: tuple[str, ...] = ()
    action_phase: Literal["none", "primary", "post_action_rest"] = "none"
