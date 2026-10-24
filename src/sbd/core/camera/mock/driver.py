"""Deterministic mock camera."""

from sbd.core.camera.null.driver import NullCamera
from sbd.core.config.models import CameraConfig


class MockCamera(NullCamera):
    def __init__(
        self,
        config: CameraConfig | None = None,
        *,
        images: tuple[bytes, ...] | None = None,
    ) -> None:
        super().__init__(config or CameraConfig(driver="mock"))
        self._images = images
        self._index = 0

    async def capture(self) -> bytes:
        if not self._images:
            return await super().capture()
        value = self._images[self._index % len(self._images)]
        self._index += 1
        return value
