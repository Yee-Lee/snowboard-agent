"""Minimal conforming fakes for M1 protocol smoke tests.

These fakes satisfy the public interfaces of InputSource, Perception,
Action, Adaptor, and Reasoner with no real behaviour.  They are used
by SM/RM tests for assembly verification (M1-CON-001).
"""

from __future__ import annotations

from typing import Any

from sbd.core.lifecycle import ForceAbortReport


# ---------------------------------------------------------------------------
# InputSource fake
# ---------------------------------------------------------------------------

class FakeInputSource:
    """Minimal InputSource that does nothing."""

    def __init__(self) -> None:
        self._available = False

    async def start(self) -> None:
        self._available = True

    async def stop(self) -> None:
        self._available = False

    def is_available(self) -> bool:
        return self._available


# ---------------------------------------------------------------------------
# Perception fake
# ---------------------------------------------------------------------------

class FakePerception:
    """Minimal Perception that returns immediately without publishing."""

    def __init__(self) -> None:
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def abort(self) -> None:
        pass

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        # Real worker would publish PerceptionResult via Bus; fake does nothing.
        pass


# ---------------------------------------------------------------------------
# Action fake
# ---------------------------------------------------------------------------

class FakeAction:
    """Minimal Action that returns immediately without publishing."""

    def __init__(self) -> None:
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def abort(self) -> None:
        pass

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    async def execute(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        payload: dict[str, Any],
    ) -> None:
        # Real worker would publish ActionCompleted via Bus; fake does nothing.
        pass


# ---------------------------------------------------------------------------
# Adaptor fake
# ---------------------------------------------------------------------------

class FakeAdaptor:
    """Minimal Adaptor that does nothing."""

    def __init__(self) -> None:
        self._available = False

    async def start(self) -> None:
        self._available = True

    async def stop(self) -> None:
        self._available = False

    def is_available(self) -> bool:
        return self._available


# ---------------------------------------------------------------------------
# Reasoner fake
# ---------------------------------------------------------------------------

class FakeReasoner:
    """Minimal Reasoner that returns immediately without publishing."""

    def __init__(self) -> None:
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def abort(self) -> None:
        pass

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[Any, ...],
        pending_message_ids: tuple[str, ...],
    ) -> None:
        pass
