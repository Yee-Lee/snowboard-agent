"""In-memory mock display with explicit back-buffer/show semantics."""

from sbd.core.config.models import DisplayConfig


class MockDisplay:
    def __init__(self, config: DisplayConfig | None = None) -> None:
        self._config = config or DisplayConfig(driver="mock")
        if self._config.width <= 0 or self._config.height <= 0:
            raise ValueError("display dimensions must be positive")
        factors = {"mono1": None, "rgb565": 2, "rgb888": 3}
        if self._config.pixel_format not in factors:
            raise ValueError("unknown pixel format")
        pixels = self._config.width * self._config.height
        factor = factors[self._config.pixel_format]
        self._buffer_size = (pixels + 7) // 8 if factor is None else pixels * factor
        self._back_buffer = bytes(self._buffer_size)
        self.shown_buffers: list[bytes] = []
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    def clear(self) -> None:
        self._back_buffer = bytes(self._buffer_size)

    def write_pixels(self, buf: bytes) -> None:
        if type(buf) is not bytes or len(buf) != self._buffer_size:
            raise ValueError("pixel buffer has invalid length")
        self._back_buffer = bytes(buf)

    def show(self) -> None:
        self.shown_buffers.append(self._back_buffer)

    def size(self) -> tuple[int, int]:
        return (self._config.width, self._config.height)
