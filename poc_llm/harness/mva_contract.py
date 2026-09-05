"""Pure M4B-MVA contract helpers; no model, Pi, or product composition imports."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Callable, Mapping


PROTOCOL_VERSION = "snowboard.llm/2"
READY_NO_SESSION = "READY_NO_SESSION"
SESSION_IDLE = "SESSION_IDLE"
GENERATING = "GENERATING"
FATAL = "FATAL"
SESSION_FACTS = {
    "name": "雪板",
    "role": "你的語音小助理",
    "locale": "zh-TW",
    "available_perceptions": ["listen"],
    "available_actions": ["speak", "rest"],
}


class ContractViolation(ValueError):
    """A frozen MVA input, semantic, lifecycle, or identity rule was violated."""


def _is_non_bool_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_semantic(value: object) -> dict[str, object]:
    """Accept only exact compact text/end output and return a defensive copy."""

    if not isinstance(value, dict) or set(value) != {"text", "end"}:
        raise ContractViolation("semantic output must contain exact text/end keys")
    text = value["text"]
    end = value["end"]
    if not isinstance(text, str) or not isinstance(end, bool):
        raise ContractViolation("semantic text/end types are invalid")
    if len(text) > 4096:
        raise ContractViolation("semantic text exceeds wire limit")
    if end and text != "":
        raise ContractViolation("end=true requires empty text")
    if not end and not text.strip():
        raise ContractViolation("end=false requires nonblank text")
    return {"text": text, "end": end}


def validate_session_facts(value: object) -> dict[str, object]:
    """Reject capability drift and all tool/look/read additions for the MVA profile."""

    if value != SESSION_FACTS:
        raise ContractViolation("SessionFacts do not match the frozen MVA profile")
    return json.loads(json.dumps(SESSION_FACTS, ensure_ascii=False))


def reasoner_projection(
    semantic: object,
    *,
    speak_available: bool = True,
    listen_available: bool = True,
) -> dict[str, object]:
    """Project model semantics into the canonical action owned by Reasoner."""

    result = validate_semantic(semantic)
    if result["end"] or not (speak_available and listen_available):
        return {"action_kind": "rest", "action_payload": {}, "next_perceptions": []}
    return {
        "action_kind": "speak",
        "action_payload": {"text": result["text"]},
        "next_perceptions": ["listen"],
    }


def render_user_turn(template: str, user_text: str) -> str:
    """Render only the new perception; history remains in the active Conversation."""

    marker = "{{USER_TEXT_JSON}}"
    if template.count(marker) != 1:
        raise ContractViolation("user template must contain one JSON marker")
    if not isinstance(user_text, str) or not user_text:
        raise ContractViolation("user turn text must be nonempty")
    return template.replace(marker, json.dumps(user_text, ensure_ascii=False))


def admit_tokens(
    *,
    new_user_tokens: int,
    incremental_tokens: int,
    current_kv_tokens: int,
    output_reserve_tokens: int = 128,
    user_new_limit: int = 32,
    engine_kv_limit: int = 1024,
) -> None:
    """Apply separate new-user and total incremental/KV admission boundaries."""

    values = (
        new_user_tokens,
        incremental_tokens,
        current_kv_tokens,
        output_reserve_tokens,
        user_new_limit,
        engine_kv_limit,
    )
    if any(not _is_non_bool_int(value) or value < 0 for value in values):
        raise ContractViolation("token counts and limits must be nonnegative integers")
    if new_user_tokens > user_new_limit:
        raise ContractViolation("INPUT_TOO_LARGE")
    if current_kv_tokens + incremental_tokens + output_reserve_tokens > engine_kv_limit:
        raise ContractViolation("CONTEXT_LIMIT")


@dataclass
class MvaLifecycleOracle:
    """Deterministic oracle for one-Conversation-per-product-session behavior."""

    state: str = READY_NO_SESSION
    session_id: str | None = None
    last_closed_session_id: str | None = None
    last_turn_id: int = 0
    conversation_creates: int = 0
    conversation_closes: int = 0
    events: list[str] = field(default_factory=list)

    def open_session(self, session_id: str, facts: object) -> None:
        if self.state != READY_NO_SESSION or self.session_id is not None:
            raise ContractViolation("SESSION_MISMATCH")
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            raise ContractViolation("invalid session identity")
        validate_session_facts(facts)
        self.session_id = session_id
        self.last_turn_id = 0
        self.conversation_creates += 1
        self.state = SESSION_IDLE
        self.events.append(f"open:{session_id}")

    def begin_generate(self, session_id: str, turn_id: int) -> None:
        if self.state != SESSION_IDLE or session_id != self.session_id:
            raise ContractViolation("SESSION_MISMATCH")
        if not _is_non_bool_int(turn_id) or turn_id != self.last_turn_id + 1:
            raise ContractViolation("turn identity must increase by one")
        self.state = GENERATING
        self.events.append(f"generate:{session_id}:{turn_id}")

    def finish_generate(self, session_id: str, turn_id: int, semantic: object) -> dict[str, object]:
        if self.state != GENERATING or session_id != self.session_id:
            raise ContractViolation("SESSION_MISMATCH")
        if turn_id != self.last_turn_id + 1:
            raise ContractViolation("late or duplicate terminal")
        result = validate_semantic(semantic)
        self.last_turn_id = turn_id
        self.state = SESSION_IDLE
        self.events.append(f"result:{session_id}:{turn_id}")
        return result

    def close_session(self, session_id: str, reason: str) -> None:
        if self.state == READY_NO_SESSION and self.session_id is None:
            if session_id == self.last_closed_session_id:
                self.events.append(f"close-noop:{session_id}")
                return
            raise ContractViolation("SESSION_MISMATCH")
        if session_id != self.session_id:
            raise ContractViolation("SESSION_MISMATCH")
        if self.state == GENERATING:
            raise ContractViolation("active generation requires typed convergence")
        if reason not in {"rest", "interrupt", "error", "shutdown", "capacity"}:
            raise ContractViolation("invalid close reason")
        self._discard_conversation(f"close:{session_id}:{reason}")

    def dirty_terminal(self, session_id: str, code: str) -> None:
        if session_id != self.session_id or self.state != GENERATING:
            raise ContractViolation("SESSION_MISMATCH")
        if code not in {"TIMEOUT", "GENERATION_FAILED", "INVALID_OUTPUT", "CANCELLED"}:
            raise ContractViolation("not a dirty terminal")
        self._discard_conversation(f"dirty:{session_id}:{code}")

    def cleanup_failed(self, session_id: str) -> None:
        if session_id != self.session_id:
            raise ContractViolation("SESSION_MISMATCH")
        self.state = FATAL
        self.events.append(f"fatal:{session_id}:CLEANUP_FAILED")

    def _discard_conversation(self, event: str) -> None:
        assert self.session_id is not None
        closed = self.session_id
        self.conversation_closes += 1
        self.session_id = None
        self.last_closed_session_id = closed
        self.last_turn_id = 0
        self.state = READY_NO_SESSION
        self.events.append(event)


def ordinary_least_squares_slope(samples: list[tuple[int, float]]) -> float:
    """Return the fixed-window OLS slope in MiB/session."""

    if len(samples) < 2:
        raise ContractViolation("at least two samples are required")
    xs = [item[0] for item in samples]
    ys = [item[1] for item in samples]
    if any(not _is_non_bool_int(value) for value in xs):
        raise ContractViolation("session indices must be integers")
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    if denominator == 0:
        raise ContractViolation("session indices must vary")
    return sum((x - mean_x) * (y - mean_y) for x, y in samples) / denominator


def fixed_steady_window(samples: Mapping[int, float]) -> list[tuple[int, float]]:
    """Select exactly sessions 11-20; never substitute a post-hoc window."""

    required = list(range(11, 21))
    if any(index not in samples for index in required):
        raise ContractViolation("steady analysis window is incomplete")
    return [(index, float(samples[index])) for index in required]


def sha256_file(path: Path, digest: Callable[[bytes], str]) -> str:
    """Small injection point used by the future non-recursive surface lock builder."""

    return digest(path.read_bytes())
