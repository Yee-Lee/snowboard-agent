"""M3-CAM-001 null camera format validity."""

from __future__ import annotations

import asyncio

from sbd.core.camera.null import NullCamera
from sbd.core.config.models import CameraConfig


def _jpeg_size(data: bytes):
    offset = 2
    while offset < len(data) - 4:
        marker = data[offset + 1]
        length = int.from_bytes(data[offset + 2:offset + 4], "big")
        if marker == 0xC0:
            return (
                int.from_bytes(data[offset + 7:offset + 9], "big"),
                int.from_bytes(data[offset + 5:offset + 7], "big"),
            )
        if marker == 0xDA:
            break
        offset += length + 2
    raise AssertionError("JPEG missing SOF")


def test_m3_cam_001() -> None:
    async def scenario():
        rgb = await NullCamera(CameraConfig(driver="null", format="RGB", width=8, height=6)).capture()
        yuv = await NullCamera(CameraConfig(driver="null", format="YUV", width=8, height=6)).capture()
        jpeg = await NullCamera(CameraConfig(driver="null", format="JPEG", width=8, height=6)).capture()
        assert rgb == bytes(8 * 6 * 3)
        assert len(yuv) == 8 * 6 * 3 // 2
        assert yuv[:48] == bytes(48) and yuv[48:] == bytes((128,)) * 24
        assert _jpeg_size(jpeg) == (8, 6)
        assert jpeg.startswith(b"\xff\xd8") and jpeg.endswith(b"\xff\xd9")
    asyncio.run(scenario())
