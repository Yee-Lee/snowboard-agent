"""Host seam tests for the lazy Picamera2 backend."""

from __future__ import annotations

import asyncio

import numpy as np
from PIL import Image

from sbd.core.camera.picamera2.driver import PiCamera
from sbd.core.config.models import CameraConfig


class FakeCamera:
    def __init__(self):
        self.configuration = None
        self.started = False
        self.stopped = False
        self.closed = False
    def create_still_configuration(self, **kwargs): return kwargs
    def configure(self, value): self.configuration = value
    def start(self): self.started = True
    def stop(self): self.stopped = True
    def close(self): self.closed = True
    def capture_image(self, stream): return Image.new("RGB", (4, 2), (10, 20, 30))
    def capture_array(self, stream):
        fmt = self.configuration["main"]["format"]
        if fmt == "BGR888":
            return np.arange(2 * 8 * 3, dtype=np.uint8).reshape(2, 8, 3)
        return np.arange(6 * 8, dtype=np.uint8).reshape(6, 8)


def test_picamera2_backend_crops_stride_and_reopens() -> None:
    async def scenario():
        created = []
        def factory():
            camera = FakeCamera(); created.append(camera); return camera
        rgb = PiCamera(CameraConfig(driver="picamera2", format="RGB", width=4, height=2), camera_factory=factory)
        await rgb.start()
        assert len(await rgb.capture()) == 4 * 2 * 3
        await rgb.stop(); await rgb.stop(); await rgb.start(); await rgb.stop()
        assert all(camera.stopped and camera.closed for camera in created)

        yuv = PiCamera(CameraConfig(driver="picamera2", format="YUV", width=4, height=4), camera_factory=factory)
        await yuv.start()
        assert len(await yuv.capture()) == 4 * 4 * 3 // 2
        await yuv.stop()

        jpeg = PiCamera(CameraConfig(driver="picamera2", format="JPEG", width=4, height=2), camera_factory=factory)
        await jpeg.start()
        value = await jpeg.capture()
        assert value.startswith(b"\xff\xd8") and value.endswith(b"\xff\xd9")
        await jpeg.stop()
    asyncio.run(scenario())
