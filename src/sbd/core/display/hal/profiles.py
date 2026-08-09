"""
HAL display device profiles.

Each profile describes physical panel characteristics and logical layout.
Real fixture GPIO/SPI values are loaded from a recorded JSON config.

The waveshare_lcd_2in_rgb_128 "virtual driver" lives here as a profile
rather than as a separate native driver.

Profile pin values are descriptive only and are never deployment defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Python-side pin/SPI config (mirrors pin_config.h)
# ---------------------------------------------------------------------------

@dataclass
class SpiConfig:
    """SPI bus configuration."""
    bus: int = 0           # SPI bus index
    chip: int = 0          # SPI CE (chip enable) index
    speed_hz: int = 4_000_000
    mode: int = 0


@dataclass
class GpiochipConfig:
    """Resolved lgpio gpiochip selection."""
    chip_index: int = -1


@dataclass
class PinConfig:
    """
    GPIO pin numbers (BCM / GPIO numbering).

    -1 means "not present / not used".

    Refer to README.md for the physical pin ↔ GPIO mapping table.
    """
    rst: int         # Reset
    dc: int          # Data/Command
    cs: int          # SPI Chip Select (CE)
    bl: int = -1     # Backlight (-1 = no backlight, e.g. OLED)


@dataclass
class DisplayPinConfig:
    """Combined pin + SPI + gpiochip config (passed to display_open)."""
    pins: PinConfig
    spi: SpiConfig = field(default_factory=SpiConfig)
    gpio_chip: GpiochipConfig = field(default_factory=GpiochipConfig)


# ---------------------------------------------------------------------------
# Panel profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PanelProfile:
    """Static description of one physical panel + its preferred layout."""

    # Hardware / native resolution
    native_width: int
    native_height: int

    # Logical canvas size presented to the renderer
    logical_width: int
    logical_height: int

    # Human-readable identifier
    name: str

    # Default pin mapping for this panel
    default_pins: PinConfig = field(compare=False)

    # Frames-per-second ceiling the panel can handle
    max_fps: Optional[int] = None


# ------------------------------------------------------------------
# Predefined profiles
# ------------------------------------------------------------------
#
# Default pin mapping (matches README.md接線表):
#   CS  → GPIO 8   (SPI0 CE0, Pin 24)
#   DC  → GPIO 25  (Pin 22)
#   RST → GPIO 27  (Pin 13)
#   BL  → GPIO 18  (Pin 12, LCD only)
#
# These are the connector pin numbers for the Raspberry Pi 5 setup
# described in the project README.
#
# Real runs must load and record a local JSON config even when it matches these
# descriptive values.

_DEFAULT_OLED_PINS = PinConfig(cs=8, dc=25, rst=27, bl=-1)
_DEFAULT_LCD_PINS  = PinConfig(cs=8, dc=25, rst=27, bl=18)

PROFILES: dict[str, PanelProfile] = {
    # 1.5-inch OLED (SSD1351), 128×128
    "waveshare_oled_1in5_rgb": PanelProfile(
        name="waveshare_oled_1in5_rgb",
        native_width=128,
        native_height=128,
        logical_width=128,
        logical_height=128,
        default_pins=_DEFAULT_OLED_PINS,
        max_fps=None,
    ),
    # 2-inch LCD (ST7789), 320×240, full native resolution
    "waveshare_lcd_2in_rgb": PanelProfile(
        name="waveshare_lcd_2in_rgb",
        native_width=320,
        native_height=240,
        logical_width=320,
        logical_height=240,
        default_pins=_DEFAULT_LCD_PINS,
        max_fps=None,
    ),
    # 2-inch LCD used as a 128×128 canvas (scaled + centred layout)
    "waveshare_lcd_2in_rgb_128": PanelProfile(
        name="waveshare_lcd_2in_rgb_128",
        native_width=320,
        native_height=240,
        logical_width=128,
        logical_height=128,
        default_pins=_DEFAULT_LCD_PINS,
        max_fps=None,
    ),
    # Mock / headless (CI / PC)
    "mock": PanelProfile(
        name="mock",
        native_width=128,
        native_height=128,
        logical_width=128,
        logical_height=128,
        default_pins=PinConfig(cs=-1, dc=-1, rst=-1, bl=-1),
        max_fps=120,
    ),
}


def get_profile(name: str) -> PanelProfile:
    if name not in PROFILES:
        raise KeyError(
            f"Unknown panel profile '{name}'. Available: {list(PROFILES)}"
        )
    return PROFILES[name]


def load_display_config(path: str | Path) -> DisplayPinConfig:
    """Load a recorded local fixture config; deployment values are not defaulted."""
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported display config schema_version")
    spi = data["spi"]
    gpio = data["gpio"]
    frame = data["frame"]
    panel = data["panel"]
    power = data["power"]
    if panel.get("controller") != "SSD1351" or panel.get("interface") != "4-wire SPI":
        raise ValueError("reference adapter config must identify SSD1351 4-wire SPI")
    if power.get("vcc_volts") != 3.3 or power.get("logic_volts") != 3.3:
        raise ValueError("reference fixture requires 3.3 V supply and logic")
    if gpio.get("numbering") != "BCM":
        raise ValueError("display GPIO numbering must be BCM")
    if not isinstance(gpio.get("chip"), int):
        raise ValueError("gpio.chip must be resolved to an integer for a real run")
    if frame.get("pixel_format") != "RGB565" or frame.get("byte_order") != "MSB_FIRST":
        raise ValueError("only RGB565_MSB_FIRST is supported")
    if frame.get("rotation_degrees") != 0:
        raise ValueError("reference adapter currently supports rotation_degrees=0 only")
    if (
        frame.get("physical_width") != 128
        or frame.get("physical_height") != 128
        or frame.get("logical_width") != 128
        or frame.get("logical_height") != 128
        or frame.get("buffer_bytes") != 32768
    ):
        raise ValueError("reference SSD1351 fixture requires a 128x128 full frame")
    bus = int(spi["bus"])
    chip_select = int(spi["chip_select"])
    if spi.get("device") != f"/dev/spidev{bus}.{chip_select}":
        raise ValueError("spi.device must match spi.bus and spi.chip_select")
    if chip_select not in {0, 1}:
        raise ValueError("only CE0/CE1 chip select values are supported")
    return DisplayPinConfig(
        pins=PinConfig(
            cs={0: 8, 1: 7}[chip_select],
            dc=int(gpio["dc"]),
            rst=int(gpio["rst"]),
            bl=-1 if gpio.get("bl") is None else int(gpio["bl"]),
        ),
        spi=SpiConfig(
            bus=bus,
            chip=chip_select,
            speed_hz=int(spi["requested_speed_hz"]),
            mode=int(spi["mode"]),
        ),
        gpio_chip=GpiochipConfig(chip_index=int(gpio["chip"])),
    )
