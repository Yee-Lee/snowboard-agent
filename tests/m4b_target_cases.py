"""Explicit target measurement entry; no release/human PASS cards are inferred."""
import json
import os
import pytest
from scripts.m4b_llm_product import ProductFailure
from scripts.m4b_target_metrics import TARGET_IDS

pytestmark = pytest.mark.rpi


def require_native_scenario_binding() -> list[str]:
    try:
        args = json.loads(os.environ["M4B_MEASUREMENT_ARGS"])
        if type(args) is not list or not args or any(type(value) is not str for value in args):
            raise ValueError
        return args
    except Exception:
        raise ProductFailure("M4B_MEASUREMENT_INPUTS_MISSING") from None


def test_m4b_exact_product_gate3_cards() -> None:
    # Retain the importing suite's entry point. A successful lab run returns
    # Measured, never PASS for the independent seven Pi/human acceptance IDs.
    from scripts.m4b_measurement import main
    assert main(require_native_scenario_binding()) == 0
