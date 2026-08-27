"""M4A-CFG-001 — strict real Audio config and pre-hardware rejection."""

from __future__ import annotations

import sys
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from sbd.core.config import ConfigValueError, UnknownConfigKey, load_config
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import ASRConfig, TTSConfig
from sbd.core.config.validate import validate_config
from sbd.action.speak import make_tts_adapter
from sbd.perception.listen import make_asr_adapter


def _file(path: Path, *, executable: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture")
    if executable:
        path.chmod(0o755)
    return path.resolve()


def _real_configs(tmp_path: Path) -> tuple[ASRConfig, TTSConfig]:
    runtime = _file(tmp_path / "runtime" / "bin" / "python", executable=True)
    (runtime.parent.parent / "pyvenv.cfg").write_text("include-system-site-packages = false\n", encoding="utf-8")
    lock = _file(tmp_path / "audio-artifacts.json")
    model_dir = tmp_path / "matcha"
    model_dir.mkdir()
    return (
        ASRConfig(
            driver="whispercpp", engine_name="whisper.cpp-1.9.2",
            model_path=_file(tmp_path / "ggml-base-q8_0.bin"),
            worker_path=_file(tmp_path / "m4a-whispercpp-worker", executable=True),
            runtime_python=runtime, vad_model_path=_file(tmp_path / "silero_vad.onnx"),
            artifact_lock_path=lock, language="zh-TW",
            dsp_profile="silero-6.2.1-endpoint-v1", decoder_profile="p0-greedy-best-of-1",
        ),
        TTSConfig(
            driver="sherpa_matcha", engine_name="sherpa-onnx-1.13.5-matcha",
            model_path=model_dir.resolve(), vocoder_path=_file(tmp_path / "vocos-16khz-univ.onnx"),
            runtime_python=runtime, artifact_lock_path=lock,
            voice_id="matcha-zh-en-default-sid-0", native_sample_rate=16000,
            native_channels=1, native_sample_format="s16_le",
        ),
    )


def test_m4a_cfg_001_accepts_exact_real_fields_and_paths(tmp_path: Path) -> None:
    asr, tts = _real_configs(tmp_path)
    config = replace(
        DEFAULT_CONFIG,
        perception=replace(DEFAULT_CONFIG.perception, listen=replace(DEFAULT_CONFIG.perception.listen, adapter=asr)),
        action=replace(DEFAULT_CONFIG.action, tts=tts),
    )
    validate_config(config)
    assert "onnxruntime" not in sys.modules
    assert "sherpa_onnx" not in sys.modules


@pytest.mark.parametrize(
    ("domain", "field", "wrong"),
    [
        ("asr", "engine_name", "whisper.cpp-1.9.1"),
        ("asr", "language", "zh"),
        ("asr", "dsp_profile", "other"),
        ("asr", "decoder_profile", "beam"),
        ("tts", "engine_name", "sherpa-onnx-1.13.4-matcha"),
        ("tts", "voice_id", "other"),
        ("tts", "native_sample_rate", 22050),
        ("tts", "native_channels", 2),
        ("tts", "native_sample_format", "s32_le"),
    ],
)
def test_m4a_cfg_001_rejects_mismatched_real_identity(tmp_path: Path, domain: str, field: str, wrong) -> None:
    asr, tts = _real_configs(tmp_path)
    if domain == "asr":
        asr = replace(asr, **{field: wrong})
    else:
        tts = replace(tts, **{field: wrong})
    config = replace(
        DEFAULT_CONFIG,
        perception=replace(DEFAULT_CONFIG.perception, listen=replace(DEFAULT_CONFIG.perception.listen, adapter=asr)),
        action=replace(DEFAULT_CONFIG.action, tts=tts),
    )
    with pytest.raises(ConfigValueError, match=field):
        validate_config(config)


def test_m4a_cfg_001_mock_null_need_no_artifacts_and_reject_real_only_fields(tmp_path: Path) -> None:
    validate_config(DEFAULT_CONFIG)
    null_config = replace(
        DEFAULT_CONFIG,
        perception=replace(DEFAULT_CONFIG.perception, listen=replace(DEFAULT_CONFIG.perception.listen, adapter=ASRConfig(driver="null"))),
        action=replace(DEFAULT_CONFIG.action, tts=TTSConfig(driver="null")),
    )
    validate_config(null_config)
    bad = replace(null_config, action=replace(null_config.action, tts=TTSConfig(driver="null", model_path=tmp_path)))
    with pytest.raises(ConfigValueError, match="real-only"):
        validate_config(bad)


def test_m4a_cfg_001_yaml_rejects_unknown_driver_and_checksum_override(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text("perception:\n  listen:\n    adapter:\n      driver: whisper\n", encoding="utf-8")
    with pytest.raises(ConfigValueError, match="driver"):
        load_config(local_path=unknown, dotenv_path=tmp_path / "none", environ={})
    checksum = tmp_path / "checksum.yaml"
    checksum.write_text("action:\n  tts:\n    checksum: deadbeef\n", encoding="utf-8")
    with pytest.raises(UnknownConfigKey, match="checksum"):
        load_config(local_path=checksum, dotenv_path=tmp_path / "none", environ={})


def test_m4a_cfg_001_invalid_path_rejected_before_any_native_import(tmp_path: Path) -> None:
    asr, _ = _real_configs(tmp_path)
    asr = replace(asr, model_path=(tmp_path / "missing.bin").resolve())
    config = replace(
        DEFAULT_CONFIG,
        perception=replace(DEFAULT_CONFIG.perception, listen=replace(DEFAULT_CONFIG.perception.listen, adapter=asr)),
    )
    with pytest.raises(ConfigValueError, match="model_path"):
        validate_config(config)
    assert "onnxruntime" not in sys.modules
    assert "sherpa_onnx" not in sys.modules


def test_m4a_cfg_001_public_factory_signatures_remain_single_cfg_parameter() -> None:
    assert tuple(inspect.signature(make_asr_adapter).parameters) == ("cfg",)
    assert tuple(inspect.signature(make_tts_adapter).parameters) == ("cfg",)


@pytest.mark.parametrize("kind", ["asr", "tts"])
def test_m4a_cfg_001_rejects_nonpositive_child_lifecycle_timeout(kind: str) -> None:
    if kind == "asr":
        config = replace(
            DEFAULT_CONFIG,
            perception=replace(
                DEFAULT_CONFIG.perception,
                listen=replace(
                    DEFAULT_CONFIG.perception.listen,
                    adapter=replace(
                        DEFAULT_CONFIG.perception.listen.adapter,
                        child_ready_timeout_seconds=0,
                    ),
                ),
            ),
        )
    else:
        config = replace(
            DEFAULT_CONFIG,
            action=replace(
                DEFAULT_CONFIG.action,
                tts=replace(DEFAULT_CONFIG.action.tts, child_kill_wait_timeout_seconds=float("inf")),
            ),
        )
    with pytest.raises(ConfigValueError, match="child_.*timeout_seconds"):
        validate_config(config)


@pytest.mark.parametrize("kind", ["asr", "tts"])
def test_m4a_cfg_001_factory_injects_same_verified_lock_by_keyword(
    monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    import sbd.adaptor.audio_lock as lock_module

    class SentinelLock:
        def verify_asr_config(self, cfg) -> None:
            assert cfg is config

        def verify_tts_config(self, cfg) -> None:
            assert cfg is config

    sentinel = SentinelLock()
    monkeypatch.setattr(lock_module.AudioArtifactLock, "load", lambda path: sentinel)
    calls: list[tuple[object, object]] = []
    if kind == "asr":
        import sbd.perception.listen.whispercpp.adapter as adapter_module
        config = ASRConfig(driver="whispercpp", artifact_lock_path=Path("/lock"))
        monkeypatch.setattr(
            adapter_module,
            "WhisperCppASRAdapter",
            lambda cfg, *, lock: calls.append((cfg, lock)) or object(),
        )
        make_asr_adapter(config)
    else:
        import sbd.action.speak.matcha.adapter as adapter_module
        config = TTSConfig(driver="sherpa_matcha", artifact_lock_path=Path("/lock"))
        monkeypatch.setattr(
            adapter_module,
            "MatchaTTSAdapter",
            lambda cfg, *, lock: calls.append((cfg, lock)) or object(),
        )
        make_tts_adapter(config)
    assert calls == [(config, sentinel)]


def test_m4a_cfg_001_composition_uses_same_real_owner_as_recovery_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sbd.core.m2_composition as composition_module
    from sbd.core.event_bus import EventBus

    class Owner:
        async def start(self) -> None: pass
        async def stop(self) -> None: pass
        async def rebuild(self, bus, config) -> None: pass

    class CaptureRM:
        def __init__(self) -> None:
            self.specs = []

        def register(self, spec) -> None:
            self.specs.append(spec)

    asr_owner, tts_owner = Owner(), Owner()
    monkeypatch.setattr(composition_module, "make_asr_adapter", lambda cfg: asr_owner)
    monkeypatch.setattr(composition_module, "make_tts_adapter", lambda cfg: tts_owner)
    config = replace(
        DEFAULT_CONFIG,
        perception=replace(
            DEFAULT_CONFIG.perception,
            listen=replace(
                DEFAULT_CONFIG.perception.listen,
                adapter=ASRConfig(driver="whispercpp"),
            ),
        ),
        action=replace(
            DEFAULT_CONFIG.action,
            tts=TTSConfig(driver="sherpa_matcha"),
        ),
    )
    rm = CaptureRM()
    composition_module.M2Composition()(rm, EventBus(), config)
    by_key = {spec.key: spec for spec in rm.specs}
    asr_spec = by_key["backend.perception.listen.asr"]
    tts_spec = by_key["backend.action.speak.tts"]
    assert asr_spec.factory(None) is asr_owner
    assert asr_spec.recoverable is True and asr_spec.recovery_hook is asr_owner
    assert tts_spec.factory(None) is tts_owner
    assert tts_spec.recoverable is True and tts_spec.recovery_hook is tts_owner


def test_m4a_cfg_001_mock_composition_is_not_recoverable() -> None:
    from sbd.core.event_bus import EventBus
    from sbd.core.m2_composition import M2Composition

    class CaptureRM:
        def __init__(self) -> None:
            self.specs = []

        def register(self, spec) -> None:
            self.specs.append(spec)

    rm = CaptureRM()
    M2Composition()(rm, EventBus(), DEFAULT_CONFIG)
    by_key = {spec.key: spec for spec in rm.specs}
    for key in ("backend.perception.listen.asr", "backend.action.speak.tts"):
        assert by_key[key].recoverable is False
        assert by_key[key].recovery_hook is None


@pytest.mark.parametrize(
    ("kind", "contents"),
    [
        ("asr", None),
        ("tts", None),
        ("asr", b"not-json"),
        ("tts", b'{"schema":"wrong"}'),
    ],
)
def test_m4a_cfg_001_lock_failure_precedes_real_adapter_import_and_workdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, contents: bytes | None,
) -> None:
    module_name = (
        "sbd.perception.listen.whispercpp.adapter"
        if kind == "asr"
        else "sbd.action.speak.matcha.adapter"
    )
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    lock_path = tmp_path / "audio-artifacts.json"
    if contents is not None:
        lock_path.write_bytes(contents)
    workdir_calls = 0

    def forbidden_workdir(*args, **kwargs):
        nonlocal workdir_calls
        workdir_calls += 1
        raise AssertionError("workdir must not be created")

    monkeypatch.setattr("tempfile.mkdtemp", forbidden_workdir)
    if kind == "asr":
        config = ASRConfig(driver="whispercpp", artifact_lock_path=lock_path)
        operation = lambda: make_asr_adapter(config)
    else:
        config = TTSConfig(driver="sherpa_matcha", artifact_lock_path=lock_path)
        operation = lambda: make_tts_adapter(config)
    with pytest.raises(ValueError):
        operation()
    assert module_name not in sys.modules
    assert workdir_calls == 0


def test_m4a_cfg_001_mock_and_null_factories_never_read_product_lock(monkeypatch) -> None:
    import sbd.adaptor.audio_lock as lock_module

    calls = 0

    def forbidden(path):
        nonlocal calls
        calls += 1
        raise AssertionError("mock/null must not read a product lock")

    monkeypatch.setattr(lock_module.AudioArtifactLock, "load", forbidden)
    for driver in ("mock", "null"):
        make_asr_adapter(ASRConfig(driver=driver))
        make_tts_adapter(TTSConfig(driver=driver))
    assert calls == 0
