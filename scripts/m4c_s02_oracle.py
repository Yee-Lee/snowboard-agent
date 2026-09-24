"""Deterministic oracle for the composite M4C S02 streaming session."""

from __future__ import annotations

import hashlib
import re
from typing import Any


TIMELINE_KEYS = (
    "button_acceptance",
    "conversation_ready",
    "asr_final",
    "llm_send",
    "first_safe_text",
    "tts_first_pcm",
    "audio_first_write",
    "llm_terminal",
    "playback_complete",
    "drain_complete",
    "turn2_asr_final",
    "turn2_llm_terminal",
    "turn2_playback_complete",
    "turn2_drain_complete",
    "idle",
)


class S02OracleError(ValueError):
    """A stable fail-closed reason for invalid private scenario evidence."""


def _fail(code: str) -> None:
    raise S02OracleError(code)


def expected_display_publications(
    utterance_1: str,
    answer_1: str,
    utterance_2: str,
    answer_2: str,
) -> list[tuple[str, str | None]]:
    """Exact Main-slot publications for either legal second-turn branch."""
    values = [
        ("WAKE", None),
        ("THINK", utterance_1),
        ("ACTION", answer_1),
        ("THINK", utterance_2),
    ]
    if answer_2:
        values.append(("ACTION", answer_2))
    values.append(("IDLE", None))
    return values


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_s02_private_evidence(value: object) -> dict[str, Any]:
    """Validate private evidence and return its privacy-safe public projection."""
    if type(value) is not dict or set(value) != {
        "schema_version", "streaming_path", "fragments", "terminal_text",
        "spoken_text", "display_text", "provisional_display_publications",
        "timeline", "playback", "turn2", "cleanup",
    }:
        _fail("M4C_S02_EVIDENCE_SCHEMA_INVALID")
    if value["schema_version"] != 1 or value["streaming_path"] != (
        "B2-ONE-LOOKAHEAD-COALESCE"
    ):
        _fail("M4C_S02_B2_PATH_INVALID")

    fragments = value["fragments"]
    if (type(fragments) is not list or not fragments
            or any(type(item) is not str or not item for item in fragments)):
        _fail("M4C_S02_ELIGIBLE_FRAGMENT_MISSING")
    terminal = value["terminal_text"]
    spoken = value["spoken_text"]
    displayed = value["display_text"]
    if any(type(item) is not str or not item for item in (terminal, spoken, displayed)):
        _fail("M4C_S02_ANSWER_INVALID")
    if "".join(fragments) != terminal:
        _fail("M4C_S02_FRAGMENT_TERMINAL_MISMATCH")
    digests = {_digest(item) for item in (terminal, spoken, displayed)}
    if len(digests) != 1:
        _fail("M4C_S02_ANSWER_DIGEST_MISMATCH")
    if value["provisional_display_publications"] != 0:
        _fail("M4C_S02_PROVISIONAL_DISPLAY_LEAK")

    timeline = value["timeline"]
    if type(timeline) is not dict or tuple(timeline) != TIMELINE_KEYS:
        _fail("M4C_S02_TIMELINE_SCHEMA_INVALID")
    if any(type(timeline[key]) is not int or timeline[key] <= 0 for key in TIMELINE_KEYS):
        _fail("M4C_S02_TIMELINE_NODE_INVALID")
    if any(timeline[left] > timeline[right] for left, right in zip(
        TIMELINE_KEYS, TIMELINE_KEYS[1:]
    )):
        _fail("M4C_S02_TIMELINE_ORDER_INVALID")
    if timeline["audio_first_write"] >= timeline["llm_terminal"]:
        _fail("M4C_S02_FIRST_WRITE_NOT_PRETERMINAL")
    playback = value["playback"]
    if (type(playback) is not dict or set(playback) != {
            "admitted_fragment_count", "played_fragment_count", "play_call_count",
            "drain_call_count", "complete"}
            or playback["complete"] is not True
            or type(playback["admitted_fragment_count"]) is not int
            or playback["admitted_fragment_count"] != len(fragments)
            or playback["played_fragment_count"] != len(fragments)
            or type(playback["play_call_count"]) is not int
            or playback["play_call_count"] <= 0
            or playback["drain_call_count"] != playback["play_call_count"]):
        _fail("M4C_S02_PLAYBACK_DRAIN_INCOMPLETE")

    turn2 = value["turn2"]
    if type(turn2) is not dict or set(turn2) != {
        "end", "branch", "answer_length"
    }:
        _fail("M4C_S02_TURN2_SCHEMA_INVALID")
    if (turn2["end"] is not True
            or turn2["branch"] not in {"nonempty_play_then_rest", "empty_direct_rest"}
            or type(turn2["answer_length"]) is not int or turn2["answer_length"] < 0):
        _fail("M4C_S02_TURN2_OUTCOME_INVALID")
    if ((turn2["branch"] == "empty_direct_rest") != (turn2["answer_length"] == 0)):
        _fail("M4C_S02_TURN2_BRANCH_INVALID")

    cleanup = value["cleanup"]
    if type(cleanup) is not dict or cleanup != {
        "conversation_close": True,
        "request_terminal": True,
        "stream_closed": True,
        "owner_count": 0,
        "state": "IDLE",
        "status": "待命",
        "main_empty": True,
    }:
        _fail("M4C_S02_CLEANUP_INVALID")

    answer_digest = digests.pop()
    return {
        "schema_version": 1,
        "scenario_code": "M4C-PI-S02/NORMAL_END",
        "streaming_path_code": "B2-ONE-LOOKAHEAD-COALESCE",
        "fragment_count": len(fragments),
        "fragment_lengths": [len(item) for item in fragments],
        "answer_codepoints": len(terminal),
        "answer_sha256": answer_digest,
        "display_sha256": answer_digest,
        "spoken_sha256": answer_digest,
        "provisional_display_publication_count": 0,
        "timeline_nodes_ns": dict(timeline),
        "preterminal_first_write_margin_ns": (
            timeline["llm_terminal"] - timeline["audio_first_write"]
        ),
        "played_fragment_count": playback["played_fragment_count"],
        "play_call_count": playback["play_call_count"],
        "drain_call_count": playback["drain_call_count"],
        "playback_drain_complete": True,
        "turn2_branch_code": turn2["branch"],
        "turn2_answer_length": turn2["answer_length"],
        "conversation_close_proven": True,
        "request_terminal_proven": True,
        "stream_closed": True,
        "owner_count": 0,
        "terminal_state_code": "IDLE",
        "status_code": "IDLE_READY",
        "main_empty": True,
    }


__all__ = [
    "S02OracleError",
    "TIMELINE_KEYS",
    "expected_display_publications",
    "validate_s02_private_evidence",
]
