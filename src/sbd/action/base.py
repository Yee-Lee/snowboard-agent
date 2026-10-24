"""Action Protocol — execute commands / effects.

Defined per Ch 2 §2.4.  Action workers are in the SM in-flight set
and support cooperative (abort) and forced (force_abort) cancellation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sbd.core.lifecycle import ForceAbortReport


@runtime_checkable
class Action(Protocol):
    """Executes actions and publishes ActionCompleted via the Bus."""

    async def start(self) -> None:
        """Initialise long-term resources.  Fully ready on return."""
        ...

    async def stop(self) -> None:
        """Idempotently shut down and release all long-term resources."""
        ...

    async def abort(self) -> None:
        """Level 1 cooperative cancellation of in-flight execute()."""
        ...

    async def force_abort(self) -> ForceAbortReport:
        """Level 2 forced convergence after abort() timeout."""
        ...

    async def execute(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        payload: dict[str, Any],
    ) -> None:
        """Execute action.  Publishes ActionCompleted via the Bus.

        No timeout parameter — cancellation goes through abort/force_abort.
        """
        ...
