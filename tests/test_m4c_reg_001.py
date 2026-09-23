"""M4C-REG-001 — affected catalog and anti-weakening checks."""
from __future__ import annotations

from pathlib import Path

from scripts.candidate_gate import m4b_source_violations
from sbd.action.speak import StreamingSpeakControl
from sbd.core.audio import VolumeControlledAudioOutput
from sbd.core.config.models import AudioOutputConfig
from sbd.core.state_manager.session import SessionContext

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tests/m4c_portable_suite.txt"


def test_m4c_reg_001_g01_affected_sources_have_no_weakening_controls() -> None:
    affected = [
        *ROOT.joinpath("tests").glob("test_m4c_*.py"),
        ROOT / "src/sbd/action/speak/streaming.py",
        ROOT / "src/sbd/core/audio/volume.py",
        ROOT / "src/sbd/cognition/reasoner.py",
        ROOT / "src/sbd/core/state_manager/manager.py",
    ]
    violations = []
    for path in affected:
        violations.extend(
            (str(path.relative_to(ROOT)), line, reason)
            for line, reason in m4b_source_violations(path.read_text(encoding="utf-8"))
        )
    assert violations == []


def test_m4c_reg_001_g02_catalog_is_exact_existing_and_unique() -> None:
    entries = CATALOG.read_text(encoding="utf-8").splitlines()
    assert entries
    assert len(entries) == len(set(entries))
    assert entries[:6] == [
        "tests/test_m4c_vol_001.py",
        "tests/test_m4c_ss_ctrl_001.py",
        "tests/test_m4c_ss_extract_001.py",
        "tests/test_m4c_ss_outcome_001.py",
        "tests/test_m4c_noinput_001.py",
        "tests/test_m4c_reg_001.py",
    ]
    assert all((ROOT / entry).is_file() for entry in entries)


def test_m4c_reg_001_g03_product_symbols_are_single_importable_types() -> None:
    assert VolumeControlledAudioOutput.__module__ == "sbd.core.audio.volume"
    assert StreamingSpeakControl.__module__ == "sbd.action.speak.streaming"


def test_m4c_reg_001_g04_pure_python_import_defaults() -> None:
    assert AudioOutputConfig().volume_percent == 100
    assert SessionContext("session", "button").no_input_streak == 0
