"""Central settings.

Three-layer loading (see docs/arch.md §13):
    defaults (this file) -> config.local.yaml -> environment variables

M1 only implements defaults + optional YAML overlay. .env loading is a stub
for M2+ so the API is stable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass
class StateManagerSettings:
    error_recovery_seconds: float = 1.5
    perception_timeout_seconds: float = 8.0


@dataclass
class LoggingSettings:
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


@dataclass
class Settings:
    state_manager: StateManagerSettings = field(default_factory=StateManagerSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    models_dir: Path = MODELS_DIR


def _merge(dc: Any, overrides: dict[str, Any]) -> None:
    for f in fields(dc):
        if f.name not in overrides:
            continue
        value = overrides[f.name]
        current = getattr(dc, f.name)
        if is_dataclass(current) and isinstance(value, dict):
            _merge(current, value)
        else:
            setattr(dc, f.name, value)


def load_settings(local_yaml: Path | None = None) -> Settings:
    settings = Settings()

    yaml_path = local_yaml or PROJECT_ROOT / "config.local.yaml"
    if yaml_path.exists():
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            pass
        else:
            with yaml_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if isinstance(data, dict):
                _merge(settings, data)

    level_override = os.environ.get("SBD_LOG_LEVEL")
    if level_override:
        settings.logging.level = level_override

    return settings
