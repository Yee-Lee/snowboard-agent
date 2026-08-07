import asyncio
from dataclasses import dataclass
from typing import Literal, Any
from sbd.core.events import WorkerFact

@dataclass
class InFlightRecord:
    correlation_id: int
    session_id: str
    turn_id: int
    phase: Literal["perception", "think", "action"]
    kind: str
    worker: Any
    task: asyncio.Task[None]
    terminal_fact: WorkerFact | None = None
    cancel_requested: bool = False
