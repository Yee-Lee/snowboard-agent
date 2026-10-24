"""No-op null display."""

import logging


class NullDisplay:
    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self._logger.info("display running in null mode")
        self._started = True

    async def stop(self) -> None:
        self._started = False

    def clear(self) -> None:
        pass

    def write_pixels(self, buf: bytes) -> None:
        pass

    def show(self) -> None:
        pass

    def size(self) -> tuple[int, int]:
        return (0, 0)
