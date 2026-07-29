"""
HAL device factory.

Creates the appropriate DisplayDevice based on a profile name and
optional override arguments.  Callers never need to import concrete
backend classes directly.

Pin configuration priority (high → low):
  1. *pin_config* argument (explicit caller override)
  2. Environment variables (DISPLAY_PIN_CS, DISPLAY_PIN_DC, …)
  3. Profile built-in defaults (hal/profiles.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .mock import MockDisplayDevice
from .profiles import (
    PanelProfile,
    PinConfig,
    DisplayPinConfig,
    get_profile,
    resolve_pin_config,
)
from .protocol import DisplayDevice


def create_device(
    profile_name: str,
    *,
    so_path: Optional[str | Path] = None,
    mock: bool = False,
    save_frames_to: Optional[Path] = None,
    pin_config: Optional[PinConfig] = None,
) -> DisplayDevice:
    """
    Instantiate a DisplayDevice for the given *profile_name*.

    Parameters
    ----------
    profile_name:
        One of the keys in ``hal.profiles.PROFILES``, e.g.
        ``"waveshare_oled_1in5_rgb"`` or ``"mock"``.
    so_path:
        Path to ``libdisplay.so``.  Required when ``mock=False`` and the
        profile is not ``"mock"``.  Falls back to the default location
        ``native/<profile_name>/libdisplay.so`` if omitted.
    mock:
        Force-use the mock backend even for a real profile name.
    save_frames_to:
        When using the mock backend, save each frame as a PNG to this
        directory.
    pin_config:
        Optional explicit GPIO pin mapping.  When provided, overrides
        both the profile defaults and environment variables.
        Use ``hal.profiles.PinConfig`` to build one:

            pin_config=PinConfig(cs=8, dc=24, rst=25, bl=-1)

    Example — use env vars to override default pins::

        # Before running:
        #   export DISPLAY_PIN_DC=23
        device = create_device("waveshare_oled_1in5_rgb")

    Example — explicit override::

        device = create_device(
            "waveshare_oled_1in5_rgb",
            pin_config=PinConfig(cs=8, dc=23, rst=25, bl=-1),
        )
    """
    profile = get_profile(profile_name)

    if mock or profile_name == "mock":
        return MockDisplayDevice(
            width=profile.logical_width,
            height=profile.logical_height,
            name=profile.name,
            save_dir=save_frames_to,
        )

    # Resolve the final pin/SPI/gpiochip config
    resolved_cfg: DisplayPinConfig = resolve_pin_config(
        profile, override=pin_config, apply_env=True
    )

    # Resolve libdisplay.so path
    if so_path is None:
        base = (
            Path(__file__).parent.parent
            / "native"
            / profile_name
            / "libdisplay.so"
        )
        so_path = base

    so_path = Path(so_path)
    if not so_path.exists():
        raise FileNotFoundError(
            f"libdisplay.so not found at {so_path}. "
            f"Run 'make' inside native/{profile_name}/ first, or pass mock=True."
        )

    from .ctypes_backend import CtypesDisplayDevice  # lazy import

    scale = (
        profile.logical_width != profile.native_width
        or profile.logical_height != profile.native_height
    )

    return CtypesDisplayDevice(
        so_path=so_path,
        logical_width=profile.logical_width,
        logical_height=profile.logical_height,
        pin_config=resolved_cfg,
        scale_to_native=scale,
        native_width=profile.native_width,
        native_height=profile.native_height,
    )
