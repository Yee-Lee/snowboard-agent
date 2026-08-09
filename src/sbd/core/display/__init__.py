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
    config_path: Optional[str] = None,
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
    config_path:
        Path to a recorded local fixture JSON. Required for real hardware.

    Example::

        service = create_service("waveshare_oled_1in5_rgb")
        await service.start()
        client = DisplayClient(service)
        client.set_status("starry_night")

    Example with a recorded fixture::

        from sbd.core.display import create_service
        service = create_service(
            "waveshare_oled_1in5_rgb",
            config_path="poc_display/evidence/DSP-DELIVERY-001/run-001/config.json",
        )
    """
    device = create_device(profile, so_path=so_path, mock=mock, config_path=config_path)
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
