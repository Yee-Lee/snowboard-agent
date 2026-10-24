"""M3-REG-001 test inventory guardrails."""

from __future__ import annotations

import json

import pytest

from tests import rpi_support
from tests.m3_manifest import (
    M3_TEST_RECORDS,
    blocked_test_ids,
    implemented_nodes,
    pending_test_ids,
)


def test_m3_reg_001(monkeypatch, tmp_path) -> None:
    """M3-REG-001: inventory stays complete while implementation is in progress."""
    ids = [record.test_id for record in M3_TEST_RECORDS]
    assert len(ids) == 47
    assert len(ids) == len(set(ids))
    assert all(record.planned_node and "::test_m3_" in record.planned_node for record in M3_TEST_RECORDS)
    assert sum(record.platform == "DEV-PY311" for record in M3_TEST_RECORDS) == 27
    assert sum(record.platform == "RPI-NATIVE" for record in M3_TEST_RECORDS) == 20
    assert len(implemented_nodes()) == 47
    assert len(blocked_test_ids()) == 0
    assert pending_test_ids() == ()

    revision = "a" * 40
    monkeypatch.setenv("SBD_M3_CANDIDATE_SHA", revision)

    def clean_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return revision
        if args[:2] == ("rev-parse", "--abbrev-ref"):
            return "m3-candidate"
        if args[:2] == ("status", "--porcelain"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(rpi_support, "_git", clean_git)
    assert rpi_support.candidate_identity() == {
        "branch": "m3-candidate", "implementation_sha": revision,
    }

    hardware = tmp_path / "hardware.json"
    hardware.write_text(json.dumps({
        "pi": "fixture Pi", "peripherals": {"fixture": "mock"},
        "wiring": "fixture wiring", "operator": "fixture operator",
    }))
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setenv("SBD_M3_RPI_CONFIG", "config.example.yaml")
    monkeypatch.setenv("SBD_M3_EVIDENCE_DIR", str(evidence))
    monkeypatch.setenv("SBD_M3_HARDWARE_MANIFEST", str(hardware))
    rpi_support._CARD_STARTED["M3-REG-FIXTURE"] = rpi_support._utc_now()
    rpi_support.record_result(
        "M3-REG-FIXTURE",
        expected="schema fixture passes",
        actual="schema fixture passed",
        fixture={"name": "schema", "sha256": "inline"},
    )
    rpi_support.validate_evidence_bundle(("M3-REG-FIXTURE",))
    result = json.loads((evidence / "results/M3-REG-FIXTURE.json").read_text())
    assert result["status"] == "Pass"
    assert result["product_revision"]["implementation_sha"] == revision
    assert len(result["fixture"]["sha256"]) == 64
    assert (evidence / "cards/M3-REG-FIXTURE.md").is_file()
    assert (evidence / "checksums/SHA256SUMS").is_file()
    assert (evidence / "environment/system.json").is_file()
    assert (evidence / "manifest.json").is_file()

    def dirty_git(*args: str) -> str:
        if args[:2] == ("status", "--porcelain"):
            return " M src/sbd/core/audio/alsa/input.py"
        return clean_git(*args)

    monkeypatch.setattr(rpi_support, "_git", dirty_git)
    with pytest.raises(AssertionError, match="worktree is dirty"):
        rpi_support.candidate_identity()
