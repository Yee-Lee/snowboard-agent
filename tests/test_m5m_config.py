"""M5M-CFG-001: MQTT profile, credentials and explicit provider boundary."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from sbd.core.config.loader import load_config
from sbd.core.config.models import SecretValue
from sbd.core.config.validate import ConfigValueError, MissingSecretError, validate_config
from sbd.core.m2_composition import M2Composition
from sbd.core.event_bus import EventBus
from tests.test_m5t_config import m5_config


def _mqtt_config(tmp_path):
    base = m5_config(tmp_path)
    return replace(base,
        adaptors=replace(base.adaptors,
            mqtt=replace(base.adaptors.mqtt,
                policy=replace(base.adaptors.mqtt.policy, enabled=True))),
        perception=replace(base.perception,
            read=replace(base.perception.read, enabled=True)),
        input_sources=replace(base.input_sources,
            external_message=replace(base.input_sources.external_message,
                policy=replace(base.input_sources.external_message.policy, enabled=True))))


def test_m5m_cfg_001_defaults_external_constraints_and_env_only(tmp_path):
    config = _mqtt_config(tmp_path)
    validate_config(config)
    mqtt = config.adaptors.mqtt
    assert (mqtt.provider, mqtt.host, mqtt.port, mqtt.qos, mqtt.tls_enabled) == (
        "local_test", "localhost", 1883, 1, False)
    assert (config.external_message.buffer_max,
            config.external_message.overflow_policy) == (8, "drop_newest")
    ca = tmp_path / "ca.pem"
    ca.write_text("CA")
    external = replace(mqtt, provider="external", host="broker.example",
        tls_enabled=True, ca_path=ca, username="user", password=SecretValue("secret"))
    validate_config(replace(config, adaptors=replace(config.adaptors, mqtt=external)))
    for changed in (
        replace(external, host="localhost"), replace(external, tls_enabled=False, ca_path=None),
        replace(external, ca_path=None), replace(external, username=None),
        replace(external, notification_topic_suffix="other"), replace(external, qos=True),
    ):
        with pytest.raises(ConfigValueError):
            validate_config(replace(config, adaptors=replace(config.adaptors, mqtt=changed)))
    with pytest.raises(MissingSecretError):
        validate_config(replace(config, adaptors=replace(config.adaptors,
            mqtt=replace(external, password=None))))
    with pytest.raises(ConfigValueError):
        validate_config(replace(config, perception=replace(config.perception,
            read=replace(config.perception.read, enabled=False))))
    with pytest.raises(ConfigValueError):
        validate_config(replace(config, input_sources=replace(config.input_sources,
            external_message=replace(config.input_sources.external_message,
                policy=replace(config.input_sources.external_message.policy, enabled=False)))))
    yaml = tmp_path / "config.yaml"
    yaml.write_text("adaptors:\n  mqtt:\n    password: leaked\n")
    with pytest.raises(ConfigValueError, match="environment"):
        load_config(local_path=yaml, dotenv_path=tmp_path / "missing", environ={})
    yaml.write_text("adaptors:\n  mqtt:\n    username: user\n")
    loaded = load_config(local_path=yaml, dotenv_path=tmp_path / "missing",
                         environ={"SBD_MQTT_PASSWORD": "secret"})
    assert loaded.adaptors.mqtt.password.reveal() == "secret"
    assert "secret" not in yaml.read_text()


def test_m5m_cfg_001_composition_binds_real_command_publisher(tmp_path, monkeypatch):
    import sbd.core.m2_composition as module
    from sbd.core.audio.null import NullAudioOutput

    for name, replacement in (
        ("make_audio_input", lambda _cfg: object()),
        ("make_audio_output", lambda _cfg: NullAudioOutput()),
        ("make_display", lambda _cfg: object()),
        ("make_camera", lambda _cfg: object()),
        ("make_gpio", lambda _cfg: object()),
        ("make_tts_adapter", lambda _cfg: object()),
        ("make_asr_adapter", lambda _cfg: SimpleNamespace(_initial_prompt=None)),
        ("make_llm_adapter", lambda _cfg, **_kwargs: SimpleNamespace(control=object())),
    ):
        monkeypatch.setattr(module, name, replacement)

    class CaptureRM:
        def __init__(self):
            self.specs = []
        def register(self, spec):
            self.specs.append(spec)
        def begin_recovery(self, *_args):
            pass
        def wait_recovery(self, *_args):
            pass

    composition = M2Composition(llm_resource_sampler=object())
    rm = CaptureRM()
    composition(rm, EventBus(), _mqtt_config(tmp_path))
    assert composition.tools.contains("mock.send")
    assert type(composition.tools._registered("mock.send").execution_control).__name__ == "MQTTCommandTool"
    assert {spec.key for spec in rm.specs} >= {"adaptor.mqtt", "input.external_message",
                                                "worker.perception.read"}
