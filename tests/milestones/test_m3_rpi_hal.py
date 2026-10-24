"""M3 Raspberry Pi HAL milestone entrypoint.

This entrypoint becomes green only when every approved M3 requirement has
real executable product assertions.  The W0 inventory guard is deliberately
kept outside this command so a scaffold cannot be mistaken for M3 acceptance.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from tests.m3_manifest import (
    M3_TEST_RECORDS,
    blocked_test_ids,
    implemented_nodes_for,
    pending_test_ids,
)
from tests.rpi_support import validate_evidence_bundle


def test_m3_rpi_hal_milestone_suite() -> None:
    """Run every available portable M3 assertion; Blocked IDs stay explicit."""
    pending = pending_test_ids()
    assert not pending, (
        "M3 implementation has undispositioned Pending requirements: "
        + ", ".join(pending)
    )
    nodes = implemented_nodes_for("DEV-PY311")
    assert nodes
    assert len(nodes) == len(set(nodes))

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *nodes],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"M3 Raspberry Pi HAL suite failed:\n{result.stdout}\n{result.stderr}"


@pytest.mark.rpi
def test_m3_rpi_hardware_acceptance_gate() -> None:
    """Never report target-device acceptance while hardware IDs are Blocked."""
    blocked = blocked_test_ids()
    assert not blocked, "M3 RPi acceptance is Blocked: " + ", ".join(blocked)
    nodes = implemented_nodes_for("RPI-NATIVE")
    assert len(nodes) == 20
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-m", "rpi", "-q", *nodes],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"M3 RPi suite failed:\n{result.stdout}\n{result.stderr}"
    expected_ids = (
        record.test_id for record in M3_TEST_RECORDS
        if record.platform == "RPI-NATIVE"
    )
    validate_evidence_bundle(expected_ids)
