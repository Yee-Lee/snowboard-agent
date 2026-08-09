"""
HAL device factory.

Creates the appropriate DisplayDevice based on a profile name. Real hardware
requires an explicit, recorded local JSON config; deployment values never come
from environment variables or source defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .mock import MockDisplayDevice
from .profiles import (
    DisplayPinConfig,
    get_profile,
    load_display_config,
)
from .protocol import DisplayDevice


def create_device(
    profile_name: str,
    *,
    so_path: Optional[str | Path] = None,
    mock: bool = False,
    save_frames_to: Optional[Path] = None,
    config_path: Optional[str | Path] = None,
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
    config_path:
        Recorded local fixture JSON. Required for every real backend.
    """
    profile = get_profile(profile_name)

    if mock or profile_name == "mock":
        return MockDisplayDevice(
            width=profile.logical_width,
            height=profile.logical_height,
            name=profile.name,
            save_dir=save_frames_to,
        )

    if config_path is None:
        raise ValueError(
            "real display requires config_path pointing to a recorded local config"
        )
    if profile_name != "waveshare_oled_1in5_rgb":
        raise ValueError(
            "only the primary SSD1351 fixture has a strict v0.3 config contract"
        )
    resolved_cfg: DisplayPinConfig = load_display_config(config_path)

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
