import asyncio
from dataclasses import dataclass
from sbd.core.events import CorrelationId, SessionId

@dataclass(frozen=True, slots=True)
class _TaskCompleted:
    kind: str
    correlation_id: CorrelationId
    task: asyncio.Task[None]

@dataclass(frozen=True, slots=True)
class _WakeAckElapsed:
    session_id: SessionId

@dataclass(frozen=True, slots=True)
class _RecoveryCompleted:
    generation: int
    waiter: asyncio.Task[None]
