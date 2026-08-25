import pytest
import os
from pathlib import Path
from sbd.core.config import (
    load_config, SecretValue, UnknownConfigKey, ConfigParseError,
    ConfigTypeError, ConfigValueError, AppConfig
)

# M1-CFG-005: example file passes full validation
def test_m1_cfg_005_example_file_passes():
    example_path = Path(__file__).parent.parent / "config.example.yaml"
    config = load_config(local_path=example_path)
    assert isinstance(config, AppConfig)
    assert config.perception.listen.adapter.driver == "mock"

# M1-CFG-001: defaults complete, leaf override only, precedence chain, immutable result
def test_m1_cfg_001_precedence_and_immutability(tmp_path):
    # default
    config = load_config(local_path=Path("nonexistent.yaml"), dotenv_path=Path("nonexistent.env"), environ={})
    assert config.log.level == "INFO"

    # leaf override
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("log:\n  level: WARNING\n")
    config2 = load_config(local_path=yaml_file, dotenv_path=Path("nonexistent.env"), environ={})
    assert config2.log.level == "WARNING"
    assert config2.wake.ack_seconds == 0.3  # kept default

    # dotenv override
    env_file = tmp_path / ".env"
    env_file.write_text("SBD_LOG_LEVEL=ERROR\n")
    config3 = load_config(local_path=yaml_file, dotenv_path=env_file, environ={})
    assert config3.log.level == "ERROR"

    # environ override
    config4 = load_config(local_path=yaml_file, dotenv_path=env_file, environ={"SBD_LOG_LEVEL": "CRITICAL"})
    assert config4.log.level == "CRITICAL"

    # immutable mappings
    with pytest.raises(TypeError):
        config4.core.gpio.pins["test"] = "test"

# M1-CFG-004: SecretValue redaction, malformed .env, unknown SBD_ rejected
def test_m1_cfg_004_secret_and_env(tmp_path):
    sv = SecretValue("mysecret")
    assert str(sv) == "***"
    assert repr(sv) == "SecretValue(***)"
    assert sv.reveal() == "mysecret"

    env_file = tmp_path / ".env"
    sentinel = "DOTENV_SECRET_MUST_NOT_LEAK"
    env_file.write_text(f"MALFORMED_{sentinel}\n")
    with pytest.raises(ConfigParseError, match="line 1") as error:
        load_config(dotenv_path=env_file, environ={})
    assert sentinel not in str(error.value)

    env_file.write_text("SBD_UNKNOWN_VAR=1\n")
    with pytest.raises(UnknownConfigKey):
        load_config(dotenv_path=env_file, environ={})

    # unrelated env ignored
    config = load_config(environ={"OTHER_VAR": "value"})
    assert config

# M1-CFG-002: validation table
def test_m1_cfg_002_validation(tmp_path):
    def load_with(yaml_str):
        p = tmp_path / "test.yaml"
        p.write_text(yaml_str)
        return load_config(local_path=p, environ={})

    with pytest.raises(UnknownConfigKey):
        load_with("unknown_key: true")

    with pytest.raises(ConfigTypeError):
        load_with("log: 'string_instead_of_mapping'")

    with pytest.raises(ConfigTypeError):
        load_with("wake:\n  ack_seconds: null")

    with pytest.raises(ConfigValueError, match="contradiction"):
        load_with("perception:\n  listen:\n    required: true\n    enabled: false")

    with pytest.raises(ConfigValueError, match="timeout"):
        load_with("wake:\n  ack_seconds: -1")

    with pytest.raises(ConfigValueError, match="cancel timeout"):
        load_with("cancel:\n  abort_timeout_seconds:\n    by_kind:\n      'unknown.op': 1.0")

    with pytest.raises(ConfigValueError, match="resource timeout"):
        load_with("resource:\n  startup_timeout_seconds:\n    by_kind:\n      'unknown.resource': 1.0")

    with pytest.raises(ConfigTypeError, match="must be one of"):
        load_with("perception:\n  listen:\n    adapter:\n      driver: whisper\n      model_path: null")

    with pytest.raises(ConfigValueError, match="exact integer"):
        # 16000 * 20 / 1000 * 1.5 = 480 bytes, let's make it float
        load_with(
            "core:\n  audio:\n    input:\n      frame_duration_ms: 15\n"
            "      stream_format:\n        sample_rate: 16001\n"
        )

    with pytest.raises(ConfigValueError, match="rotate_backup_count"):
        load_with("log:\n  rotate_max_bytes: 100\n  rotate_backup_count: 0")

    with pytest.raises(ConfigValueError, match="Duplicate physical GPIO pin"):
        load_with("core:\n  gpio:\n    pins:\n      p1:\n        pin: 1\n      p2:\n        pin: 1")

    with pytest.raises(ConfigTypeError, match="must be one of"):
        load_with(
            "core:\n  audio:\n    output:\n      stream_format:\n"
            "        sample_rate: 48000\n        channels: 2\n"
            "        sample_format: s32_le\n"
            "action:\n  tts:\n    driver: piper"
        )



@pytest.mark.parametrize(
    ("yaml_text", "path"),
    [
        ("wake:\n  ack_seconds: true", "wake.ack_seconds"),
        (
            "core:\n  audio:\n    input:\n      stream_format:\n        sample_rate: true",
            "audio.input.stream_format.sample_rate",
        ),
        ("log:\n  level: VERBOSE", "log.level"),
        ("perception:\n  default_perceptions: [listen, 7]", "default_perceptions\\[1\\]"),
        ("resource:\n  startup_timeout_seconds:\n    default: true", "startup_timeout_seconds.default"),
        (
            "resource:\n  startup_timeout_seconds:\n    by_kind:\n      core.audio.input: false",
            "core.audio.input",
        ),
    ],
)
def test_m1_cfg_002_rejects_bool_literal_and_nested_element_types(
    tmp_path: Path, yaml_text: str, path: str
) -> None:
    config_path = tmp_path / "typed.yaml"
    config_path.write_text(yaml_text)
    with pytest.raises(ConfigTypeError, match=path):
        load_config(local_path=config_path, environ={})


def test_m1_cfg_001_relative_paths_resolve_from_config_directory(tmp_path: Path) -> None:
    config_dir = tmp_path / "nested"
    config_dir.mkdir()
    config_path = config_dir / "config.yaml"
    config_path.write_text("log:\n  file: logs/sbd.log\n")

    config = load_config(local_path=config_path, dotenv_path=tmp_path / "missing.env", environ={})

    assert config.log.file == (config_dir / "logs/sbd.log").resolve()


@pytest.mark.parametrize(
    ("yaml_text", "path"),
    [
        ("core:\n  display:\n    width: 0", "core.display.width"),
        ("core:\n  display:\n    width: 127", "core.display.width"),
        ("core:\n  camera:\n    height: 0", "core.camera.height"),
        ("core:\n  camera:\n    quality: 101", "core.camera.quality"),
    ],
)
def test_m1_cfg_002_cross_field_and_real_model_validation(
    tmp_path: Path, yaml_text: str, path: str
) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(yaml_text)
    with pytest.raises(ConfigValueError, match=path):
        load_config(local_path=config_path, environ={})
