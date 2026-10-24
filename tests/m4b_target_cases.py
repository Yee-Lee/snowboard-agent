"""Explicit target entry for the canonical single-PV runner."""
import importlib.util
import json
import os
from pathlib import Path
import pytest
from scripts.m4b_llm_product import ProductFailure
from scripts.m4b_target_metrics import TARGET_IDS

pytestmark = pytest.mark.rpi


def require_pv_binding() -> list[str]:
    try:
        args = json.loads(os.environ["M4B_PV_ARGS"])
        if type(args) is not list or not args or any(type(value) is not str for value in args):
            raise ValueError
        return args
    except Exception:
        raise ProductFailure("M4B_PV_INPUTS_MISSING") from None


def test_m4b_exact_product_gate3_cards() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts/run-m4b-pv.py"
    spec = importlib.util.spec_from_file_location("m4b_pv_target", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(require_pv_binding()) == 0
