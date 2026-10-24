"""Perception Protocol — physical signal → internal data.

Defined per Ch 2 §2.3.  Perception workers are in the SM in-flight set
and support cooperative (abort) and forced (force_abort) cancellation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@runtime_checkable
class Perception(Protocol):
    """Translates physical signals into internal data via PerceptionResult."""

    async def start(self) -> None:
        """Initialise long-term resources.  Fully ready on return."""
        ...

    async def stop(self) -> None:
        """Idempotently shut down and release all long-term resources."""
        ...

    async def abort(self) -> None:
        """Level 1 cooperative cancellation of in-flight perceive()."""
        ...

    async def force_abort(self) -> ForceAbortReport:
        """Level 2 forced convergence after abort() timeout."""
        ...

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        """Execute perception.  Publishes PerceptionResult via the Bus.

        The method returns None; the terminal Fact is published, not returned.
        """
        ...
