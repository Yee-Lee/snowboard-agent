"""Lifecycle control values shared across SM, workers, and RM.

This module is the single source of ForceAbortReport and lifecycle-related
exceptions.  It does NOT go through the Event Bus — these are control-flow
values, not Events.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# ForceAbortReport — Level 2 force_abort() return value
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ForceAbortReport:
    """Returned by ``force_abort()`` to report which backends were destroyed.

    ``destroyed_backends`` uses stable RM keys defined in Ch 5.
    A non-destructive or pure-asyncio worker returns an empty tuple.
    """

    destroyed_backends: tuple[str, ...] = ()
