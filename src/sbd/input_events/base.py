"""InputSource Protocol — constant input channel.

Defined per Ch 2 §2.2.  InputSource is a background publisher of Signal
events.  It is NOT in the SM in-flight set and does not declare abort().
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class InputSource(Protocol):
    """Background input source that publishes Signal events to the Bus."""

    async def start(self) -> None:
        """Initialise and begin publishing.  Must be fully ready on return."""
        ...

    async def stop(self) -> None:
        """Idempotently shut down and release all resources."""
        ...

    def is_available(self) -> bool:
        """Synchronous query — can this source currently publish Signals?"""
        ...
