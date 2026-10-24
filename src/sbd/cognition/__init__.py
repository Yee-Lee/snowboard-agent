"""Cognition subsystem."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .factory import make_llm_adapter
    from .llm import (
        LLMEngineAdapter,
        LLMGeneration,
        LLMGenerationMetrics,
        LLMResourceSample,
    )


def __getattr__(name: str) -> Any:
    if name == "make_llm_adapter":
        return import_module(".factory", __name__).make_llm_adapter
    if name in {
        "LLMEngineAdapter",
        "LLMGeneration",
        "LLMGenerationMetrics",
        "LLMResourceSample",
    }:
        return getattr(import_module(".llm", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "LLMEngineAdapter",
    "LLMGeneration",
    "LLMGenerationMetrics",
    "LLMResourceSample",
    "make_llm_adapter",
]
