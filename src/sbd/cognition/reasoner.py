"""Reasoner — single cognition module.

Per Ch 2 §2.8, cognition has no base.py Protocol (single implementation).
This module defines the Reasoner class with the same in-flight contract
as Perception/Action workers.

M1 provides only the skeleton signature; M2+ supplies the real implementation.
"""

from __future__ import annotations

from typing import Any, Callable

from sbd.core.lifecycle import ForceAbortReport


class Reasoner:
    """Single cognition module that drives LLM reasoning.

    Constructor dependencies are placeholders for M1; real types
    (LLMEngineAdapter, PromptBuilder) are defined in Ch 2b (M2+).
    """

    def __init__(
        self,
        llm: Any,                                  # Ch 2b LLMEngineAdapter
        prompt_builder: Any,                        # Ch 2b PromptBuilder
        bus: Any,                                   # EventBus
        capability_of: Callable[[str], bool],
    ) -> None:
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._bus = bus
        self._capability_of = capability_of

    async def start(self) -> None:
        """LLM engine warmup and prompt template loading."""
        ...

    async def stop(self) -> None:
        """Release LLM engine resources."""
        ...

    async def abort(self) -> None:
        """Level 1 cooperative cancellation of in-flight reason()."""
        ...

    async def force_abort(self) -> ForceAbortReport:
        """Level 2 forced convergence; reports destroyed backends."""
        return ForceAbortReport()

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[Any, ...],
        pending_message_ids: tuple[str, ...],
    ) -> None:
        """Execute reasoning.  Publishes LLMResponse via the Bus.

        Returns None; the terminal Fact is published, not returned.
        """
        ...
