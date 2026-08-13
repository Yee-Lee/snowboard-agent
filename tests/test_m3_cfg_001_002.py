"""M3 strict config tests; Audio CFG-002 stays blocked by P4 selection."""

from __future__ import annotations

import hashlib
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
    dc_bcm: 24
    reset_bcm: 25
{override}
"""


def test_m3_cfg_001(tmp_path: Path) -> None:
    artifact = tmp_path / "libdisplay.so"
    artifact.write_bytes(b"fixture artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    path = tmp_path / "valid.yaml"
    path.write_text(_ssd_yaml(artifact, digest))
    config = load_config(local_path=path, environ={})
    assert config.core.display.driver == "ssd1351"
    assert config.core.display.frame_buffer_bytes == 32768
    assert config.core.display.native_library_sha256 == digest

    invalid = {
        "checksum": _ssd_yaml(artifact, "0" * 64),
        "abi": _ssd_yaml(artifact, digest).replace("native_abi_version: 1", "native_abi_version: 2"),
        "speed": _ssd_yaml(artifact, digest).replace("spi_speed_hz: 4000000", "spi_speed_hz: 8000000"),
        "rotation": _ssd_yaml(artifact, digest, "    rotation: 90"),
        "mock-real": "core:\n  display:\n    driver: mock\n    spi_device: /dev/spidev0.0\n",
    }
    for name, yaml_text in invalid.items():
        candidate = tmp_path / f"{name}.yaml"
        candidate.write_text(yaml_text)
        with pytest.raises(ConfigError):
            load_config(local_path=candidate, environ={})

    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(_ssd_yaml(artifact, digest, "    extra_native_knob: 1"))
    with pytest.raises(UnknownConfigKey, match="extra_native_knob"):
        load_config(local_path=unknown, environ={})

    generic = Path("config.example.yaml")
    generic_config = load_config(local_path=generic, environ={})
    assert generic_config.core.display.driver == "mock"
    assert generic_config.core.display.native_library_path is None
    assert generic_config.core.display.dc_bcm is None

    blocked = tmp_path / "audio.yaml"
    blocked.write_text("core:\n  audio:\n    driver: alsa\n")
    with pytest.raises(ConfigValueError, match="P4 final selection ACK"):
        load_config(local_path=blocked, environ={})
