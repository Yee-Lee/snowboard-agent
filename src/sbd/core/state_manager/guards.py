from typing import Literal
from sbd.core.events import (
    Event, WorkerFact, State, PerceptionResult, LLMResponse, ActionCompleted,
    ButtonPressed, WakeWordDetected, ExternalMessageArrived,
    InterruptRequested, ShutdownRequested, ErrorOccurred
)
from sbd.core.state_manager.session import SessionContext
from sbd.core.state_manager.notices import _TaskCompleted, _WakeAckElapsed, _RecoveryCompleted

InboxItem = Event | _TaskCompleted | _WakeAckElapsed | _RecoveryCompleted

STATE_WHITELIST: dict[State, tuple[type, ...]] = {
    "IDLE": (ButtonPressed, WakeWordDetected, ExternalMessageArrived, InterruptRequested, ShutdownRequested, ErrorOccurred),
    "WAKE": (ButtonPressed, InterruptRequested, ShutdownRequested, ErrorOccurred, ExternalMessageArrived, _WakeAckElapsed),
    "PERCEPTION": (ButtonPressed, PerceptionResult, InterruptRequested, ShutdownRequested, ErrorOccurred, ExternalMessageArrived, _TaskCompleted),
    "THINK": (ButtonPressed, LLMResponse, InterruptRequested, ShutdownRequested, ErrorOccurred, ExternalMessageArrived, _TaskCompleted),
    "ACTION": (ButtonPressed, ActionCompleted, InterruptRequested, ShutdownRequested, ErrorOccurred, ExternalMessageArrived, _TaskCompleted),
    "ERROR": (ButtonPressed, InterruptRequested, ShutdownRequested, ErrorOccurred, _TaskCompleted, _RecoveryCompleted),
}

def is_allowed_in_state(item: InboxItem, state: State) -> bool:
    if isinstance(item, _TaskCompleted) or isinstance(item, _WakeAckElapsed) or isinstance(item, _RecoveryCompleted):
        # notices are always allowed to be processed, we check their correlation internally
        return type(item) in STATE_WHITELIST[state]
    if isinstance(item, Event):
        # we check if it is an instance of allowed types
        return isinstance(item, STATE_WHITELIST[state])
    return False

def is_valid_fact(fact: WorkerFact, ctx: SessionContext) -> bool:
    if isinstance(fact, ErrorOccurred):
        return True
    return (
        fact.session_id == ctx.session_id
        and fact.turn_id == ctx.turn_id
    )
