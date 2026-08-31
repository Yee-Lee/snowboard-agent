"""Bounded semantic projection for the structured M4b reasoner seam."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from sbd.core.events import PerceptionResult


_PERCEPTION_ORDER = {"listen": 0, "read": 1, "look": 2}
_ACTION_ORDER = {"speak": 0, "tool": 1, "rest": 2}


@dataclass(frozen=True, slots=True)
class ReasoningPerception:
    kind: str
    status: str
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningInput:
    perceptions: tuple[ReasoningPerception, ...]
    pending_message_count: int
    available_perceptions: tuple[str, ...]
    available_actions: tuple[str, ...]
    tool_schemas: tuple[dict[str, Any], ...]


class PromptBuilder:
    """Project product facts into one stateless, handler-free semantic value."""

    def __init__(self, tool_schemas: tuple[dict[str, Any], ...] = ()) -> None:
        self._tool_schemas = copy.deepcopy(tool_schemas)

    def build(
        self,
        *,
        perceptions: tuple[PerceptionResult, ...],
        pending_message_count: int,
        available_perceptions: tuple[str, ...],
        available_actions: tuple[str, ...],
    ) -> ReasoningInput:
        projected = tuple(
            ReasoningPerception(
                kind=fact.kind,
                status=fact.status,
                text="" if fact.text is None else fact.text,
            )
            for fact in sorted(
                perceptions,
                key=lambda fact: _PERCEPTION_ORDER.get(
                    fact.kind, len(_PERCEPTION_ORDER)
                ),
            )
        )
        perception_capabilities = tuple(sorted(
            available_perceptions,
            key=lambda kind: _PERCEPTION_ORDER.get(
                kind, len(_PERCEPTION_ORDER)
            ),
        ))
        actions = set(available_actions)
        actions.add("rest")
        if not self._tool_schemas:
            actions.discard("tool")
        if not perception_capabilities:
            actions.discard("speak")
            actions.discard("tool")
        action_capabilities = tuple(sorted(
            actions,
            key=lambda kind: _ACTION_ORDER.get(kind, len(_ACTION_ORDER)),
        ))
        return ReasoningInput(
            perceptions=projected,
            pending_message_count=pending_message_count,
            available_perceptions=perception_capabilities,
            available_actions=action_capabilities,
            tool_schemas=tuple(copy.deepcopy(self._tool_schemas)),
        )


__all__ = ["PromptBuilder", "ReasoningInput", "ReasoningPerception"]
