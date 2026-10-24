"""Tests for M1-REG-001: M1 pure software regression guard.

Verifies that M1 tests and codebase:
1. Do not import Pi-only or concrete hardware dependencies (sounddevice, picamera2, gpiod, LiteRT-LM).
2. Registered 'rpi' marker correctly.
3. Importing M1 surfaces does not import Ch 7 external-message or Ch 9 payload validator modules.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_reg_001_no_pi_only_dependencies_imported():
    forbidden_modules = [
        "sounddevice",
        "picamera2",
        "gpiod",
        "LiteRT_LM",
        "litert_lm",
    ]
    for mod in forbidden_modules:
        assert mod not in sys.modules, f"Forbidden Pi-only module '{mod}' was imported into sys.modules"


def test_reg_001_no_m2_concrete_modules_imported():
    """Importing only M1 surfaces in a clean process must not load M2 code."""
    forbidden_concrete = (
        "sbd.input_events.external_message.buffer",
        "sbd.action.payload_validator",
    )
    script = "\n".join((
        "import sys",
        "import sbd.main",
        "import sbd.core.resource_manager.catalog",
        f"forbidden = {forbidden_concrete!r}",
        "loaded = [name for name in forbidden if name in sys.modules]",
        "print('\\n'.join(loaded))",
        "raise SystemExit(bool(loaded))",
    ))
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "M1 import surface loaded M2 concrete modules:\n" + result.stdout
    )


def test_reg_001_rpi_marker_registered(pytestconfig):
    markers = pytestconfig.getini("markers")
    has_rpi = any("rpi" in m for m in markers)
    assert has_rpi, "rpi marker must be registered in pytest config"
