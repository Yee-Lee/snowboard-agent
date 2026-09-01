"""AR1 local streaming-ASR research scaffolding."""

from .protocol import (
    ErrorCode,
    EventKind,
    LifecycleCommand,
    LifecycleOperation,
    PCMChunk,
    ProtocolError,
    SessionState,
    TranscriptAlternative,
    TranscriptEvent,
    final_text_for_downstream,
)

__all__ = [
    "ErrorCode",
    "EventKind",
    "LifecycleCommand",
    "LifecycleOperation",
    "PCMChunk",
    "ProtocolError",
    "SessionState",
    "TranscriptAlternative",
    "TranscriptEvent",
    "final_text_for_downstream",
]
