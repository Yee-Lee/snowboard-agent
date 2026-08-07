"""Deterministic, payload-safe prompt construction for the M2 reasoner."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from sbd.core.events import PerceptionResult


_PERCEPTION_ORDER = {"listen": 0, "read": 1, "look": 2}


@dataclass(frozen=True, slots=True)
class ReasoningInput:
    perceptions: tuple[PerceptionResult, ...]
    pending_message_ids: tuple[str, ...]
    available_perceptions: tuple[str, ...]
    available_actions: tuple[str, ...]
    tool_schemas: tuple[dict[str, Any], ...]


class PromptBuilder:
    """Build one complete prompt per turn without retaining conversation state."""

    def __init__(self, tool_schemas: tuple[dict[str, Any], ...] = ()) -> None:
        self._tool_schemas = copy.deepcopy(tool_schemas)

    def build(self, value: ReasoningInput) -> str:
        ordered = sorted(
            value.perceptions,
            key=lambda fact: _PERCEPTION_ORDER[fact.kind],
        )
        document = {
            "perceptions": [
                {
                    "kind": fact.kind,
                    "status": fact.status,
                    "text": fact.text,
                    "extra": copy.deepcopy(fact.extra),
                }
                for fact in ordered
            ],
            "pending_messages": {
                "count": len(value.pending_message_ids),
                "opaque_ids": list(value.pending_message_ids),
            },
            "available_perceptions": list(value.available_perceptions),
            "available_actions": list(value.available_actions),
            "tools": copy.deepcopy(value.tool_schemas or self._tool_schemas),
            "output_contract": {
                "exact_fields": [
                    "action_kind",
                    "action_payload",
                    "next_perceptions",
                ],
                "action_kinds": ["speak", "tool", "rest"],
                "rest_next_perceptions": [],
            },
        }
        return json.dumps(document, ensure_ascii=False, sort_keys=True)


__all__ = ["PromptBuilder", "ReasoningInput"]
