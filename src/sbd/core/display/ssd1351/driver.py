"""ctypes adapter for the accepted SSD1351 native display ABI v1.

The native library is deployment-local.  This module intentionally contains no
hardware import or probing until :meth:`DisplayDriver.start`.
"""

from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path

from sbd.core.config.models import DisplayConfig


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
    """The selected artifact does not implement the required ABI."""


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


def _build_c_config(config: DisplayConfig) -> _CDisplayConfig:
    """Map the already validated Core config directly onto ABI v1."""
    if config.gpio_chip_index is None or config.gpio_chip_index < 0:
        raise ValueError("gpio_chip_index must be resolved before start()")
    if config.spi_speed_hz is None or config.spi_speed_hz <= 0:
        raise ValueError("spi_speed_hz must be positive")

    native = _CDisplayConfig()
    native.abi_version = DISPLAY_CONFIG_VERSION
    native.struct_size = ctypes.sizeof(_CDisplayConfig)
    native.pins.rst = config.reset_bcm
    native.pins.dc = config.dc_bcm
    native.pins.cs = -1  # SPI0 CE0 is kernel-owned; never claim it as GPIO.
    native.pins.bl = -1  # The selected OLED fixture has no backlight pin.
    native.spi.bus = 0
    native.spi.chip = config.spi_chip_select
    native.spi.speed_hz = config.spi_speed_hz
    native.spi.mode = config.spi_mode
    native.gpio_chip.chip_index = config.gpio_chip_index
    native.width = config.width
    native.height = config.height
    native.rotation_degrees = config.rotation
    native.pixel_format = DISPLAY_PIXEL_FORMAT_RGB565
    native.byte_order = DISPLAY_BYTE_ORDER_MSB_FIRST
    native.buffer_bytes = config.frame_buffer_bytes
    return native


class DisplayDriver:
    """A full-frame RGB565 MSB-first SSD1351 ``DisplayDevice``."""

    def __init__(self, config: DisplayConfig) -> None:
        self._config = config
        self._lib: ctypes.CDLL | None = None
        self._handle = 0
        self._back_buffer: bytearray | None = None

    async def start(self) -> None:
        if self._lib is not None or self._handle:
            raise RuntimeError("SSD1351 display already started")
        if self._config.native_abi_version != DISPLAY_ABI_VERSION:
            raise DisplayAbiError("selected native display ABI version is unsupported")
        self._verify_artifact()
        self._open()
        self._back_buffer = bytearray(self._config.frame_buffer_bytes)

    async def stop(self) -> None:
        try:
            self._close()
        finally:
            self._back_buffer = None

    def clear(self) -> None:
        self._require_buffer("clear")[:] = b"\x00" * self._config.frame_buffer_bytes

    def write_pixels(self, buf: bytes) -> None:
        if type(buf) is not bytes:
            raise TypeError("write_pixels() requires bytes")
        buffer = self._require_buffer("write_pixels")
        if len(buf) != self._config.frame_buffer_bytes:
            raise ValueError(
                f"expected {self._config.frame_buffer_bytes} bytes, got {len(buf)}"
            )
        buffer[:] = buf

    def show(self) -> None:
        buffer = self._require_buffer("show")
        assert self._lib is not None
        raw = (ctypes.c_uint8 * len(buffer)).from_buffer_copy(buffer)
        status = int(
            self._lib.display_present_rgb565(
                self._handle,
                ctypes.cast(raw, ctypes.POINTER(ctypes.c_uint8)),
                len(buffer),
            )
        )
        self._raise_status("display_present_rgb565", status)

    def size(self) -> tuple[int, int]:
        return (self._config.width, self._config.height)

    def _verify_artifact(self) -> None:
        path = self._config.native_library_path
        digest = self._config.native_library_sha256
        if path is None or digest is None or not path.is_file():
            raise DisplayNativeError("selected native display artifact is unavailable")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise DisplayAbiError("selected native display artifact checksum mismatch")

    def _open(self) -> None:
        assert self._config.native_library_path is not None
        try:
            library = ctypes.CDLL(str(self._config.native_library_path))
        except OSError as exc:
            raise DisplayNativeError("unable to load selected native display artifact") from exc
        self._lib = library
        try:
            self._setup_signatures()
            if int(library.display_abi_version()) != DISPLAY_ABI_VERSION:
                raise DisplayAbiError("native display ABI version mismatch")
            native_config = _build_c_config(self._config)
            handle = ctypes.c_int32(0)
            status = int(library.display_open(ctypes.byref(native_config), ctypes.byref(handle)))
            self._raise_status("display_open", status)
            if handle.value == 0:
                raise DisplayNativeError("display_open returned an invalid handle")
            self._handle = handle.value
            self._verify_info()
        except Exception:
            self._close_after_failed_start()
            raise

    def _verify_info(self) -> None:
        assert self._lib is not None
        info = _CDisplayInfo()
        status = int(self._lib.display_get_info(self._handle, ctypes.byref(info)))
        self._raise_status("display_get_info", status)
        if (
            info.abi_version != DISPLAY_ABI_VERSION
            or info.struct_size != ctypes.sizeof(_CDisplayInfo)
            or info.width != self._config.width
            or info.height != self._config.height
            or info.pixel_format != DISPLAY_PIXEL_FORMAT_RGB565
            or info.byte_order != DISPLAY_BYTE_ORDER_MSB_FIRST
            or info.buffer_bytes != self._config.frame_buffer_bytes
        ):
            raise DisplayAbiError("native display info does not match selected profile")

    def _close_after_failed_start(self) -> None:
        if self._lib is not None and self._handle:
            try:
                self._lib.display_close(self._handle)
            except Exception:
                pass
        self._handle = 0
        self._lib = None

    def _close(self) -> None:
        library, handle = self._lib, self._handle
        self._handle = 0
        self._lib = None
        if library is None or not handle:
            return
        self._raise_status("display_close", int(library.display_close(handle)))

    def _require_buffer(self, operation: str) -> bytearray:
        if self._back_buffer is None or self._lib is None or not self._handle:
            raise RuntimeError(f"{operation} called before start()")
        return self._back_buffer

    def _setup_signatures(self) -> None:
        assert self._lib is not None
        self._lib.display_abi_version.restype = ctypes.c_uint32
        self._lib.display_abi_version.argtypes = []
        self._lib.display_open.restype = ctypes.c_int32
        self._lib.display_open.argtypes = [ctypes.POINTER(_CDisplayConfig), ctypes.POINTER(ctypes.c_int32)]
        self._lib.display_get_info.restype = ctypes.c_int32
        self._lib.display_get_info.argtypes = [ctypes.c_int32, ctypes.POINTER(_CDisplayInfo)]
        self._lib.display_present_rgb565.restype = ctypes.c_int32
        self._lib.display_present_rgb565.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32]
        self._lib.display_close.restype = ctypes.c_int32
        self._lib.display_close.argtypes = [ctypes.c_int32]

    @staticmethod
    def _raise_status(operation: str, status: int) -> None:
        if status == DISPLAY_OK:
            return
        message = f"{operation} failed with native status {status}"
        if status == DISPLAY_E_ABI_MISMATCH:
            raise DisplayAbiError(message)
        if status in {DISPLAY_E_INVALID_ARGUMENT, DISPLAY_E_BAD_CONFIG, DISPLAY_E_BUFFER_SIZE}:
            raise ValueError(message)
        if status in {DISPLAY_E_ALREADY_OPEN, DISPLAY_E_NOT_OPEN, DISPLAY_E_INVALID_HANDLE, DISPLAY_E_WRONG_THREAD}:
            raise RuntimeError(message)
        raise DisplayNativeError(message)


__all__ = ["DisplayAbiError", "DisplayDriver", "DisplayNativeError"]
