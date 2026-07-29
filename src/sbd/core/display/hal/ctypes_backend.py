"""
ctypes-based display backend.

Loads libdisplay.so and calls the stable C ABI:

    display_open(config: DisplayConfig*) -> handle (int)
    display_get_info(handle) -> DisplayInfo
    display_present_rgb565(handle, buffer, length)
    display_present_rect_rgb565(handle, x, y, width, height, buffer, length)
    display_clear(handle)
    display_close(handle)

Pin mapping is passed to display_open() via a ctypes struct that mirrors
the C-side DisplayConfig (pin_config.h).  No pin is hardcoded in Python.

All calls are made from a single dedicated I/O thread enforced by the
DisplayService — never directly from any other thread.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
from pathlib import Path
from typing import Optional

from .protocol import DisplayDevice, DisplayInfo, Rect, Rgb565Frame
from .profiles import DisplayPinConfig, PinConfig, SpiConfig, GpiochipConfig

logger = logging.getLogger(__name__)


class _CDisplayInfo(ctypes.Structure):
    """Must match the C-side DisplayInfo layout in display.h."""
    _fields_ = [
        ("width",  ctypes.c_int),
        ("height", ctypes.c_int),
        ("name",   ctypes.c_char * 64),
    ]


class _CSpiConfig(ctypes.Structure):
    """Mirrors SpiConfig in pin_config.h."""
    _fields_ = [
        ("bus",      ctypes.c_int),
        ("chip",     ctypes.c_int),
        ("speed_hz", ctypes.c_int),
        ("mode",     ctypes.c_int),
    ]


class _CGpiochipConfig(ctypes.Structure):
    """Mirrors GpiochipConfig in pin_config.h."""
    _fields_ = [
        ("chip_index", ctypes.c_int),
    ]


class _CDisplayPinConfig(ctypes.Structure):
    """Mirrors DisplayPinConfig in pin_config.h."""
    _fields_ = [
        ("rst", ctypes.c_int),
        ("dc",  ctypes.c_int),
        ("cs",  ctypes.c_int),
        ("bl",  ctypes.c_int),
    ]


class _CDisplayConfig(ctypes.Structure):
    """Mirrors DisplayConfig in pin_config.h — passed to display_open()."""
    _fields_ = [
        ("pins",      _CDisplayPinConfig),
        ("spi",       _CSpiConfig),
        ("gpio_chip", _CGpiochipConfig),
    ]


def _build_c_config(cfg: DisplayPinConfig) -> _CDisplayConfig:
    """Convert a Python DisplayPinConfig to the ctypes C struct."""
    c = _CDisplayConfig()
    c.pins.rst = cfg.pins.rst
    c.pins.dc  = cfg.pins.dc
    c.pins.cs  = cfg.pins.cs
    c.pins.bl  = cfg.pins.bl
    c.spi.bus      = cfg.spi.bus
    c.spi.chip     = cfg.spi.chip
    c.spi.speed_hz = cfg.spi.speed_hz
    c.spi.mode     = cfg.spi.mode
    c.gpio_chip.chip_index = cfg.gpio_chip.chip_index
    return c


class CtypesDisplayDevice:
    """
    Hardware backend that forwards calls to a compiled libdisplay.so.

    The .so is expected to expose the stable C ABI defined in
    native/include/display.h.  The Python side never touches GPIO/SPI
    directly — all that lives inside the native driver.

    Pin mapping is provided via *pin_config* (a DisplayPinConfig).
    If None, the driver's built-in defaults (from pin_config.h) are used.

    Note: open/present/clear/close MUST be called from the same OS
    thread (the native I/O thread managed by DisplayService).
    """

    def __init__(
        self,
        so_path: str | Path,
        logical_width: int,
        logical_height: int,
        *,
        pin_config: Optional[DisplayPinConfig] = None,
        scale_to_native: bool = False,
        native_width: int = 0,
        native_height: int = 0,
    ) -> None:
        self._so_path = Path(so_path)
        self._logical_width = logical_width
        self._logical_height = logical_height
        self._pin_config = pin_config     # None → pass NULL → driver defaults
        self._scale = scale_to_native
        self._native_width = native_width or logical_width
        self._native_height = native_height or logical_height

        self._lib: Optional[ctypes.CDLL] = None
        self._handle: int = 0
        self.info = DisplayInfo(
            width=self._native_width,
            height=self._native_height,
            logical_width=logical_width,
            logical_height=logical_height,
        )

    # ------------------------------------------------------------------
    # DisplayDevice protocol
    # ------------------------------------------------------------------

    async def open(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._open_sync)

    async def present(self, frame: Rgb565Frame) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._present_sync, bytes(frame))

    async def present_rect(self, rect: Rect, frame: Rgb565Frame) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._present_rect_sync, rect, bytes(frame))

    async def clear(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._clear_sync)

    async def close(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._close_sync)

    # ------------------------------------------------------------------
    # Synchronous helpers (called from executor / I/O thread)
    # ------------------------------------------------------------------

    def _open_sync(self) -> None:
        logger.info("[CtypesDisplay] Loading %s", self._so_path)
        self._lib = ctypes.CDLL(str(self._so_path))
        self._setup_signatures()

        if self._pin_config is not None:
            c_cfg = _build_c_config(self._pin_config)
            self._handle = self._lib.display_open(ctypes.byref(c_cfg))
            logger.info(
                "[CtypesDisplay] open with pins CS=%d DC=%d RST=%d BL=%d SPI%d.%d@%dHz",
                self._pin_config.pins.cs,
                self._pin_config.pins.dc,
                self._pin_config.pins.rst,
                self._pin_config.pins.bl,
                self._pin_config.spi.bus,
                self._pin_config.spi.chip,
                self._pin_config.spi.speed_hz,
            )
        else:
            self._handle = self._lib.display_open(None)
            logger.info("[CtypesDisplay] open with driver built-in pin defaults")

        if self._handle == 0:
            raise RuntimeError(f"display_open() returned 0 (failed) for {self._so_path}")
        logger.info("[CtypesDisplay] open OK, handle=%d", self._handle)

    def _present_sync(self, frame: bytes) -> None:
        if self._lib is None:
            raise RuntimeError("CtypesDisplayDevice not open")
        rc = self._lib.display_present_rgb565(
            self._handle,
            ctypes.c_char_p(frame),
            ctypes.c_int(len(frame)),
        )
        if rc != 0:
            logger.error("[CtypesDisplay] display_present_rgb565 returned %d", rc)

    def _present_rect_sync(self, rect: Rect, frame: bytes) -> None:
        if self._lib is None:
            raise RuntimeError("CtypesDisplayDevice not open")
        rc = self._lib.display_present_rect_rgb565(
            self._handle,
            ctypes.c_int(rect.x),
            ctypes.c_int(rect.y),
            ctypes.c_int(rect.width),
            ctypes.c_int(rect.height),
            ctypes.c_char_p(frame),
            ctypes.c_int(len(frame)),
        )
        if rc != 0:
            logger.error("[CtypesDisplay] display_present_rect_rgb565 returned %d", rc)

    def _clear_sync(self) -> None:
        if self._lib is None:
            return
        self._lib.display_clear(self._handle)

    def _close_sync(self) -> None:
        if self._lib is None:
            return
        self._lib.display_close(self._handle)
        self._handle = 0
        logger.info("[CtypesDisplay] closed")

    def _setup_signatures(self) -> None:
        """Configure ctypes argument / return types for the C ABI."""
        lib = self._lib
        assert lib is not None

        # display_open(config: DisplayConfig*) -> int handle
        # We use c_void_p here so we can pass either byref(c_cfg) or None.
        lib.display_open.restype = ctypes.c_int
        lib.display_open.argtypes = [ctypes.c_void_p]

        # display_present_rgb565(handle, buf, length) -> int error_code
        lib.display_present_rgb565.restype = ctypes.c_int
        lib.display_present_rgb565.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        # display_present_rect_rgb565(handle, x, y, w, h, buf, len) -> int
        lib.display_present_rect_rgb565.restype = ctypes.c_int
        lib.display_present_rect_rgb565.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int,
            ctypes.c_char_p, ctypes.c_int,
        ]

        # display_clear(handle) -> void
        lib.display_clear.restype = None
        lib.display_clear.argtypes = [ctypes.c_int]

        # display_close(handle) -> void
        lib.display_close.restype = None
        lib.display_close.argtypes = [ctypes.c_int]
