#!/usr/bin/env python3
"""
Snowboard Hardware Diagnostic Tool (Automated)

This tool automatically verifies hardware peripherals (Audio, Display, Camera, GPIO).
It runs without requiring human visual or auditory inspection, using programmatic 
checks to determine if the hardware is returning expected signals.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import asyncio
import logging
import math
from array import array
from typing import AsyncIterator

from sbd.core.config import load_config
from sbd.core.audio.alsa.input import AlsaAudioInput
from sbd.core.audio.alsa.output import AlsaAudioOutput
from sbd.core.display.ssd1351.driver import DisplayDriver as SSD1351Driver
from sbd.core.display.renderer import Oled128Renderer
from sbd.core.camera.picamera2.driver import PiCamera
from sbd.core.gpio.gpiod.driver import GpiodGPIO

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("hw_diag")


def _calculate_rms(frames: list[bytes]) -> float:
    """Calculate the Root Mean Square of 16-bit PCM audio frames."""
    if not frames:
        return 0.0
    
    pcm_data = array('h')
    for frame in frames:
        # Assuming little-endian 16-bit PCM
        pcm_data.frombytes(frame)
        
    if not pcm_data:
        return 0.0
        
    sum_squares = sum(float(sample) * float(sample) for sample in pcm_data)
    return math.sqrt(sum_squares / len(pcm_data))


async def _capture_audio(input_device: AlsaAudioInput, seconds: float = 2.0) -> list[bytes]:
    frames = []
    
    async def _read():
        async for frame in input_device.frames():
            frames.append(frame)
            
    task = asyncio.create_task(_read())
    await asyncio.sleep(seconds)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
        
    return frames


async def test_audio(config) -> bool:
    logger.info("=== Testing Audio ===")
    try:
        audio_in = AlsaAudioInput(config.core.audio)
        audio_out = AlsaAudioOutput(config.core.audio)
        
        await audio_in.start()
        await audio_out.start()
        
        # 1. Test Mic
        logger.info("Recording for 2 seconds to check noise floor...")
        frames = await _capture_audio(audio_in, 2.0)
        
        rms = _calculate_rms(frames)
        logger.info(f"Captured {len(frames)} frames. Audio RMS: {rms:.2f}")
        if rms < 1.0:
            logger.error("Audio RMS is too low (complete silence). Mic might be disconnected or muted.")
            return False
            
        # 2. Test Speaker (Driver level)
        logger.info("Sending blank frames to speaker to test driver binding...")
        async def _playback_stream() -> AsyncIterator[bytes]:
            # Generate 1 second of silence
            yield bytes(48000 * 2)
                
        await audio_out.play(_playback_stream())
        
        await audio_in.stop()
        await audio_out.stop()
        logger.info("✅ Audio test passed.\n")
        return True
    except Exception as e:
        logger.error(f"❌ Audio test failed: {e}\n", exc_info=True)
        return False


async def test_display(config) -> bool:
    logger.info("=== Testing Display ===")
    try:
        driver = SSD1351Driver(config.core.display)
        await driver.start()
        
        from sbd.core.display.renderer import RenderModel
        from sbd.core.display.hints import DisplayHint
        
        renderer = Oled128Renderer()
        model = RenderModel(
            status_slots=(("state", DisplayHint("status.state", {"state": "IDLE"})),),
            main=DisplayHint("main.text", {"text": "HW Diag OK"}),
            fullscreen=None
        )
        img_bytes = renderer.render(size=(config.core.display.width, config.core.display.height), model=model)
        
        # If writing pixels doesn't throw an ABI/IO error, the SPI connection is generally responsive.
        driver.clear()
        driver.write_pixels(img_bytes)
        driver.show()
        
        await asyncio.sleep(0.5)
        driver.clear()
        driver.show()
        await driver.stop()
        
        logger.info("✅ Display test passed (SPI driver successful).\n")
        return True
    except Exception as e:
        logger.error(f"❌ Display test failed: {e}\n", exc_info=True)
        return False


async def test_camera(config) -> bool:
    logger.info("=== Testing Camera ===")
    try:
        cam = PiCamera(config.core.camera)
        await cam.start()
        
        img_bytes = await cam.capture()
        logger.info(f"Captured image of size: {len(img_bytes)} bytes")
        
        await cam.stop()
        
        # Verify valid payload based on configured format
        cam_format = getattr(config.core.camera, 'format', 'JPEG').upper()
        
        if cam_format == 'RGB':
            expected_size = config.core.camera.width * config.core.camera.height * 3
            if len(img_bytes) != expected_size:
                logger.error(f"Captured RGB image size {len(img_bytes)} does not match expected {expected_size} bytes.")
                return False
        else:
            if len(img_bytes) < 1024:
                logger.error("Captured image is abnormally small.")
                return False
                
            if not img_bytes.startswith(b'\xff\xd8'):
                logger.error("Captured image does not have a valid JPEG header.")
                return False
            
        logger.info(f"✅ Camera test passed (Valid {cam_format} captured).\n")
        return True
    except Exception as e:
        logger.error(f"❌ Camera test failed: {e}\n", exc_info=True)
        return False


async def test_gpio(config) -> bool:
    logger.info("=== Testing GPIO ===")
    try:
        gpio = GpiodGPIO(config.core.gpio)
        await gpio.start()
        
        pressed = asyncio.Event()
        
        async def on_button_press(event):
            pressed.set()
            
        pin = 23 
        if "conversation" in config.core.gpio.pins:
            pin = config.core.gpio.pins["conversation"].pin
            
        # 1. Test Input Binding
        await gpio.register_input(pin, "falling", on_button_press, debounce_ms=50)
        logger.info(f"GPIO chip bind successful for Pin {pin}.")
        
        # 2. Automated bind verification only (Zero interaction)
        logger.info("✅ GPIO test passed (Driver bind successful, physical circuit unverified).\n")
            
        await gpio.unregister(pin)
        await gpio.stop()
        return True
    except Exception as e:
        logger.error(f"❌ GPIO test failed: {e}\n", exc_info=True)
        return False


async def main():
    logger.info("Loading configuration...")
    config_path = Path("config.local.yaml") if Path("config.local.yaml").exists() else (Path("config.m3.local.yaml") if Path("config.m3.local.yaml").exists() else Path("config.local.yaml"))
    config = load_config(local_path=config_path)
    # Override config for diag
    from sbd.core.config.models import AudioFormatConfig
    import dataclasses
    
    # Reconstruct nested frozen dataclasses
    audio_out = dataclasses.replace(config.core.audio.output, native_format=AudioFormatConfig(sample_rate=48000, channels=2, sample_format='s32_le'))
    audio_in = dataclasses.replace(config.core.audio.input, native_format=AudioFormatConfig(sample_rate=48000, channels=2, sample_format='s32_le'))
    audio_in = dataclasses.replace(audio_in, device='default', channel_index=0)
    audio_out = dataclasses.replace(audio_out, device='default')
    new_audio = dataclasses.replace(config.core.audio, output=audio_out, input=audio_in)
    
    new_display = dataclasses.replace(config.core.display, native_abi_version=1)
    new_core = dataclasses.replace(config.core, audio=new_audio, display=new_display)
    config = dataclasses.replace(config, core=new_core)



    
    results = {
        "Audio": await test_audio(config),
        "Display": await test_display(config),
        "Camera": await test_camera(config),
        "GPIO": await test_gpio(config),
    }
    
    logger.info("=== Hardware Diagnostic Summary ===")
    all_passed = True
    for component, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"{component}: {status}")
        if not passed:
            all_passed = False
            
    if all_passed:
        logger.info("All automated checks PASSED.")
        sys.exit(0)
    else:
        logger.error("One or more hardware checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
