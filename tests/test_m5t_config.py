"""M5T-CFG-001: profile and capability combination is explicit."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from types import SimpleNamespace

from sbd.cognition.litert_lm.m5_profile import M5ProfileError, load_m5_profile
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import AudioFormatConfig, LLMConfig
from sbd.core.config.validate import ConfigValueError, validate_config
from sbd.core.audio.null import NullAudioOutput
from sbd.core.event_bus import EventBus
from sbd.core.m2_composition import M2Composition
from tests.test_m4a_cfg_001 import _real_configs
from tests.test_m4b_cfg_001 import real_config as m4_config
from sbd.perception.listen.whispercpp import supervisor as asr_supervisor


TEMPLATE = Path(__file__).resolve().parents[1] / "requirements/m5tool/product-profile.json"


def m5_config(tmp_path):
    asr, tts = _real_configs(tmp_path)
    profile = json.loads(TEMPLATE.read_text())
    profile.update(profile_stage="release", prompt_tokens=120,
        min_mem_available_generate_bytes=2048,
        min_mem_available_speak_bytes=1024)
    profile_path = tmp_path / "m5-profile.json"
    profile_path.write_text(json.dumps(profile))
    model = tmp_path / "model"
    model.write_bytes(b"x")
    python = asr.runtime_python
    native_format = AudioFormatConfig(48000, 2, "s32_le")
    audio = replace(DEFAULT_CONFIG.core.audio, driver="alsa",
        input=replace(DEFAULT_CONFIG.core.audio.input, device="hw:1,0",
            native_format=native_format, channel_index=0, valid_bits=24,
            valid_bits_alignment="msb", resampler="samplerate.sinc_best"),
        output=replace(DEFAULT_CONFIG.core.audio.output, device="hw:1,0",
            native_format=native_format))
    return replace(DEFAULT_CONFIG,
        cognition=replace(DEFAULT_CONFIG.cognition, llm=LLMConfig(driver="litert_lm",
            runtime_python=python, model_path=model, product_profile_path=profile_path,
            profile_id="core-m5-tool-001")),
        perception=replace(DEFAULT_CONFIG.perception,
            listen=replace(DEFAULT_CONFIG.perception.listen, adapter=asr),
            read=replace(DEFAULT_CONFIG.perception.read, enabled=False)),
        action=replace(DEFAULT_CONFIG.action,
            tool=replace(DEFAULT_CONFIG.action.tool, enabled=True), tts=tts),
        core=replace(DEFAULT_CONFIG.core, audio=audio),
        input_sources=replace(DEFAULT_CONFIG.input_sources,
            voice_wake=replace(DEFAULT_CONFIG.input_sources.voice_wake,
                policy=replace(DEFAULT_CONFIG.input_sources.voice_wake.policy, enabled=False)),
            external_message=replace(DEFAULT_CONFIG.input_sources.external_message,
                policy=replace(DEFAULT_CONFIG.input_sources.external_message.policy, enabled=False))))


def test_m5_profile_template_is_not_a_release_profile():
    assert load_m5_profile(TEMPLATE, allow_template=True)["profile_stage"] == "template"
    with pytest.raises(M5ProfileError):
        load_m5_profile(TEMPLATE)


def test_m5_config_accepts_only_supported_capabilities(tmp_path):
    config = m5_config(tmp_path)
    validate_config(config)
    for changed in (
        replace(config, perception=replace(config.perception,
            read=replace(config.perception.read, enabled=True))),
        replace(config, action=replace(config.action,
            tool=replace(config.action.tool, enabled=False))),
        replace(config, core=replace(config.core,
            camera=replace(config.core.camera, driver="null"))),
        replace(config, cognition=replace(config.cognition,
            llm=replace(config.cognition.llm, artifact_lock_path=tmp_path / "legacy"))),
    ):
        with pytest.raises(ConfigValueError, match="M5.tool"):
            validate_config(changed)


def test_m5_native_asr_uses_only_remote_connection_prompt(tmp_path, monkeypatch):
    launched = []
    def popen(argv, **kwargs):
        launched.append(argv)
        return SimpleNamespace(pid=1234, stdin=None, stdout=None)
    monkeypatch.setattr(asr_supervisor.subprocess, "Popen", popen)
    monkeypatch.setattr(asr_supervisor.NativeWorker, "_line",
                        lambda self, timeout: "READY\t1.9.2\t0\t1234")
    worker = asr_supervisor.NativeWorker(tmp_path / "worker", tmp_path / "model",
                                         tmp_path, "遠端連線")
    try:
        assert launched[0][-2:] == ["--initial-prompt", "遠端連線"]
    finally:
        worker._stderr.close()


def test_m5_composition_sets_asr_prompt_without_changing_m4(tmp_path, monkeypatch):
    import sbd.core.m2_composition as composition_module

    monkeypatch.setattr(composition_module, "make_audio_input", lambda cfg: object())
    monkeypatch.setattr(composition_module, "make_audio_output", lambda cfg: NullAudioOutput())
    monkeypatch.setattr(composition_module, "make_display", lambda cfg: object())
    monkeypatch.setattr(composition_module, "make_camera", lambda cfg: object())
    monkeypatch.setattr(composition_module, "make_gpio", lambda cfg: object())
    monkeypatch.setattr(composition_module, "make_tts_adapter", lambda cfg: object())
    monkeypatch.setattr(composition_module, "make_llm_adapter",
                        lambda cfg, **kwargs: SimpleNamespace(control=object()))
    adapters = []

    def make_asr(cfg):
        adapter = SimpleNamespace(_initial_prompt=None)
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(composition_module, "make_asr_adapter", make_asr)

    class CaptureRM:
        def register(self, spec):
            pass

        def begin_recovery(self, *args):
            pass

        def wait_recovery(self, *args):
            pass

    m4_path, m5_path = tmp_path / "m4", tmp_path / "m5"
    m4_path.mkdir()
    m5_path.mkdir()
    for config, expected in ((m4_config(m4_path), None),
                             (m5_config(m5_path), "遠端連線")):
        M2Composition(llm_resource_sampler=object())(CaptureRM(), EventBus(), config)
        assert adapters[-1]._initial_prompt == expected
