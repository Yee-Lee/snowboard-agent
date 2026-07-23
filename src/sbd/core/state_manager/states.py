"""State enumeration (see docs/arch.md §11.1)."""

from __future__ import annotations

from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    WAKE = "WAKE"
    PERCEPTION = "PERCEPTION"
    THINK = "THINK"
    ACTION = "ACTION"
    ERROR = "ERROR"
