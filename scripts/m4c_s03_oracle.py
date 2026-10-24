#!/usr/bin/env python3
"""Behavioral oracle for M4C-PI-S03/TWO_TIMEOUTS."""

from __future__ import annotations

from typing import Any


RETRY_TEXT = "我沒聽清楚，請再說一次。"


class S03OracleError(AssertionError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise S03OracleError(code)


def validate_s03_private_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the single-session two-timeout behavior and return a safe projection."""
    required = {
        "schema_version", "perceptions", "responses", "actions",
        "no_input_streaks", "reasoner_call_count", "order", "playback", "cleanup",
    }
    _require(type(value) is dict and set(value) == required and value["schema_version"] == 1,
             "M4C_S03_EVIDENCE_SCHEMA_INVALID")

    perceptions = value["perceptions"]
    _require(type(perceptions) is list and len(perceptions) == 2,
             "M4C_S03_TIMEOUT_COUNT_INVALID")
    _require([item.get("status") for item in perceptions] == ["timeout", "timeout"],
             "M4C_S03_TIMEOUT_CLASSIFICATION_INVALID")
    session_ids = [item.get("session_id") for item in perceptions]
    _require(all(type(item) is str and item for item in session_ids)
             and session_ids[0] == session_ids[1], "M4C_S03_SESSION_CHANGED")
    _require([item.get("turn_id") for item in perceptions] == [1, 2],
             "M4C_S03_TURN_SEQUENCE_INVALID")

    responses = value["responses"]
    _require(type(responses) is list and len(responses) == 2,
             "M4C_S03_RESPONSE_COUNT_INVALID")
    first, second = responses
    _require(
        first.get("action_kind") == "speak"
        and first.get("action_payload") == {"text": RETRY_TEXT}
        and first.get("post_action_route") == "KEEP_NEXT",
        "M4C_S03_RETRY_RESPONSE_INVALID",
    )
    _require(
        second.get("action_kind") == "rest"
        and second.get("action_payload") == {}
        and second.get("post_action_route") == "END_SESSION",
        "M4C_S03_SECOND_TIMEOUT_ROUTE_INVALID",
    )
    _require(value["no_input_streaks"] == [1, 2], "M4C_S03_STREAK_INVALID")
    _require(value["reasoner_call_count"] == 0, "M4C_S03_LLM_CALLED")

    actions = value["actions"]
    _require(
        type(actions) is list
        and [(item.get("kind"), item.get("status")) for item in actions]
        == [("speak", "ok"), ("rest", "ok")],
        "M4C_S03_ACTION_SEQUENCE_INVALID",
    )
    order = value["order"]
    required_order = [
        "timeout_1", "retry_speak_complete", "listen_2_started",
        "timeout_2", "rest_complete", "idle",
    ]
    _require(
        type(order) is list
        and all(item in order for item in required_order)
        and [order.index(item) for item in required_order]
        == sorted(order.index(item) for item in required_order),
        "M4C_S03_ORDER_INVALID",
    )

    playback = value["playback"]
    _require(
        type(playback) is dict
        and playback == {"retry_play_count": 1, "complete": True},
        "M4C_S03_RETRY_PLAYBACK_INVALID",
    )
    cleanup = value["cleanup"]
    _require(
        type(cleanup) is dict
        and cleanup.get("state") == "IDLE"
        and cleanup.get("status") == "待命"
        and cleanup.get("main_empty") is True,
        "M4C_S03_CLEANUP_INVALID",
    )

    return {
        "schema_version": 1,
        "scenario_code": "M4C-PI-S03/TWO_TIMEOUTS",
        "timeout_count": 2,
        "streak_transitions": [1, 2],
        "retry_speak_count": 1,
        "rest_count": 1,
        "reasoner_call_count": 0,
        "same_session": True,
        "ordered_after_retry_playback": True,
        "terminal_state_code": "IDLE",
        "status_code": "IDLE_READY",
        "main_empty": True,
    }


__all__ = ["RETRY_TEXT", "S03OracleError", "validate_s03_private_evidence"]
