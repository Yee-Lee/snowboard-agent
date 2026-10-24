"""GPIO HAL protocol and event value."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Literal, Protocol, runtime_checkable


Edge = Literal["rising", "falling", "both"]


@dataclass(frozen=True, slots=True)
class GPIOEvent:
    pin: int
    edge: Literal["rising", "falling"]
    at: float


GPIOCallback = Callable[[GPIOEvent], Awaitable[None]]


@runtime_checkable
class GPIO(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def register_input(
        self,
        pin: int,
        edge: Edge,
        callback: GPIOCallback,
        debounce_ms: int = 0,
    ) -> None: ...
    async def unregister(self, pin: int) -> None: ...
    async def set_output(self, pin: int, value: bool) -> None: ...
    async def configure_output(self, pin: int, initial: bool = False) -> None: ...
