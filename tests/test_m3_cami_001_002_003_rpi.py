"""M3 Picamera2 Raspberry Pi acceptance cards."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from io import BytesIO

import pytest
from PIL import Image

from sbd.core.camera import make_camera
from sbd.core.camera.null import NullCamera
from sbd.core.config.models import CameraConfig
from sbd.core.camera.picamera2.driver import PiCamera
from tests.rpi_support import record_result, rpi_config


pytestmark = pytest.mark.rpi


def test_m3_cami_001() -> None:
    config = rpi_config()

    async def scenario() -> None:
        camera = make_camera(replace(config.core.camera, driver="picamera2", format="JPEG"))
        await camera.start()
        try:
            payload = await camera.capture()
        finally:
            await camera.stop()
        with Image.open(BytesIO(payload)) as image:
            assert image.size == (config.core.camera.width, config.core.camera.height)
        assert len(payload) > 128
    asyncio.run(scenario())
    record_result("M3-CAMI-001", format="JPEG")


def test_m3_cami_002() -> None:
    config = rpi_config()

    async def scenario() -> None:
        for fmt, expected in (("RGB", config.core.camera.width * config.core.camera.height * 3), ("YUV", config.core.camera.width * config.core.camera.height * 3 // 2)):
            camera = make_camera(replace(config.core.camera, driver="picamera2", format=fmt))
            await camera.start()
            try:
                payload = await camera.capture()
            finally:
                await camera.stop()
            assert len(payload) == expected
            assert any(payload)
    asyncio.run(scenario())
    record_result("M3-CAMI-002", formats=["RGB", "YUV"])


def test_m3_cami_003() -> None:
    config = rpi_config()

    async def scenario() -> None:
        broken = PiCamera(config.core.camera, camera_factory=lambda: (_ for _ in ()).throw(RuntimeError("missing CSI")))
        with pytest.raises(RuntimeError, match="missing CSI"):
            await broken.start()
        fallback = NullCamera(config.core.camera)
        await fallback.start()
        assert len(await fallback.capture()) > 0
        await fallback.stop()
    asyncio.run(scenario())
    record_result("M3-CAMI-003", fallback="null", capability=False)
