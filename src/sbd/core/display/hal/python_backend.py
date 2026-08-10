"""
Python display backend using the official Waveshare Python library (luma/spidev based).
This backend avoids compiling C extensions.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .profiles import DisplayPinConfig
from .protocol import DisplayDevice, DisplayInfo, Rect, Rgb565Frame

logger = logging.getLogger(__name__)

class PythonDisplayDevice:
    """
    Display backend that uses the official waveshare_OLED Python library.
    """
    def __init__(self, profile_name: str, width: int, height: int, pin_config: DisplayPinConfig):
        self.info = DisplayInfo(width=width, height=height, name=profile_name)
        self.pin_config = pin_config
        self._disp = None
        self._is_open = False

    async def open(self) -> None:
        if self._is_open:
            return

        import sys
        import os
        # Add the waveshare path to sys.path
        waveshare_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../../../../waveshare/OLED_Module_Code/RaspberryPi/python/lib"
        ))
        if waveshare_path not in sys.path:
            sys.path.append(waveshare_path)

        try:
            from waveshare_OLED import OLED_1in5_rgb, config
        except ImportError as e:
            logger.error(f"[PythonBackend] Failed to import waveshare_OLED: {e}")
            raise

        logger.info(f"[PythonBackend] Initializing {self.info.name} using official Python library")
        
        # Override the config defaults to match our pin_config
        config.RaspberryPi.__init__.__defaults__ = (
            config.spidev.SpiDev(self.pin_config.spi.bus, self.pin_config.spi.chip),
            self.pin_config.spi.speed_hz,
            self.pin_config.pins.rst,
            self.pin_config.pins.dc,
            self.pin_config.pins.bl if self.pin_config.pins.bl >= 0 else 18,
            1000,
            None
        )

        self._disp = OLED_1in5_rgb.OLED_1in5_rgb()
        self._disp.Init()
        self._disp.clear()
        
        self._is_open = True
        logger.info(f"[PythonBackend] init OK, speed={self.pin_config.spi.speed_hz}Hz")

    async def present(self, frame: Rgb565Frame) -> None:
        if not self._is_open or not self._disp:
            return
            
        # Set window address
        self._disp.command(0x15)
        self._disp.data(0x00)
        self._disp.data(0x7f)
        self._disp.command(0x75)
        self._disp.data(0x00)
        self._disp.data(0x7f)
        self._disp.command(0x5C)
        
        # DC high for data
        self._disp.digital_write(self._disp.DC_PIN, True)
        
        # Fast chunked write to SPI
        chunk_size = 4096
        buf = memoryview(frame)
        for i in range(0, len(buf), chunk_size):
            chunk = buf[i:i+chunk_size].tolist()
            self._disp.spi.writebytes(chunk)

    async def present_rect(self, rect: Rect, frame: Rgb565Frame) -> None:
        await self.present(frame)

    async def clear(self) -> None:
        if self._is_open and self._disp:
            self._disp.clear()

    async def close(self) -> None:
        if self._is_open and self._disp:
            self._disp.module_exit()
            self._disp = None
            self._is_open = False
