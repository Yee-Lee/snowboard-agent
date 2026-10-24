#!/usr/bin/env python3
"""Private-evidence oracle for M4C-PI-S04 interrupt variants."""

from __future__ import annotations

from typing import Any


VARIANTS = ("PERCEPTION", "THINK", "ACTION")


class S04OracleError(AssertionError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise S04OracleError(code)


def validate_s04_private_evidence(value: dict[str, Any]) -> dict[str, Any]:
    _require(type(value) is dict and value.get("schema_version") == 1,
             "M4C_S04_SCHEMA_INVALID")
    variant = value.get("variant")
    _require(variant in VARIANTS, "M4C_S04_VARIANT_INVALID")
    interrupt = value.get("interrupt")
    _require(type(interrupt) is dict, "M4C_S04_INTERRUPT_MISSING")
    _require(interrupt.get("operation") == variant,
             "M4C_S04_INTERRUPT_OPERATION_INVALID")
    expected_states = {variant} if variant != "ACTION" else {"THINK", "ACTION"}
    _require(interrupt.get("state") in expected_states,
             "M4C_S04_INTERRUPT_STATE_INVALID")
    _require(interrupt.get("operation_active") is True,
             "M4C_S04_OPERATION_NOT_ACTIVE")
    _require(interrupt.get("main_text") == "已中止",
             "M4C_S04_INTERRUPT_DISPLAY_MISSING")
    _require(value.get("affected_success_count") == 0,
             "M4C_S04_OLD_SUCCESS_PUBLISHED")
    _require(value.get("post_interrupt_start_count") == 0,
             "M4C_S04_LATE_OPERATION_STARTED")
    _require(value.get("unexpected_error_count") == 0,
             "M4C_S04_SYSTEM_FAULT_FABRICATED")

    cleanup = value.get("cleanup")
    _require(type(cleanup) is dict, "M4C_S04_CLEANUP_MISSING")
    _require(cleanup.get("state") == "IDLE",
             "M4C_S04_FINAL_STATE_INVALID")
    _require(cleanup.get("main_empty") is True,
             "M4C_S04_FINAL_MAIN_NOT_EMPTY")
    _require(cleanup.get("affected_owner_idle") is True,
             "M4C_S04_AFFECTED_OWNER_NOT_IDLE")

    return {
        "schema_version": 1,
        "scenario_code": f"M4C-PI-S04/{variant}",
        "interrupt_state_code": interrupt["state"],
        "affected_operation_code": variant,
        "operation_active_at_interrupt": True,
        "interrupt_main_shown": True,
        "affected_success_count": 0,
        "post_interrupt_start_count": 0,
        "system_fault_count": 0,
        "affected_owner_idle": True,
        "terminal_state_code": "IDLE",
        "main_empty": True,
    }


__all__ = ["S04OracleError", "VARIANTS", "validate_s04_private_evidence"]
