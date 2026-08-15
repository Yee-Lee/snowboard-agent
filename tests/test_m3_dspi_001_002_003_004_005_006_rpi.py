"""M3 SSD1351 Raspberry Pi acceptance cards."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from statistics import quantiles
from time import monotonic

import pytest

from sbd.core.config.models import DisplayConfig
from sbd.core.display import make_display
from sbd.core.display.null import NullDisplay
from tests.rpi_support import record_result, require_manual, rpi_config


pytestmark = pytest.mark.rpi
_FRAME = bytes((0xF8, 0x00)) * 16_384


async def _present(display, frame: bytes = _FRAME) -> None:
    display.clear()
    display.write_pixels(frame)
    display.show()


def test_m3_dspi_001() -> None:
    config = rpi_config()
    assert config.core.display.driver == "ssd1351"

    async def scenario() -> None:
        display = make_display(config.core.display)
        await display.start()
        try:
            await _present(display)
        finally:
            await display.stop()
    asyncio.run(scenario())
    record_result("M3-DSPI-001", frame_bytes=32_768, presents=1)


def test_m3_dspi_002() -> None:
    rpi_config()
    require_manual("M3-DSPI-002")
    record_result("M3-DSPI-002", manual="PASS", observations=["boot_blank", "idle_text", "shutdown_blank"])


def test_m3_dspi_003() -> None:
    config = rpi_config()
    missing = replace(config.core.display, native_library_path=config.core.display.native_library_path.with_name("missing-libdisplay.so"))

    async def scenario() -> None:
        real = make_display(missing)
        with pytest.raises(Exception):
            await real.start()
        fallback = NullDisplay()
        await fallback.start()
        assert fallback.size() == (0, 0)
        await fallback.stop()
    asyncio.run(scenario())
    record_result("M3-DSPI-003", fallback="null", capability=False)


def test_m3_dspi_004() -> None:
    config = rpi_config()

    async def scenario() -> None:
        display = make_display(config.core.display)
        for _ in range(2):
            await display.start()
            await _present(display)
            await display.stop()
            await display.stop()
    asyncio.run(scenario())
    record_result("M3-DSPI-004", reopen_cycles=2)


def test_m3_dspi_005() -> None:
    rpi_config()
    require_manual("M3-DSPI-005")
    record_result("M3-DSPI-005", manual="PASS", fixture="orientation-and-rgb565-bars")


def test_m3_dspi_006() -> None:
    config = rpi_config()

    async def scenario() -> list[float]:
        display = make_display(config.core.display)
        await display.start()
        samples: list[float] = []
        try:
            for _ in range(10):
                await _present(display)
            for _ in range(100):
                started = monotonic()
                await _present(display)
                elapsed = monotonic() - started
                assert elapsed < 1
                samples.append(elapsed)
        finally:
            await display.stop()
        return samples
    samples = asyncio.run(scenario())
    record_result(
        "M3-DSPI-006", samples=samples, p50=quantiles(samples, n=100)[49],
        p95=quantiles(samples, n=100)[94], maximum=max(samples),
    )
