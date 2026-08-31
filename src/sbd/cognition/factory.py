"""Strict M4b adapter factory with validation before real-side effects."""

from __future__ import annotations

from pathlib import Path

from sbd.cognition.litert_lm.lock import LLMArtifactLock
from sbd.cognition.llm import (
    LLMEngineAdapter,
    LLMGeneration,
    LLMGenerationMetrics,
    LLMResourceSampler,
    MockLLMEngineAdapter,
    ScheduleRecovery,
    WaitRecovery,
)
from sbd.core.config.models import LLMConfig
from sbd.core.config.validate import ConfigValueError


_EXACT_NUMERIC = {
    "child_ready_timeout_seconds": 45.0,
    "generation_timeout_seconds": 15.0,
    "terminal_grace_seconds": 2.0,
    "child_terminate_timeout_seconds": 2.0,
    "child_kill_wait_timeout_seconds": 1.0,
    "rebuild_ready_timeout_seconds": 10.0,
    "recycle_max_inference_attempts": 8,
    "recycle_owner_pss_delta_mib": 48,
    "recycle_min_mem_available_mib": 768,
}


def _validate_shape(cfg: LLMConfig) -> None:
    for field, expected in _EXACT_NUMERIC.items():
        actual = getattr(cfg, field)
        expected_type = int if isinstance(expected, int) else float
        if type(actual) is not expected_type or actual != expected:
            raise ConfigValueError(f"cognition.llm.{field} must be {expected!r}")
    real_fields = (
        cfg.runtime_python,
        cfg.model_path,
        cfg.product_config_path,
        cfg.artifact_lock_path,
        cfg.profile_id,
    )
    if cfg.driver == "mock":
        if any(item is not None for item in real_fields):
            raise ConfigValueError("cognition.llm mock cannot contain real-only fields")
        return
    if cfg.driver != "litert_lm":
        raise ConfigValueError("cognition.llm.driver is unsupported")
    for field in (
        "runtime_python", "model_path", "product_config_path", "artifact_lock_path",
    ):
        value = getattr(cfg, field)
        if not isinstance(value, Path) or not value.is_absolute() or not value.is_file():
            raise ConfigValueError(f"cognition.llm.{field} must be an existing absolute file")
    if cfg.profile_id != "litert-lm-v0.16.0-pi-g2b-r5":
        raise ConfigValueError("cognition.llm.profile_id mismatch")


def _mock_generation() -> LLMGeneration:
    return LLMGeneration(
        {"action_kind": "rest", "action_payload": {}, "next_perceptions": []},
        LLMGenerationMetrics(0.0, 1.0, 1, 1.0, 1, 1.0, 1),
    )


def make_llm_adapter(
    cfg: LLMConfig,
    *,
    schedule_recovery: ScheduleRecovery | None = None,
    wait_recovery: WaitRecovery | None = None,
    resource_sampler: LLMResourceSampler | None = None,
) -> LLMEngineAdapter:
    _validate_shape(cfg)
    ports = (schedule_recovery, wait_recovery, resource_sampler)
    if cfg.driver == "mock":
        if any(port is not None for port in ports):
            raise ConfigValueError("mock LLM does not accept recovery/resource ports")
        return MockLLMEngineAdapter((_mock_generation(),))
    if any(port is None for port in ports):
        raise ConfigValueError("real LLM requires all recovery/resource ports")

    assert cfg.artifact_lock_path is not None
    repo_root = cfg.artifact_lock_path.resolve().parents[2]
    lock = LLMArtifactLock.load(cfg.artifact_lock_path, repo_root=repo_root)
    lock.verify_config_paths(cfg)

    # The internal adapter module is pure Python. The selected native runtime is
    # imported only by the isolated worker after spawn and identity checks.
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter

    assert schedule_recovery is not None
    assert wait_recovery is not None
    assert resource_sampler is not None
    return LiteRTLMAdapter(
        cfg,
        lock=lock,
        schedule_recovery=schedule_recovery,
        wait_recovery=wait_recovery,
        resource_sampler=resource_sampler,
    )


__all__ = ["make_llm_adapter"]
