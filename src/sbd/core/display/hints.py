"""Immutable display intent values and public validation errors."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType
from typing import Any, Mapping


class DisplayArbiterError(RuntimeError):
    pass


class DisplayHintError(ValueError):
    pass


class UnknownDisplaySlot(DisplayHintError):
    pass


def _freeze_json(value: Any, path: str = "data") -> Any:
    if value is None or type(value) in {str, int, float, bool}:
        if type(value) is float and not math.isfinite(value):
            raise DisplayHintError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise DisplayHintError(f"{path} keys must be strings")
            copied[key] = _freeze_json(item, f"{path}.{key}")
        return MappingProxyType(copied)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[]") for item in value)
    raise DisplayHintError(f"{path} contains a non-JSON value")


@dataclass(frozen=True, slots=True)
class DisplayHint:
    template: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.template) is not str or not self.template:
            raise DisplayHintError("template must be a non-empty string")
        if not isinstance(self.data, Mapping):
            raise DisplayHintError("data must be a mapping")
        object.__setattr__(self, "data", _freeze_json(self.data))
