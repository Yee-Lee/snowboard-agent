#!/usr/bin/env python3
"""Private-evidence oracle for M4C-PI-S05 application shutdown."""

from __future__ import annotations

from typing import Any


class S05OracleError(AssertionError):
    """Stable S05 adjudication failure."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise S05OracleError(code)


def validate_s05_private_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the direct product risks and return the public projection."""
    _require(value.get("schema_version") == 1, "M4C_S05_SCHEMA_INVALID")
    _require(value.get("variant") == "APP_EXIT", "M4C_S05_VARIANT_INVALID")
    _require(value.get("application_exit_code") == 0, "M4C_S05_EXIT_NONZERO")
    _require(value.get("shutdown_signal_count") == 1,
             "M4C_S05_SHUTDOWN_SIGNAL_INVALID")
    _require(value.get("wake_entry_count") == 0, "M4C_S05_SESSION_ACCEPTED")
    _require(value.get("shutdown_blank_seen") is True,
             "M4C_S05_SHUTDOWN_BLANK_MISSING")
    _require(value.get("blank_before_display_close") is True,
             "M4C_S05_DISPLAY_CLOSED_BEFORE_BLANK")
    _require(value.get("stop_failure_count") == 0,
             "M4C_S05_RESOURCE_STOP_FAILED")
    _require(value.get("surviving_native_child_count") == 0,
             "M4C_S05_NATIVE_CHILD_SURVIVED")

    return {
        "schema_version": 1,
        "scenario_code": "M4C-PI-S05/APP_EXIT",
        "status_code": "APPLICATION_EXITED",
        "application_exit_code": 0,
        "session_accepted": False,
        "shutdown_blank_before_display_close": True,
        "stop_failure_count": 0,
        "surviving_native_child_count": 0,
    }


__all__ = ["S05OracleError", "validate_s05_private_evidence"]
