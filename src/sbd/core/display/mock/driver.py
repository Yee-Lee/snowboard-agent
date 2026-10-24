"""In-memory mock display with explicit back-buffer/show semantics."""

from sbd.core.config.models import DisplayConfig


class MockDisplay:
    def __init__(self, config: DisplayConfig | None = None) -> None:
        self._config = config or DisplayConfig(driver="mock")
        if self._config.width <= 0 or self._config.height <= 0:
            raise ValueError("display dimensions must be positive")
        factors = {"rgb565": 2}
        if self._config.pixel_format not in factors:
            raise ValueError("unknown pixel format")
        pixels = self._config.width * self._config.height
        factor = factors[self._config.pixel_format]
        self._buffer_size = pixels * factor
        if self._buffer_size != self._config.frame_buffer_bytes:
            raise ValueError("display frame buffer size contradicts selected profile")
        self._back_buffer = bytes(self._buffer_size)
        self.shown_buffers: list[bytes] = []
        self.calls: list[str] = []
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    def clear(self) -> None:
        self.calls.append("clear")
        self._back_buffer = bytes(self._buffer_size)

    def write_pixels(self, buf: bytes) -> None:
        if type(buf) is not bytes or len(buf) != self._buffer_size:
            raise ValueError("pixel buffer has invalid length")
        self._back_buffer = bytes(buf)
        self.calls.append("write_pixels")

    def show(self) -> None:
        self.calls.append("show")
        self.shown_buffers.append(self._back_buffer)

    def size(self) -> tuple[int, int]:
        return (self._config.width, self._config.height)
