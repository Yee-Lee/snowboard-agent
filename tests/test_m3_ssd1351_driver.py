"""Host conformance tests for the accepted SSD1351 ABI v1 bridge.

These tests use a temporary native stub.  They validate Core's ctypes boundary
but do not replace the six Raspberry Pi acceptance cards.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.core.config.models import DisplayConfig
from sbd.core.display import make_display


_STUB = r'''
#include <stdint.h>
typedef int32_t DisplayHandle;
typedef struct { int32_t rst, dc, cs, bl; } Pins;
typedef struct { int32_t bus, chip; uint32_t speed_hz, mode; } Spi;
typedef struct { int32_t chip_index; } Gpiochip;
typedef struct { uint32_t abi_version, struct_size; Pins pins; Spi spi; Gpiochip gpio_chip; uint32_t width, height, rotation_degrees, pixel_format, byte_order, buffer_bytes; } Config;
typedef struct { uint32_t abi_version, struct_size, width, height, pixel_format, byte_order, buffer_bytes; char name[64]; } Info;
static int opened; static unsigned int presents; static Config received;
uint32_t display_abi_version(void) { return 1; }
int32_t display_open(const Config *config, DisplayHandle *handle) { received = *config; opened = 1; *handle = 41; return 0; }
int32_t display_get_info(DisplayHandle handle, Info *info) { if (!opened || handle != 41) return -5; info->abi_version=1; info->struct_size=sizeof(*info); info->width=128; info->height=128; info->pixel_format=1; info->byte_order=1; info->buffer_bytes=32768; return 0; }
int32_t display_present_rgb565(DisplayHandle handle, const uint8_t *data, uint32_t length) { if (!opened || handle != 41) return -5; if (!data || length != 32768) return -7; presents++; return 0; }
int32_t display_close(DisplayHandle handle) { if (!opened || handle != 41) return -5; opened = 0; return 0; }
int32_t test_presents(void) { return (int32_t)presents; }
int32_t test_gpio_chip_index(void) { return received.gpio_chip.chip_index; }
int32_t test_cs(void) { return received.pins.cs; }
'''


def _artifact(tmp_path: Path) -> Path:
    source = tmp_path / "stub.c"
    artifact = tmp_path / "libdisplay_stub.dylib"
    source.write_text(_STUB)
    subprocess.run(["cc", "-shared", "-fPIC", str(source), "-o", str(artifact)], check=True)
    return artifact


def _config(artifact: Path, *, gpio_chip_index: int = 7) -> DisplayConfig:
    return DisplayConfig(
        driver="ssd1351", native_library_path=artifact,
        native_library_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        native_abi_version=1, spi_device="/dev/spidev0.0", spi_speed_hz=4_000_000,
        spi_mode=0, spi_chip_select=0, gpio_chip_index=gpio_chip_index,
        dc_bcm=24, reset_bcm=25,
    )


def test_ssd1351_driver_maps_validated_config_and_flushes_once(tmp_path: Path) -> None:
    from sbd.core.display.ssd1351.driver import DisplayDriver

    artifact = _artifact(tmp_path)
    driver = make_display(_config(artifact))
    assert isinstance(driver, DisplayDriver)

    async def scenario() -> None:
        await driver.start()
        assert driver.size() == (128, 128)
        driver.clear()
        driver.write_pixels(b"\xf8\x00" * 16_384)
        driver.show()
        library = driver._lib
        assert library is not None
        assert library.test_presents() == 1
        assert library.test_gpio_chip_index() == 7
        assert library.test_cs() == -1
        before = bytes(driver._back_buffer or b"")
        with pytest.raises(ValueError, match="32768"):
            driver.write_pixels(b"bad")
        assert bytes(driver._back_buffer or b"") == before
        await driver.stop()
        await driver.stop()
        with pytest.raises(RuntimeError, match="before start"):
            driver.show()
    asyncio.run(scenario())


def test_ssd1351_driver_rejects_tampered_artifact_before_load(tmp_path: Path) -> None:
    from sbd.core.display.ssd1351.driver import DisplayAbiError, DisplayDriver

    artifact = _artifact(tmp_path)
    driver = DisplayDriver(_config(artifact))
    artifact.write_bytes(b"tampered")
    with pytest.raises(DisplayAbiError, match="checksum"):
        asyncio.run(driver.start())


def test_ssd1351_driver_rejects_unselected_abi_before_load(tmp_path: Path) -> None:
    from sbd.core.display.ssd1351.driver import DisplayAbiError, DisplayDriver

    artifact = _artifact(tmp_path)
    config = _config(artifact)
    driver = DisplayDriver(replace(config, native_abi_version=2))
    with pytest.raises(DisplayAbiError, match="unsupported"):
        asyncio.run(driver.start())
