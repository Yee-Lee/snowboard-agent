"""M3 strict display and P4-selected Audio Option A config tests."""

from __future__ import annotations

import ctypes
import hashlib
import sys
from pathlib import Path

import pytest

from sbd.core.config import load_config
from sbd.core.config.validate import ConfigError, ConfigValueError, UnknownConfigKey


def _ssd_yaml(artifact: Path, digest: str, override: str = "") -> str:
    return f"""
core:
  display:
    driver: ssd1351
    native_library_path: {artifact}
    native_library_sha256: {digest}
    native_abi_version: 1
    spi_device: /dev/spidev0.0
    spi_speed_hz: 4000000
    spi_mode: 0
    spi_chip_select: 0
    gpio_chip_index: 0
    dc_bcm: 24
    reset_bcm: 25
{override}
"""


def _alsa_yaml(override: str = "") -> str:
    return f"""
core:
  audio:
    driver: alsa
    input:
      device: hw:0,0
      native_format: {{sample_rate: 48000, channels: 2, sample_format: s32_le}}
      stream_format: {{sample_rate: 16000, channels: 1, sample_format: s16_le}}
      frame_duration_ms: 20
      channel_index: 0
      valid_bits: 24
      valid_bits_alignment: msb
      resampler: samplerate.sinc_best
    output:
      device: hw:0,0
      native_format: {{sample_rate: 48000, channels: 2, sample_format: s32_le}}
      stream_format: {{sample_rate: 48000, channels: 2, sample_format: s32_le}}
{override}
"""


def test_m3_cfg_001(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "libdisplay.so"
    artifact.write_bytes(b"fixture artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    path = tmp_path / "valid.yaml"
    path.write_text(_ssd_yaml(artifact, digest))
    config = load_config(local_path=path, environ={})
    assert config.core.display.driver == "ssd1351"
    assert config.core.display.frame_buffer_bytes == 32768
    assert config.core.display.native_library_sha256 == digest
    assert config.core.display.gpio_chip_index == 0

    invalid = {
        "checksum": _ssd_yaml(artifact, "0" * 64),
        "abi": _ssd_yaml(artifact, digest).replace("native_abi_version: 1", "native_abi_version: 2"),
        "speed": _ssd_yaml(artifact, digest).replace("spi_speed_hz: 4000000", "spi_speed_hz: 8000000"),
        "rotation": _ssd_yaml(artifact, digest, "    rotation: 90"),
        "mock-real": "core:\n  display:\n    driver: mock\n    spi_device: /dev/spidev0.0\n",
        "mock-gpio-chip": "core:\n  display:\n    driver: mock\n    gpio_chip_index: 0\n",
    }
    for name, yaml_text in invalid.items():
        candidate = tmp_path / f"{name}.yaml"
        candidate.write_text(yaml_text)
        with pytest.raises(ConfigError):
            load_config(local_path=candidate, environ={})

    def unexpected_cdll(*args, **kwargs):
        pytest.fail(f"invalid config reached ctypes.CDLL: {args!r} {kwargs!r}")

    monkeypatch.setattr(ctypes, "CDLL", unexpected_cdll)
    gpio_invalid = {
        "gpio-chip-missing": _ssd_yaml(artifact, digest).replace("    gpio_chip_index: 0\n", ""),
        "gpio-chip-negative": _ssd_yaml(artifact, digest).replace("gpio_chip_index: 0", "gpio_chip_index: -1"),
        "gpio-chip-overflow": _ssd_yaml(artifact, digest).replace("gpio_chip_index: 0", "gpio_chip_index: 2147483648"),
    }
    for name, yaml_text in gpio_invalid.items():
        candidate = tmp_path / f"{name}.yaml"
        candidate.write_text(yaml_text)
        with pytest.raises(ConfigValueError, match=r"core\.display\.gpio_chip_index"):
            load_config(local_path=candidate, environ={})

    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(_ssd_yaml(artifact, digest, "    extra_native_knob: 1"))
    with pytest.raises(UnknownConfigKey, match="extra_native_knob"):
        load_config(local_path=unknown, environ={})

    generic = Path("config.example.yaml")
    generic_config = load_config(local_path=generic, environ={})
    assert generic_config.core.display.driver == "mock"
    assert generic_config.core.display.native_library_path is None
    assert generic_config.core.display.gpio_chip_index is None
    assert generic_config.core.display.dc_bcm is None



def test_m3_cfg_002(tmp_path: Path) -> None:
    valid = tmp_path / "alsa.yaml"
    valid.write_text(_alsa_yaml())
    config = load_config(local_path=valid, environ={})
    assert config.core.audio.input.resampler == "samplerate.sinc_best"
    assert config.core.audio.output.stream_format.sample_rate == 48_000

    modules_before = set(sys.modules)
    mutations = {
        "plughw": _alsa_yaml().replace("hw:0,0", "plughw:0,0", 1),
        "native": _alsa_yaml().replace("sample_rate: 48000, channels: 2, sample_format: s32_le", "sample_rate: 16000, channels: 1, sample_format: s16_le", 1),
        "channel": _alsa_yaml().replace("channel_index: 0", "channel_index: 2"),
        "valid-bits": _alsa_yaml().replace("valid_bits: 24", "valid_bits: 16"),
        "alignment": _alsa_yaml().replace("valid_bits_alignment: msb", "valid_bits_alignment: lsb"),
        "resampler": _alsa_yaml().replace("samplerate.sinc_best", "drop-every-third"),
        "output": _alsa_yaml().replace("stream_format: {sample_rate: 48000, channels: 2, sample_format: s32_le}", "stream_format: {sample_rate: 44100, channels: 2, sample_format: s32_le}"),
        "missing": _alsa_yaml().replace("      resampler: samplerate.sinc_best\n", ""),
    }
    for name, payload in mutations.items():
        candidate = tmp_path / f"{name}.yaml"
        candidate.write_text(payload)
        with pytest.raises(ConfigValueError, match=r"core\.audio"):
            load_config(local_path=candidate, environ={})
    assert not {"alsaaudio", "samplerate"}.intersection(
        set(sys.modules).difference(modules_before)
    )
