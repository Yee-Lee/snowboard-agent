"""Thin Python adapter for the versioned native display ABI."""

from __future__ import annotations

import ctypes
import logging
from pathlib import Path

from .profiles import DisplayPinConfig
from .protocol import DisplayInfo

logger = logging.getLogger(__name__)

DISPLAY_ABI_VERSION = 1
DISPLAY_CONFIG_VERSION = 1
DISPLAY_PIXEL_FORMAT_RGB565 = 1
DISPLAY_BYTE_ORDER_MSB_FIRST = 1

DISPLAY_OK = 0
DISPLAY_E_INVALID_ARGUMENT = -1
DISPLAY_E_ABI_MISMATCH = -2
DISPLAY_E_BAD_CONFIG = -3
DISPLAY_E_ALREADY_OPEN = -4
DISPLAY_E_NOT_OPEN = -5
DISPLAY_E_INVALID_HANDLE = -6
DISPLAY_E_BUFFER_SIZE = -7
DISPLAY_E_WRONG_THREAD = -8


class DisplayNativeError(RuntimeError):
    """Native GPIO, SPI, panel, or internal operation failed."""


class DisplayAbiError(DisplayNativeError):
    """The loaded artifact does not implement the required ABI."""


class _CDisplayInfo(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("struct_size", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixel_format", ctypes.c_uint32),
        ("byte_order", ctypes.c_uint32),
        ("buffer_bytes", ctypes.c_uint32),
        ("name", ctypes.c_char * 64),
    ]


class _CSpiConfig(ctypes.Structure):
    _fields_ = [
        ("bus", ctypes.c_int32),
        ("chip", ctypes.c_int32),
        ("speed_hz", ctypes.c_uint32),
        ("mode", ctypes.c_uint32),
    ]


class _CGpiochipConfig(ctypes.Structure):
    _fields_ = [("chip_index", ctypes.c_int32)]


class _CDisplayPinConfig(ctypes.Structure):
    _fields_ = [
        ("rst", ctypes.c_int32),
        ("dc", ctypes.c_int32),
        ("cs", ctypes.c_int32),
        ("bl", ctypes.c_int32),
    ]


class _CDisplayConfig(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("struct_size", ctypes.c_uint32),
        ("pins", _CDisplayPinConfig),
        ("spi", _CSpiConfig),
        ("gpio_chip", _CGpiochipConfig),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("rotation_degrees", ctypes.c_uint32),
        ("pixel_format", ctypes.c_uint32),
        ("byte_order", ctypes.c_uint32),
        ("buffer_bytes", ctypes.c_uint32),
    ]


def _build_c_config(
    cfg: DisplayPinConfig,
    width: int,
    height: int,
) -> _CDisplayConfig:
    if cfg.gpio_chip.chip_index < 0:
        raise ValueError("gpio_chip.chip_index must be resolved before start()")
    if cfg.spi.speed_hz <= 0:
        raise ValueError("spi.speed_hz must be positive")

    config = _CDisplayConfig()
    config.abi_version = DISPLAY_CONFIG_VERSION
    config.struct_size = ctypes.sizeof(_CDisplayConfig)
    config.pins.rst = cfg.pins.rst
    config.pins.dc = cfg.pins.dc
    config.pins.cs = cfg.pins.cs
    config.pins.bl = cfg.pins.bl
    config.spi.bus = cfg.spi.bus
    config.spi.chip = cfg.spi.chip
    config.spi.speed_hz = cfg.spi.speed_hz
    config.spi.mode = cfg.spi.mode
    config.gpio_chip.chip_index = cfg.gpio_chip.chip_index
    config.width = width
    config.height = height
    config.rotation_degrees = 0
    config.pixel_format = DISPLAY_PIXEL_FORMAT_RGB565
    config.byte_order = DISPLAY_BYTE_ORDER_MSB_FIRST
    config.buffer_bytes = width * height * 2
    return config


class CtypesDisplayDevice:
    """Adapter with async lifecycle and synchronous single-thread rendering."""

    def __init__(
        self,
        so_path: str | Path,
        logical_width: int,
        logical_height: int,
        *,
        pin_config: DisplayPinConfig,
        scale_to_native: bool = False,
        native_width: int = 0,
        native_height: int = 0,
    ) -> None:
        self._so_path = Path(so_path)
        self._pin_config = pin_config
        self._scale = scale_to_native
        self._native_width = native_width or logical_width
        self._native_height = native_height or logical_height
        self._lib: ctypes.CDLL | None = None
        self._handle = 0
        self._back_buffer: bytearray | None = None
        self.info = DisplayInfo(
            width=self._native_width,
            height=self._native_height,
            logical_width=logical_width,
            logical_height=logical_height,
        )

    async def start(self) -> None:
        if self._lib is not None or self._handle != 0:
            raise RuntimeError("CtypesDisplayDevice already started")
        self._open_sync()
        self._back_buffer = bytearray(self._native_width * self._native_height * 2)

    async def stop(self) -> None:
        if self._lib is None and self._handle == 0:
            self._back_buffer = None
            return
        try:
            self._close_sync()
        finally:
            self._back_buffer = None

    def clear(self) -> None:
        buffer = self._require_buffer("clear")
        buffer[:] = b"\x00" * len(buffer)

    def write_pixels(self, frame: bytes) -> None:
        if not isinstance(frame, bytes):
            raise TypeError("write_pixels() requires bytes")
        buffer = self._require_buffer("write_pixels")
        expected = self._native_width * self._native_height * 2
        if len(frame) != expected:
            raise ValueError(f"Expected {expected} bytes, got {len(frame)}")
        buffer[:] = frame

    def show(self) -> None:
        buffer = self._require_buffer("show")
        self._present_sync(bytes(buffer))

    def size(self) -> tuple[int, int]:
        return (self._native_width, self._native_height)

    def _require_buffer(self, operation: str) -> bytearray:
        if self._back_buffer is None or self._lib is None or self._handle == 0:
            raise RuntimeError(f"{operation} called before start()")
        return self._back_buffer

    def _open_sync(self) -> None:
        logger.info("[CtypesDisplay] loading %s", self._so_path)
        lib = ctypes.CDLL(str(self._so_path))
        self._lib = lib
        try:
            self._setup_signatures()
            artifact_abi = int(lib.display_abi_version())
            if artifact_abi != DISPLAY_ABI_VERSION:
                raise DisplayAbiError(
                    f"display ABI mismatch: expected {DISPLAY_ABI_VERSION}, "
                    f"artifact reports {artifact_abi}"
                )

            config = _build_c_config(
                self._pin_config,
                self._native_width,
                self._native_height,
            )
            handle = ctypes.c_int32(0)
            status = int(lib.display_open(ctypes.byref(config), ctypes.byref(handle)))
            self._raise_status("display_open", status)
            if handle.value == 0:
                raise DisplayNativeError("display_open returned an invalid handle")
            self._handle = handle.value
            self._verify_info()
        except Exception:
            self._handle = 0
            self._lib = None
            raise

    def _verify_info(self) -> None:
        assert self._lib is not None
        info = _CDisplayInfo()
        status = int(self._lib.display_get_info(self._handle, ctypes.byref(info)))
        self._raise_status("display_get_info", status)
        expected_bytes = self._native_width * self._native_height * 2
        if (
            info.abi_version != DISPLAY_ABI_VERSION
            or info.struct_size != ctypes.sizeof(_CDisplayInfo)
            or info.width != self._native_width
            or info.height != self._native_height
            or info.pixel_format != DISPLAY_PIXEL_FORMAT_RGB565
            or info.byte_order != DISPLAY_BYTE_ORDER_MSB_FIRST
            or info.buffer_bytes != expected_bytes
        ):
            try:
                self._lib.display_close(self._handle)
            finally:
                self._handle = 0
            raise DisplayAbiError("native display info does not match requested config")

    def _present_sync(self, frame: bytes) -> None:
        if self._lib is None or self._handle == 0:
            raise RuntimeError("CtypesDisplayDevice not started")
        c_buffer = (ctypes.c_uint8 * len(frame)).from_buffer_copy(frame)
        status = int(
            self._lib.display_present_rgb565(
                self._handle,
                ctypes.cast(c_buffer, ctypes.POINTER(ctypes.c_uint8)),
                len(frame),
            )
        )
        self._raise_status("display_present_rgb565", status)

    def _close_sync(self) -> None:
        lib = self._lib
        handle = self._handle
        if lib is None or handle == 0:
            self._lib = None
            self._handle = 0
            return
        status = int(lib.display_close(handle))
        self._raise_status("display_close", status)
        self._handle = 0
        self._lib = None

    def _setup_signatures(self) -> None:
        lib = self._lib
        assert lib is not None
        lib.display_abi_version.restype = ctypes.c_uint32
        lib.display_abi_version.argtypes = []
        lib.display_open.restype = ctypes.c_int32
        lib.display_open.argtypes = [
            ctypes.POINTER(_CDisplayConfig),
            ctypes.POINTER(ctypes.c_int32),
        ]
        lib.display_get_info.restype = ctypes.c_int32
        lib.display_get_info.argtypes = [
            ctypes.c_int32,
            ctypes.POINTER(_CDisplayInfo),
        ]
        lib.display_present_rgb565.restype = ctypes.c_int32
        lib.display_present_rgb565.argtypes = [
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
        ]
        lib.display_close.restype = ctypes.c_int32
        lib.display_close.argtypes = [ctypes.c_int32]

    @staticmethod
    def _raise_status(operation: str, status: int) -> None:
        if status == DISPLAY_OK:
            return
        message = f"{operation} failed with native status {status}"
        if status == DISPLAY_E_ABI_MISMATCH:
            raise DisplayAbiError(message)
        if status in {
            DISPLAY_E_INVALID_ARGUMENT,
            DISPLAY_E_BAD_CONFIG,
            DISPLAY_E_BUFFER_SIZE,
        }:
            raise ValueError(message)
        if status in {
            DISPLAY_E_ALREADY_OPEN,
            DISPLAY_E_NOT_OPEN,
            DISPLAY_E_INVALID_HANDLE,
            DISPLAY_E_WRONG_THREAD,
        }:
            raise RuntimeError(message)
        raise DisplayNativeError(message)


__all__ = ["CtypesDisplayDevice", "DisplayAbiError", "DisplayNativeError"]
