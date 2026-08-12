"""Host-side ABI behaviour smoke using the test lgpio stub library."""

from __future__ import annotations

import ctypes
import sys
import threading

from sbd.core.display.hal.ctypes_backend import (
    DISPLAY_ABI_VERSION,
    DISPLAY_E_BAD_CONFIG,
    DISPLAY_E_BUFFER_SIZE,
    DISPLAY_E_NOT_OPEN,
    DISPLAY_E_WRONG_THREAD,
    DISPLAY_OK,
    _CDisplayConfig,
    _build_c_config,
)
from sbd.core.display.hal.profiles import (
    DisplayPinConfig,
    GpiochipConfig,
    PinConfig,
    SpiConfig,
)


def configure(lib: ctypes.CDLL) -> None:
    lib.display_abi_version.restype = ctypes.c_uint32
    lib.display_open.restype = ctypes.c_int32
    lib.display_open.argtypes = [
        ctypes.POINTER(_CDisplayConfig),
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.display_present_rgb565.restype = ctypes.c_int32
    lib.display_present_rgb565.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_uint32,
    ]
    lib.display_close.restype = ctypes.c_int32
    lib.display_close.argtypes = [ctypes.c_int32]


def config(speed_hz: int = 4_000_000) -> _CDisplayConfig:
    return _build_c_config(
        DisplayPinConfig(
            pins=PinConfig(rst=27, dc=25, cs=-1, bl=-1),
            spi=SpiConfig(bus=0, chip=0, speed_hz=speed_hz, mode=0),
            gpio_chip=GpiochipConfig(chip_index=4),
        ),
        128,
        128,
    )


def main(path: str) -> int:
    lib = ctypes.CDLL(path)
    configure(lib)
    assert lib.display_abi_version() == DISPLAY_ABI_VERSION

    invalid = config(60_000_000)
    handle = ctypes.c_int32(0)
    assert lib.display_open(ctypes.byref(invalid), ctypes.byref(handle)) == DISPLAY_E_BAD_CONFIG
    assert handle.value == 0

    valid = config()
    assert lib.display_open(ctypes.byref(valid), ctypes.byref(handle)) == DISPLAY_OK
    assert handle.value != 0

    frame = (ctypes.c_uint8 * 32768)()
    assert lib.display_present_rgb565(handle.value, frame, 32766) == DISPLAY_E_BUFFER_SIZE

    wrong_thread_status: list[int] = []
    worker = threading.Thread(
        target=lambda: wrong_thread_status.append(
            lib.display_present_rgb565(handle.value, frame, 32768)
        )
    )
    worker.start()
    worker.join()
    assert wrong_thread_status == [DISPLAY_E_WRONG_THREAD]

    assert lib.display_present_rgb565(handle.value, frame, 32768) == DISPLAY_OK
    assert lib.display_close(handle.value) == DISPLAY_OK
    assert lib.display_close(handle.value) == DISPLAY_E_NOT_OPEN
    print("native ABI behaviour smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
