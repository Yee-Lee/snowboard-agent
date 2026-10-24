"""M3 Picamera2 Raspberry Pi acceptance cards."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from io import BytesIO

import pytest
from PIL import Image

from sbd.core.camera import make_camera
from sbd.core.camera.picamera2.driver import PiCamera
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.event_bus import EventBus
from sbd.core.m2_composition import M2Composition
from sbd.core.resource_manager import ResourceManager
from tests.rpi_support import record_result, rpi_config


pytestmark = pytest.mark.rpi


def test_m3_cami_001() -> None:
    config = rpi_config("M3-CAMI-001")

    async def scenario() -> int:
        camera = make_camera(replace(config.core.camera, driver="picamera2", format="JPEG"))
        await camera.start()
        try:
            payload = await camera.capture()
        finally:
            await camera.stop()
        with Image.open(BytesIO(payload)) as image:
            assert image.size == (config.core.camera.width, config.core.camera.height)
            image.verify()
        assert len(payload) > 128
        return len(payload)

    size = asyncio.run(scenario())
    record_result(
        "M3-CAMI-001",
        expected="valid decodable JPEG at configured dimensions",
        actual=f"decoded JPEG bytes={size}",
        fixture={"name": "live CSI sensor", "sha256": "not-applicable"},
    )


def test_m3_cami_002(monkeypatch, caplog) -> None:
    config = rpi_config("M3-CAMI-002")
    broken = PiCamera(
        replace(config.core.camera, driver="picamera2"),
        camera_factory=lambda: (_ for _ in ()).throw(RuntimeError("missing CSI fixture")),
    )
    monkeypatch.setattr("sbd.core.m2_composition.make_camera", lambda _: broken)
    isolated = replace(
        DEFAULT_CONFIG,
        core=replace(DEFAULT_CONFIG.core, camera=config.core.camera),
    )

    async def scenario() -> None:
        bus = EventBus()
        rm = ResourceManager(isolated, bus)
        M2Composition()(rm, bus, isolated)
        with caplog.at_level(logging.WARNING):
            await rm.start()
        record = rm._records["core.camera"]
        assert record.using_null is True
        assert type(record.instance).__name__ == "NullCamera"
        assert rm.capability_of("camera") is False
        assert "missing CSI fixture" in caplog.text
        assert rm._startup_complete is True
        report = await rm.stop_all()
        assert report.failures == ()

    asyncio.run(scenario())
    record_result(
        "M3-CAMI-002",
        expected="ResourceManager real-to-null fallback, camera=False, warning, app continues",
        actual="NullCamera owned by RM; capability false; startup and shutdown completed",
        fixture={"name": "deterministic missing-CSI start failure", "sha256": "inline-fixture"},
    )


def test_m3_cami_003() -> None:
    config = rpi_config("M3-CAMI-003")
    observed: dict[str, int] = {}

    async def scenario() -> None:
        for fmt, expected in (
            ("RGB", config.core.camera.width * config.core.camera.height * 3),
            ("YUV", config.core.camera.width * config.core.camera.height * 3 // 2),
        ):
            camera = make_camera(replace(config.core.camera, driver="picamera2", format=fmt))
            await camera.start()
            try:
                payload = await camera.capture()
            finally:
                await camera.stop()
            assert len(payload) == expected
            assert any(payload), f"{fmt} sensor frame is entirely zero"
            observed[fmt] = len(payload)

    asyncio.run(scenario())
    record_result(
        "M3-CAMI-003",
        expected="live RGB and I420 buffers have exact configured sizes and non-zero data",
        actual=f"captured {observed}",
        fixture={"name": "live CSI sensor RGB/YUV", "sha256": "not-applicable"},
    )
