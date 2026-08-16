"""M3 SSD1351 Raspberry Pi acceptance cards."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from dataclasses import replace
from pathlib import Path
from statistics import quantiles
from time import monotonic

import pytest

from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.display import DisplayArbiter, Oled128Renderer, make_display
from sbd.core.display.hints import DisplayHint
from sbd.core.display.lifecycle import DisplayLifecycle
from sbd.core.event_bus import EventBus
from sbd.core.m3_composition import M3Composition
from sbd.core.resource_manager import ResourceManager
from tests.rpi_support import record_result, require_manual, rpi_config


pytestmark = pytest.mark.rpi
_FRAME = bytes((0xF8, 0x00)) * 16_384


class _LoggingDisplay:
    def __init__(self, target) -> None:
        self.target = target
        self.calls: list[str] = []

    async def start(self) -> None: await self.target.start()
    async def stop(self) -> None: await self.target.stop()
    def size(self): return self.target.size()
    def clear(self) -> None:
        self.calls.append("clear"); self.target.clear()
    def write_pixels(self, frame: bytes) -> None:
        self.calls.append("write_pixels"); self.target.write_pixels(frame)
    def show(self) -> None:
        self.calls.append("show"); self.target.show()


def _observation_seconds() -> float:
    value = float(os.environ.get("SBD_M3_DISPLAY_OBSERVATION_SECONDS", "3"))
    assert 1 <= value <= 30
    return value


def _open_bus_fds() -> list[str]:
    values: list[str] = []
    for path in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(path)
        except OSError:
            continue
        if "spidev" in target or "gpiochip" in target:
            values.append(target)
    return sorted(values)


def _orientation_fixture() -> bytes:
    pixels = bytearray(32_768)
    colors = (0xF800, 0x07E0, 0x001F, 0xFFFF)
    for y in range(128):
        for x in range(128):
            quadrant = (0 if y < 64 else 2) + (0 if x < 64 else 1)
            value = colors[quadrant]
            offset = (y * 128 + x) * 2
            pixels[offset:offset + 2] = value.to_bytes(2, "big")
    # Black upward arrow in the top-left red quadrant.
    for y in range(8, 48):
        half_width = max(2, (y - 8) // 3)
        for x in range(24 - half_width, 25 + half_width):
            offset = (y * 128 + x) * 2
            pixels[offset:offset + 2] = b"\x00\x00"
    return bytes(pixels)


def test_m3_dspi_001() -> None:
    config = rpi_config("M3-DSPI-001")

    async def scenario() -> list[str]:
        proxy = _LoggingDisplay(make_display(config.core.display))
        await proxy.start()
        arbiter = DisplayArbiter(proxy, Oled128Renderer())
        await arbiter.start()
        proxy.calls.clear()  # isolate the acceptance intent from startup render
        try:
            arbiter.write_main(DisplayHint("main.text", {"text": "atomic"}))
            assert proxy.calls == ["clear", "write_pixels", "show"]
            return list(proxy.calls)
        finally:
            await arbiter.stop()
            await proxy.stop()

    calls = asyncio.run(scenario())
    record_result(
        "M3-DSPI-001",
        expected="one write_main intent produces exactly clear→write_pixels→show",
        actual=f"arbiter call log={calls}",
        fixture={"name": "main.text atomic intent", "sha256": "inline-fixture"},
    )


def test_m3_dspi_002() -> None:
    config = rpi_config("M3-DSPI-002")

    async def scenario() -> tuple[list[str], dict]:
        proxy = _LoggingDisplay(make_display(config.core.display))
        await proxy.start()
        arbiter = DisplayArbiter(proxy, Oled128Renderer())
        await arbiter.start()
        lifecycle = DisplayLifecycle(arbiter)
        try:
            assert lifecycle.begin_boot() is True
            await asyncio.sleep(_observation_seconds())
            lifecycle.finish_boot()
            arbiter.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
            await asyncio.sleep(_observation_seconds())
            assert lifecycle.begin_shutdown() is True
            await asyncio.sleep(_observation_seconds())
            manual = require_manual(
                "M3-DSPI-002", ("boot_blank", "idle_text_readable", "shutdown_blank"),
            )
            assert arbiter.snapshot().fullscreen == DisplayHint("fullscreen.blank")
            return list(proxy.calls), manual
        finally:
            await arbiter.stop()
            await proxy.stop()

    calls, manual = asyncio.run(scenario())
    assert calls.count("show") >= 4
    record_result(
        "M3-DSPI-002",
        expected="boot blank, IDLE state text, and shutdown blank execute through lifecycle owner",
        actual=f"lifecycle rendered {calls.count('show')} presents; current-run checklist passed",
        fixture={"name": "SCN-BOOT/STATE/SHUTDOWN sequence", "sha256": "inline-fixture"},
        manual=manual,
        operation="Observe the three timed stages, then record the current-run checklist",
    )


def test_m3_dspi_003(caplog) -> None:
    config = rpi_config("M3-DSPI-003")
    missing = replace(
        config.core.display,
        native_library_path=config.core.display.native_library_path.with_name("missing-libdisplay.so"),
    )
    isolated = replace(
        DEFAULT_CONFIG,
        core=replace(DEFAULT_CONFIG.core, display=missing),
    )

    async def scenario() -> None:
        bus = EventBus()
        rm = ResourceManager(isolated, bus)
        M3Composition()(rm, bus, isolated)
        with caplog.at_level(logging.WARNING):
            await rm.start()
        record = rm._records["core.display"]
        assert record.using_null is True
        assert type(record.instance).__name__ == "NullDisplay"
        assert rm.capability_of("display") is False
        assert "artifact is unavailable" in caplog.text
        assert rm._startup_complete is True
        report = await rm.stop_all()
        assert report.failures == ()

    asyncio.run(scenario())
    record_result(
        "M3-DSPI-003",
        expected="missing native display falls back through RM, display=False, main flow continues",
        actual="RM owns NullDisplay; capability false; warning logged; startup/shutdown completed",
        fixture={"name": "missing native-library path", "sha256": "deterministic-invalid-artifact"},
    )


def test_m3_dspi_004() -> None:
    config = rpi_config("M3-DSPI-004")
    baseline_threads = {thread.ident for thread in threading.enumerate()}
    baseline_fds = _open_bus_fds()

    async def scenario() -> list[dict[str, object]]:
        display = make_display(config.core.display)
        cycles: list[dict[str, object]] = []
        for index in range(2):
            await display.start()
            arbiter = DisplayArbiter(display, Oled128Renderer())
            await arbiter.start()
            arbiter.write_main(DisplayHint("main.text", {"text": f"reopen {index + 1}"}))
            await arbiter.stop()
            await display.stop()
            await display.stop()
            assert display._handle == 0 and display._lib is None and display._back_buffer is None
            assert _open_bus_fds() == baseline_fds
            cycles.append({"cycle": index + 1, "handle": display._handle, "fds": _open_bus_fds()})
        return cycles

    cycles = asyncio.run(scenario())
    residual_threads = [
        thread.name for thread in threading.enumerate()
        if thread.ident not in baseline_threads and thread.is_alive()
    ]
    assert residual_threads == []
    record_result(
        "M3-DSPI-004",
        expected="two arbiter write_main cycles reopen; each stop closes handle/GPIO/SPI/thread; stop idempotent",
        actual=f"cycles={cycles}; residual_threads={residual_threads}",
        fixture={"name": "two lifecycle reopen intents", "sha256": "inline-fixture"},
    )


def test_m3_dspi_005() -> None:
    config = rpi_config("M3-DSPI-005")
    fixture = _orientation_fixture()

    class FixtureRenderer:
        def validate(self, hint) -> None:
            assert hint.template == "main.text"
        def render(self, *, size, model) -> bytes:
            assert size == (128, 128)
            return fixture

    async def scenario() -> dict:
        display = make_display(config.core.display)
        await display.start()
        pattern = DisplayArbiter(display, FixtureRenderer())
        await pattern.start()
        pattern.write_main(DisplayHint("main.text", {"text": "orientation-bars"}))
        await asyncio.sleep(_observation_seconds())
        await pattern.stop()

        content = DisplayArbiter(display, Oled128Renderer())
        await content.start()
        content.write_status_slot("state", DisplayHint("status.state", {"state": "IDLE"}))
        content.write_main(DisplayHint("main.text", {"text": "方向測試 ABC 123"}))
        await asyncio.sleep(_observation_seconds())
        manual = require_manual(
            "M3-DSPI-005",
            ("arrow_up", "no_mirror", "rgb_correct", "text_readable", "no_flicker"),
        )
        await content.stop()
        await display.stop()
        return manual

    manual = asyncio.run(scenario())
    record_result(
        "M3-DSPI-005",
        expected="rotation 0, no mirror, RGB565 primaries correct, text readable, no obvious flicker",
        actual="fixed orientation/color fixture and product renderer shown; current-run checklist passed",
        fixture={"name": "four-quadrant RGBW + up-arrow", "sha256": hashlib.sha256(fixture).hexdigest()},
        manual=manual,
        operation="Observe color/arrow stage, then text stage, and record all checks",
    )


def test_m3_dspi_006() -> None:
    config = rpi_config("M3-DSPI-006")

    async def present(display) -> None:
        display.clear(); display.write_pixels(_FRAME); display.show()

    async def scenario() -> list[float]:
        display = make_display(config.core.display)
        await display.start()
        samples: list[float] = []
        try:
            for _ in range(10):
                await present(display)
            for _ in range(100):
                started = monotonic()
                await present(display)
                elapsed = monotonic() - started
                assert elapsed < 1
                samples.append(elapsed)
        finally:
            await display.stop()
        return samples

    samples = asyncio.run(scenario())
    record_result(
        "M3-DSPI-006",
        expected="100 full-frame presents each complete under 1 second; report raw latency",
        actual=f"100/100 completed; p95={quantiles(samples, n=100)[94]:.6f}s",
        fixture={"name": "32768-byte red RGB565 frame", "sha256": hashlib.sha256(_FRAME).hexdigest()},
        raw_latency_seconds=samples,
        p50=quantiles(samples, n=100)[49],
        p95=quantiles(samples, n=100)[94],
        maximum=max(samples),
    )
