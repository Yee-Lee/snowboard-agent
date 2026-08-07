"""Camera HAL protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Camera(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def capture(self) -> bytes: ...
