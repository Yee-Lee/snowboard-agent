"""Tests for M1-REG-001: M1 pure software regression guard.

Verifies that M1 tests and codebase:
1. Do not import Pi-only or concrete hardware dependencies (sounddevice, picamera2, gpiod, LiteRT-LM).
2. Registered 'rpi' marker correctly.
3. Does not import Ch 7 external-message or Ch 9 concrete payload validator modules.
"""

from __future__ import annotations

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
    forbidden_concrete = [
        "sbd.input_events.external_message.buffer",
        "sbd.action.payload_validator",
    ]
    for mod in forbidden_concrete:
        assert mod not in sys.modules, f"Forbidden M2 concrete module '{mod}' was imported into sys.modules"


def test_reg_001_rpi_marker_registered(pytestconfig):
    markers = pytestconfig.getini("markers")
    has_rpi = any("rpi" in m for m in markers)
    assert has_rpi, "rpi marker must be registered in pytest config"
