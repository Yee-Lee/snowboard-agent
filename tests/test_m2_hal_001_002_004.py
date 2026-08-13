"""M2-HAL-001/002/004 mock and null HAL contract tests."""

from __future__ import annotations

import asyncio
import sys

import pytest

from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.audio.null import NullAudioInput, NullAudioOutput
from sbd.core.camera import make_camera
from sbd.core.camera.mock import MockCamera
from sbd.core.camera.null import NullCamera
from sbd.core.config.models import (
    AudioConfig,
    AudioFormatConfig,
    AudioInputConfig,
    CameraConfig,
    DisplayConfig,
    GPIOConfig,
)
from sbd.core.display import make_display
from sbd.core.display.mock import MockDisplay
from sbd.core.display.null import NullDisplay
from sbd.core.gpio import make_gpio
from sbd.core.gpio.mock import MockGPIO


def _jpeg_dimensions(value: bytes) -> tuple[int, int]:
    assert value.startswith(b"\xff\xd8") and value.endswith(b"\xff\xd9")
    offset = 2
    while offset < len(value) - 1:
        assert value[offset] == 0xFF
        marker = value[offset + 1]
        if marker == 0xDA:
            break
        length = int.from_bytes(value[offset + 2 : offset + 4], "big")
        if marker == 0xC0:
            height = int.from_bytes(value[offset + 5 : offset + 7], "big")
            width = int.from_bytes(value[offset + 7 : offset + 9], "big")
            return width, height
        offset += 2 + length
    raise AssertionError("JPEG has no baseline SOF marker")


def test_m2_hal_001_factories_lazy_load_only_selected_mock_backends() -> None:
    audio = AudioConfig(driver="mock")
    display = DisplayConfig(driver="mock")
    camera = CameraConfig(driver="mock", width=8, height=8)
    gpio = GPIOConfig(driver="mock")
    assert make_audio_input(audio).__class__.__name__ == "MockAudioInput"
    assert make_audio_output(audio).__class__.__name__ == "MockAudioOutput"
    assert make_display(display).__class__.__name__ == "MockDisplay"
    assert make_camera(camera).__class__.__name__ == "MockCamera"
    assert make_gpio(gpio).__class__.__name__ == "MockGPIO"
    forbidden = {"sounddevice", "picamera2", "gpiod", "litert_lm", "LiteRT_LM"}
    assert forbidden.isdisjoint({name.split(".", 1)[0] for name in sys.modules})


def test_m2_hal_002_null_audio_iterator_exclusive_reopen_and_consumption() -> None:
    async def run() -> None:
        config = AudioConfig(
            driver="null",
            input=AudioInputConfig(
                stream_format=AudioFormatConfig(sample_rate=8_000, channels=2),
                frame_duration_ms=10,
            ),
        )
        audio_in = NullAudioInput(config)
        audio_out = NullAudioOutput()
        await audio_in.start()
        await audio_out.start()
        first = audio_in.frames()
        with pytest.raises(RuntimeError, match="already streaming"):
            audio_in.frames()
        frame = await anext(first)
        assert len(frame) == 8_000 * 10 // 1000 * 2 * 2
        assert set(frame) == {0}
        await first.aclose()

        reopened = audio_in.frames()
        assert len(await anext(reopened)) == len(frame)
        await reopened.aclose()

        consumed: list[bytes] = []
        async def pcm():
            for value in (b"a", b"b"):
                consumed.append(value)
                yield value
        await audio_out.play(pcm())
        assert consumed == [b"a", b"b"]
        await audio_in.stop()
        await audio_in.stop()
        await audio_out.stop()
        await audio_out.stop()

    asyncio.run(run())


def test_m2_hal_002_null_display_and_camera_return_format_valid_values() -> None:
    async def run() -> None:
        display = NullDisplay()
        await display.start()
        assert display.size() == (0, 0)
        display.clear()
        display.write_pixels(b"")
        display.show()
        display.write_pixels(b"broken")
        await display.stop()
        await display.stop()

        rgb = NullCamera(CameraConfig(driver="null", format="RGB", width=4, height=2))
        yuv = NullCamera(CameraConfig(driver="null", format="YUV", width=4, height=2))
        jpeg = NullCamera(CameraConfig(driver="null", format="JPEG", width=13, height=9))
        assert len(await rgb.capture()) == 4 * 2 * 3
        yuv_value = await yuv.capture()
        assert len(yuv_value) == 4 * 2 * 3 // 2
        assert yuv_value[8:] == bytes((0x80,)) * 4
        jpeg_value = await jpeg.capture()
        assert _jpeg_dimensions(jpeg_value) == (13, 9)
        assert b"JFIF\x00" in jpeg_value

    asyncio.run(run())


def test_m2_hal_004_mock_display_camera_and_gpio_contracts() -> None:
    async def run() -> None:
        display = MockDisplay(DisplayConfig(driver="mock"))
        await display.start()
        assert display.size() == (128, 128)
        pixels = bytes(32768)
        display.write_pixels(pixels)
        assert display.shown_buffers == []
        display.show()
        assert display.shown_buffers == [pixels]
        with pytest.raises(ValueError):
            display.write_pixels(b"short")

        fixture = b"fixture-image"
        camera = MockCamera(CameraConfig(driver="mock", width=2, height=2), images=(fixture,))
        assert await camera.capture() == fixture

        gpio = MockGPIO()
        await gpio.start()
        good_events = []
        async def good(event) -> None:
            good_events.append(event)
        async def bad(event) -> None:
            raise RuntimeError("isolated callback")
        await gpio.register_input(1, "both", good, debounce_ms=10)
        with pytest.raises(ValueError):
            await gpio.register_input(1, "rising", good)
        await gpio.register_input(2, "rising", bad)
        assert await gpio.simulate_event(1, "rising", at=1.0)
        assert not await gpio.simulate_event(1, "falling", at=1.005)
        assert await gpio.simulate_event(1, "falling", at=1.020)
        assert await gpio.simulate_event(2, "rising", at=1.0)
        await gpio.wait_callbacks()
        assert tuple(event.edge for event in good_events) == ("rising", "falling")
        await gpio.unregister(1)
        await gpio.unregister(1)
        await gpio.configure_output(3, initial=False)
        assert gpio.output_value(3) is False
        await gpio.set_output(3, True)
        assert gpio.output_value(3) is True
        with pytest.raises(ValueError):
            await gpio.set_output(4, True)
        await gpio.stop()

    asyncio.run(run())
