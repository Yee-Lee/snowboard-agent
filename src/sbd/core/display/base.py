"""Authoritative display HAL protocol used by the Core resource manager."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DisplayDevice(Protocol):
    """Lifecycle is async; event-loop render primitives are synchronous."""

    async def start(self) -> None:
        """Acquire and initialise display resources."""
        ...

    async def stop(self) -> None:
        """Release resources. Implementations must be idempotent."""
        ...

    def clear(self) -> None:
        """Clear only the adapter-owned back buffer."""
        ...

    def write_pixels(self, buf: bytes) -> None:
        """Replace the complete RGB565_MSB_FIRST back buffer."""
        ...

    def show(self) -> None:
        """Flush the current back buffer exactly once."""
        ...

    def size(self) -> tuple[int, int]:
        """Return the physical width and height."""
        ...
