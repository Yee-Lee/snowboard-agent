"""Picamera2 backend with explicit RGB, I420, and JPEG output formats."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from sbd.core.config.models import CameraConfig


class PiCamera:
    def __init__(self, config: CameraConfig, *, camera_factory=None) -> None:
        self._config = config
        self._camera_factory = camera_factory
        self._injected_factory = camera_factory is not None
        self._camera = None
        self._executor: ThreadPoolExecutor | None = None

    async def start(self) -> None:
        if self._camera is not None:
            raise RuntimeError("PiCamera already started")
        if self._camera_factory is None:
            from picamera2 import Picamera2
            self._camera_factory = Picamera2
        if self._injected_factory:
            self._start_sync()
            return
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sbd-camera")
        try:
            await self._run(self._start_sync)
        except Exception:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
            raise

    async def stop(self) -> None:
        camera, self._camera = self._camera, None
        executor, self._executor = self._executor, None
        try:
            if camera is not None and self._injected_factory:
                camera.stop()
                close = getattr(camera, "close", None)
                if callable(close):
                    close()
            elif camera is not None and executor is not None:
                await asyncio.get_running_loop().run_in_executor(executor, camera.stop)
                close = getattr(camera, "close", None)
                if callable(close):
                    await asyncio.get_running_loop().run_in_executor(executor, close)
        finally:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)

    async def capture(self) -> bytes:
        if self._camera is None:
            raise RuntimeError("capture called before PiCamera start")
        if self._injected_factory:
            return self._capture_sync()
        return await self._run(self._capture_sync)

    async def _run(self, callback):
        if self._executor is None:
            raise RuntimeError("PiCamera worker is not available")
        return await asyncio.get_running_loop().run_in_executor(self._executor, callback)

    def _start_sync(self) -> None:
        camera = self._camera_factory()
        pixel_format = {
            "RGB": "BGR888",
            "YUV": "YUV420",
            "JPEG": "BGR888",
        }[self._config.format]
        configuration = camera.create_still_configuration(
            main={
                "size": (self._config.width, self._config.height),
                "format": pixel_format,
            },
            buffer_count=2,
        )
        camera.configure(configuration)
        camera.start()
        self._camera = camera

    def _capture_sync(self) -> bytes:
        camera = self._camera
        width, height = self._config.width, self._config.height
        if self._config.format == "JPEG":
            image = camera.capture_image("main")
            if image.size != (width, height):
                raise RuntimeError("Picamera2 JPEG image dimensions do not match config")
            output = BytesIO()
            image.save(output, format="JPEG", quality=self._config.quality)
            return output.getvalue()

        array = camera.capture_array("main")
        if self._config.format == "RGB":
            cropped = array[:height, :width, :3]
            value = cropped.tobytes(order="C")
            if len(value) != width * height * 3:
                raise RuntimeError("Picamera2 RGB array has an invalid layout")
            return value

        # Picamera2 represents planar YUV420 as (height*3/2, stride). U and V
        # each occupy height/4 rows when packed into a matrix of full-width rows.
        y = array[:height, :width]
        chroma_rows = height // 4
        u = array[height:height + chroma_rows, :width]
        v = array[height + chroma_rows:height + 2 * chroma_rows, :width]
        value = y.tobytes(order="C") + u.tobytes(order="C") + v.tobytes(order="C")
        if len(value) != width * height * 3 // 2:
            raise RuntimeError("Picamera2 YUV420 array has an invalid layout")
        return value
