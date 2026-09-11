import asyncio
from dataclasses import dataclass
from typing import Literal, Any
from sbd.core.events import WorkerFact

@dataclass
class InFlightRecord:
    correlation_id: int
    session_id: str
    turn_id: int
    phase: Literal[
        "perception", "think", "action_primary", "action_rest",
        "conversation_open", "conversation_close",
    ]
    kind: str
    worker: Any
    task: asyncio.Task[Any]
    conversation_generation: int = 0
    completion_mode: Literal["worker_fact", "private_result"] = "worker_fact"
    terminal_fact: WorkerFact | None = None
    private_result: Any = None
    request_terminal_proven: bool = False
    cleanup_proven: bool = False
    engine_usable: bool | None = None
    force_abort_proven: bool = False
    cancel_requested: bool = False
