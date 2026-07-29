"""
sbd.core.display — Display sub-system public surface.

External callers should only import from this top-level package:

    from sbd.core.display import DisplayClient, create_service

Everything else (service, rendering, hal, native) is internal.
"""

from __future__ import annotations

from typing import Optional

from .api.client import DisplayClient
from .hal.factory import create_device
from .hal.profiles import PinConfig, SpiConfig, GpiochipConfig, DisplayPinConfig
from .service.service import DisplayService


def create_service(
    profile: str = "mock",
    *,
    target_fps: int = 30,
    so_path: Optional[str] = None,
    mock: bool = False,
    pin_config: Optional["PinConfig"] = None,
) -> DisplayService:
    """
    Convenience factory: create a ready-to-start DisplayService.

    Parameters
    ----------
    profile:
        Panel profile name (see hal/profiles.py).
    target_fps:
        Render loop target frame rate.
    so_path:
        Override path to libdisplay.so.
    mock:
        Force-use MockDisplayDevice (headless).
    pin_config:
        Optional explicit GPIO pin mapping, e.g.::

            PinConfig(cs=8, dc=24, rst=25, bl=-1)

        When None, uses profile defaults + env var overrides.

    Example::

        service = create_service("waveshare_oled_1in5_rgb")
        await service.start()
        client = DisplayClient(service)
        client.set_status("starry_night")

    Example with custom pins::

        from sbd.core.display import create_service, PinConfig
        service = create_service(
            "waveshare_oled_1in5_rgb",
            pin_config=PinConfig(cs=8, dc=23, rst=25),
        )
    """
    device = create_device(profile, so_path=so_path, mock=mock, pin_config=pin_config)
    return DisplayService(device, target_fps=target_fps)


__all__ = [
    "DisplayClient",
    "DisplayService",
    "create_service",
    "create_device",
    # Pin config
    "PinConfig",
    "SpiConfig",
    "GpiochipConfig",
    "DisplayPinConfig",
]
