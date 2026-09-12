"""Strict M4b adapter factory with validation before real-side effects."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import math

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


_WATCHDOGS = ("child_ready_timeout_seconds", "generation_timeout_seconds",
              "terminal_grace_seconds", "child_terminate_timeout_seconds",
              "child_kill_wait_timeout_seconds")


def _validate_shape(cfg: LLMConfig) -> None:
    for field in _WATCHDOGS:
        actual = getattr(cfg, field)
        if type(actual) not in (int, float) or not math.isfinite(actual) or actual <= 0:
            raise ConfigValueError(f"cognition.llm.{field} must be finite and positive")
    real_fields = (
        cfg.runtime_python,
        cfg.model_path,
        cfg.product_profile_path,
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
        "runtime_python", "model_path", "product_profile_path", "artifact_lock_path",
    ):
        value = getattr(cfg, field)
        if not isinstance(value, Path) or not value.is_absolute() or not value.is_file():
            raise ConfigValueError(f"cognition.llm.{field} must be an existing absolute file")
    if cfg.profile_id != "core-m4b-cognition-001":
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
    if (not callable(schedule_recovery) or not callable(wait_recovery) or
            not callable(getattr(resource_sampler, "sample", None))):
        raise ConfigValueError("real LLM recovery/resource ports are invalid")

    assert cfg.artifact_lock_path is not None
    repo_root = cfg.artifact_lock_path.resolve().parents[2]
    lock = LLMArtifactLock.load(cfg.artifact_lock_path, repo_root=repo_root)
    profile = lock.verify_config_paths(cfg)
    lock = replace(lock, identity=lock.ready_identity(profile), product_profile=profile)

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
