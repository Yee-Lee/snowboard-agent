"""Bounded semantic projection for the structured M4b reasoner seam."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any

from sbd.core.events import PerceptionResult
from sbd.cognition.semantic import SemanticError, normalize_text


PROFILE_ID = "core-m4b-cognition-001"
CORE_PROMPT = "你是「雪板」繁體中文語音助理，只能聽與說，不能看或使用工具。只輸出含 text、end 的 JSON。一般回答的 text 不超過30字且 end=false；明確要求結束時 end=true。語氣："
PERSONALITY_PROMPT = "溫暖自然，稍帶幽默。"
SYSTEM_PROMPT = CORE_PROMPT + PERSONALITY_PROMPT
PROMPT_COUNTS = {"core": 57, "personality": 9, "system": 66}
PROMPT_HASHES = {
    "core": "8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec",
    "personality": "57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5",
    "system": "872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643",
}


def validate_prompt_identity() -> None:
    for name, text in (("core", CORE_PROMPT), ("personality", PERSONALITY_PROMPT),
                       ("system", SYSTEM_PROMPT)):
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != PROMPT_HASHES[name]:
            raise ValueError("PROMPT_IDENTITY_MISMATCH")


def attest_prompt(tokenize) -> dict[str, int]:
    validate_prompt_identity()
    counts = {}
    for name, text in (("core", CORE_PROMPT), ("personality", PERSONALITY_PROMPT),
                       ("system", SYSTEM_PROMPT)):
        try:
            tokens = tokenize(text)
            count = tokens if type(tokens) is int else len(tokens)
        except Exception:
            raise ValueError("PROMPT_TOKENIZER_MISMATCH") from None
        if type(count) is not int or count != PROMPT_COUNTS[name]:
            raise ValueError("PROMPT_TOKENIZER_MISMATCH")
        counts[name] = count
    return counts


class UnsupportedInputError(ValueError):
    def __init__(self) -> None:
        super().__init__("UNSUPPORTED_INPUT")


class ListenProjector:
    def project(self, *, perceptions: tuple[PerceptionResult, ...], session_id: str,
                turn_id: int, pending_message_count: int,
                available_perceptions: tuple[str, ...],
                available_actions: tuple[str, ...]) -> str | None:
        if (type(perceptions) is not tuple or len(perceptions) != 1 or
                type(pending_message_count) is not int or pending_message_count != 0 or
                "listen" not in available_perceptions or "speak" not in available_actions):
            raise UnsupportedInputError()
        fact = perceptions[0]
        if (not isinstance(fact, PerceptionResult) or fact.session_id != session_id or
                fact.turn_id != turn_id or fact.kind != "listen" or
                fact.status not in ("ok", "timeout", "error")):
            raise UnsupportedInputError()
        if fact.status != "ok":
            return None
        try:
            return normalize_text(fact.text) or None
        except SemanticError:
            raise UnsupportedInputError() from None


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


__all__ = ["PromptBuilder", "ReasoningInput", "ReasoningPerception", "ListenProjector",
           "UnsupportedInputError", "PROFILE_ID", "CORE_PROMPT", "PERSONALITY_PROMPT",
           "SYSTEM_PROMPT", "PROMPT_COUNTS", "PROMPT_HASHES", "attest_prompt",
           "validate_prompt_identity"]
