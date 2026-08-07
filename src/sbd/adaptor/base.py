"""Adaptor Protocol — external communication channel.

Defined per Ch 2 §2.5.  Adaptors are background observers / external
channels.  They are NOT in the SM in-flight set and do not declare abort().
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Adaptor(Protocol):
    """External channel that subscribes to Bus events and publishes outward."""

    async def start(self) -> None:
        """Initialise and begin operation.  Fully ready on return."""
        ...

    async def stop(self) -> None:
        """Idempotently shut down and release all resources."""
        ...

    def is_available(self) -> bool:
        """Synchronous query — can this adaptor currently communicate?"""
        ...
