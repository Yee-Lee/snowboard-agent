"""M4B-CFG-001 — strict config values and isolated factory surface."""

from __future__ import annotations

import inspect
import sys
from dataclasses import fields, replace
from pathlib import Path

import pytest

from sbd.cognition.factory import make_llm_adapter
from sbd.cognition.llm import LLMGeneration, LLMGenerationMetrics, LLMResourceSample
from sbd.core.config import ConfigValueError, UnknownConfigKey, load_config
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import LLMConfig
from sbd.core.config.validate import validate_config


def test_m4b_cfg_001_public_values_and_factory_signature_are_exact() -> None:
    assert [field.name for field in fields(LLMGenerationMetrics)] == [
        "init_ms", "ttft_ms", "prefill_tokens", "prefill_tokens_per_second",
        "decode_tokens", "decode_tokens_per_second", "kv_tokens",
    ]
    assert [field.name for field in fields(LLMGeneration)] == ["response", "metrics"]
    assert [field.name for field in fields(LLMResourceSample)] == ["owner_pss_bytes", "mem_available_bytes"]
    signature = inspect.signature(make_llm_adapter)
    assert tuple(signature.parameters) == ("cfg", "schedule_recovery", "wait_recovery", "resource_sampler")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in tuple(signature.parameters.values())[1:]
    )


def test_m4b_cfg_001_mock_is_side_effect_free_and_rejects_ports() -> None:
    validate_config(DEFAULT_CONFIG)
    adapter = make_llm_adapter(DEFAULT_CONFIG.cognition.llm)
    assert type(adapter).__name__ == "MockLLMEngineAdapter"
    assert "litert_lm" not in sys.modules and "litert_lm_api" not in sys.modules
    with pytest.raises(ConfigValueError, match="does not accept"):
        make_llm_adapter(DEFAULT_CONFIG.cognition.llm, schedule_recovery=lambda keys: None)


@pytest.mark.parametrize(("field", "values"), [
    ("recycle_max_inference_attempts", (7, 9)),
    ("recycle_owner_pss_delta_mib", (47, 49)),
    ("recycle_min_mem_available_mib", (767, 769)),
    ("generation_timeout_seconds", (14.0, 16.0)),
    ("terminal_grace_seconds", (1.0, 3.0)),
    ("child_ready_timeout_seconds", (44.0, 46.0)),
    ("rebuild_ready_timeout_seconds", (9.0, 11.0)),
    ("child_terminate_timeout_seconds", (1.0, 3.0)),
    ("child_kill_wait_timeout_seconds", (0.5, 2.0)),
])
def test_m4b_cfg_001_locked_numeric_drift_fails(field: str, values: tuple[object, object]) -> None:
    for value in values:
        llm = replace(DEFAULT_CONFIG.cognition.llm, **{field: value})
        config = replace(DEFAULT_CONFIG, cognition=replace(DEFAULT_CONFIG.cognition, llm=llm))
        with pytest.raises(ConfigValueError, match=field):
            validate_config(config)


def test_m4b_cfg_001_yaml_accepts_explicit_values_and_rejects_unknown_key(tmp_path: Path) -> None:
    valid = tmp_path / "valid.yaml"
    valid.write_text(
        "cognition:\n  llm:\n    recycle_max_inference_attempts: 8\n"
        "    recycle_owner_pss_delta_mib: 48\n    recycle_min_mem_available_mib: 768\n",
        encoding="utf-8",
    )
    assert load_config(local_path=valid, dotenv_path=tmp_path / "none", environ={}).cognition.llm == LLMConfig()
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("cognition:\n  llm:\n    recycle_magic: 8\n", encoding="utf-8")
    with pytest.raises(UnknownConfigKey, match="recycle_magic"):
        load_config(local_path=invalid, dotenv_path=tmp_path / "none", environ={})


def test_m4b_cfg_001_real_rejects_missing_port_before_adapter_import(tmp_path: Path) -> None:
    adapter_was_loaded = "sbd.cognition.litert_lm.adapter" in sys.modules
    files = []
    for name in ("python", "model", "profile", "lock"):
        path = (tmp_path / name).resolve()
        path.write_bytes(b"x")
        files.append(path)
    cfg = LLMConfig(
        driver="litert_lm", runtime_python=files[0], model_path=files[1],
        product_config_path=files[2], artifact_lock_path=files[3],
        profile_id="litert-lm-v0.16.0-pi-g2b-r5",
    )
    with pytest.raises(ConfigValueError, match="all recovery"):
        make_llm_adapter(cfg)
    assert ("sbd.cognition.litert_lm.adapter" in sys.modules) is adapter_was_loaded


def test_m4b_cfg_001_reasoner_abort_and_recovery_window_are_locked() -> None:
    missing = replace(
        DEFAULT_CONFIG,
        cancel=replace(
            DEFAULT_CONFIG.cancel,
            abort_timeout_seconds=replace(DEFAULT_CONFIG.cancel.abort_timeout_seconds, by_kind={}),
        ),
    )
    with pytest.raises(ConfigValueError, match="cognition.reasoner"):
        validate_config(missing)
    short = replace(DEFAULT_CONFIG, resource=replace(DEFAULT_CONFIG.resource, recovery_timeout_seconds=13.0))
    with pytest.raises(ConfigValueError, match="rebuild"):
        validate_config(short)
