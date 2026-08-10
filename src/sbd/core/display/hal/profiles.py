"""
HAL display device profiles.

Each profile describes the physical panel characteristics, the
rendering/scaling strategy, AND the default GPIO/SPI pin mapping.

The waveshare_lcd_2in_rgb_128 "virtual driver" lives here as a profile
rather than as a separate native driver.

Pin 設定可在三個層級覆寫（優先順序由低到高）：
  1. Profile 內建預設值 (下方 default_pin_config)
  2. 環境變數 (DISPLAY_PIN_CS, DISPLAY_PIN_DC, …)
  3. 呼叫端直接傳入 PinConfig dataclass
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Python-side pin/SPI config (mirrors pin_config.h)
# ---------------------------------------------------------------------------

@dataclass
class SpiConfig:
    """SPI bus configuration."""
    bus: int = 0           # SPI bus index
    chip: int = 0          # SPI CE (chip enable) index
    speed_hz: int = 60_000_000  # 60 MHz
    mode: int = 0


@dataclass
class GpiochipConfig:
    """lgpio gpiochip selection.  chip_index=-1 → auto-detect."""
    chip_index: int = -1   # -1 = auto (RPi5 → 4, others → 0)


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
# Environment variable override helper
# ---------------------------------------------------------------------------

def _env_int(key: str, default: int) -> int:
    """Read an integer from an env var, fall back to *default*."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def load_pin_config_from_env(base: PinConfig) -> PinConfig:
    """
    Override *base* PinConfig with values from environment variables.

    Variables (all optional):
        DISPLAY_PIN_CS      GPIO BCM number for Chip Select
        DISPLAY_PIN_DC      GPIO BCM number for Data/Command
        DISPLAY_PIN_RST     GPIO BCM number for Reset
        DISPLAY_PIN_BL      GPIO BCM number for Backlight (-1 = none)
        DISPLAY_SPI_BUS     SPI bus index (default 0)
        DISPLAY_SPI_CHIP    SPI CE index  (default 0)
        DISPLAY_SPI_SPEED   SPI speed in Hz (default 60000000)
        DISPLAY_GPIO_CHIP   gpiochip index (-1 = auto)
    """
    return PinConfig(
        cs=_env_int("DISPLAY_PIN_CS",  base.cs),
        dc=_env_int("DISPLAY_PIN_DC",  base.dc),
        rst=_env_int("DISPLAY_PIN_RST", base.rst),
        bl=_env_int("DISPLAY_PIN_BL",  base.bl),
    )


def load_spi_config_from_env(base: SpiConfig) -> SpiConfig:
    return SpiConfig(
        bus=_env_int("DISPLAY_SPI_BUS",   base.bus),
        chip=_env_int("DISPLAY_SPI_CHIP", base.chip),
        speed_hz=_env_int("DISPLAY_SPI_SPEED", base.speed_hz),
        mode=base.mode,
    )


def load_gpio_chip_from_env(base: GpiochipConfig) -> GpiochipConfig:
    return GpiochipConfig(
        chip_index=_env_int("DISPLAY_GPIO_CHIP", base.chip_index),
    )


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

    # Native C driver folder name in native/
    native_driver: str = ""

    # Frames-per-second ceiling the panel can handle
    max_fps: int = 60
    
    # Preferred SPI speed for this panel
    default_spi_speed: int = 60_000_000


# ------------------------------------------------------------------
# Predefined profiles
# ------------------------------------------------------------------
#
# Default pin mapping (matches README.md接線表):
#   CS  → GPIO 8   (SPI0 CE0, Pin 24)
#   DC  → GPIO 24  (Pin 18)
#   RST → GPIO 25  (Pin 22)
#   BL  → GPIO 18  (Pin 12, LCD only)
#
# These are the connector pin numbers for the Raspberry Pi 5 setup
# described in the project README.
#
# ⚠️  If your wiring differs, override via environment variables or
#     pass a custom PinConfig to create_device().

_DEFAULT_OLED_PINS = PinConfig(cs=8, dc=24, rst=25, bl=-1)
_DEFAULT_LCD_PINS  = PinConfig(cs=8, dc=24, rst=25, bl=18)

PROFILES: dict[str, PanelProfile] = {
    # 1.5-inch OLED (SSD1351), 128×128
    "waveshare_oled_1in5_rgb": PanelProfile(
        name="waveshare_oled_1in5_rgb",
        native_width=128,
        native_height=128,
        logical_width=128,
        logical_height=128,
        default_pins=_DEFAULT_OLED_PINS,
        native_driver="waveshare_ssd1351",
        max_fps=120,
        default_spi_speed=20_000_000,
        default_spi_mode=3,
    ),
    # 2-inch LCD (ST7789), 320×240, full native resolution
    "waveshare_lcd_2in_rgb": PanelProfile(
        name="waveshare_lcd_2in_rgb",
        native_width=320,
        native_height=240,
        logical_width=320,
        logical_height=240,
        default_pins=_DEFAULT_LCD_PINS,
        native_driver="waveshare_st7789",
        max_fps=60,
    ),
    # 2-inch LCD used as a 128×128 canvas (scaled + centred layout)
    "waveshare_lcd_2in_rgb_128": PanelProfile(
        name="waveshare_lcd_2in_rgb_128",
        native_width=320,
        native_height=240,
        logical_width=128,
        logical_height=128,
        default_pins=_DEFAULT_LCD_PINS,
        native_driver="waveshare_st7789",
        max_fps=60,
    ),
    # Mock / headless (CI / PC)
    "mock": PanelProfile(
        name="mock",
        native_width=128,
        native_height=128,
        logical_width=128,
        logical_height=128,
        default_pins=PinConfig(cs=-1, dc=-1, rst=-1, bl=-1),
        native_driver="mock",
        max_fps=120,
    ),
}


def get_profile(name: str) -> PanelProfile:
    if name not in PROFILES:
        raise KeyError(
            f"Unknown panel profile '{name}'. Available: {list(PROFILES)}"
        )
    return PROFILES[name]


def resolve_pin_config(
    profile: PanelProfile,
    override: Optional[PinConfig] = None,
    *,
    apply_env: bool = True,
) -> DisplayPinConfig:
    """
    Build a final DisplayPinConfig for *profile*.

    Priority (high → low):
        1. *override* (caller-supplied)
        2. Environment variables (DISPLAY_PIN_CS, …)
        3. *profile.default_pins*
    """
    base_pins = profile.default_pins
    base_spi  = SpiConfig(speed_hz=profile.default_spi_speed)
    base_gpio = GpiochipConfig()

    if apply_env:
        base_pins = load_pin_config_from_env(base_pins)
        base_spi  = load_spi_config_from_env(base_spi)
        base_gpio = load_gpio_chip_from_env(base_gpio)

    if override is not None:
        base_pins = override

    return DisplayPinConfig(
        pins=base_pins,
        spi=base_spi,
        gpio_chip=base_gpio,
    )
