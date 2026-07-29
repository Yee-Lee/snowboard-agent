"""HAL (Hardware Abstraction Layer) for display devices."""

from .protocol import DisplayDevice, DisplayInfo, Rgb565Frame, Rect
from .profiles import (
    PinConfig,
    SpiConfig,
    GpiochipConfig,
    DisplayPinConfig,
    PanelProfile,
    get_profile,
    resolve_pin_config,
    PROFILES,
)
from .factory import create_device
from .mock import MockDisplayDevice

__all__ = [
    # Protocol / types
    "DisplayDevice",
    "DisplayInfo",
    "Rgb565Frame",
    "Rect",
    # Pin config
    "PinConfig",
    "SpiConfig",
    "GpiochipConfig",
    "DisplayPinConfig",
    # Profiles
    "PanelProfile",
    "PROFILES",
    "get_profile",
    "resolve_pin_config",
    # Factory
    "create_device",
    # Backends
    "MockDisplayDevice",
]
