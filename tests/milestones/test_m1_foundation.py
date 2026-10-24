"""M1 Foundation milestone entrypoint.

Running this file executes every M1 test specified in test_spec_M1.md:
    python -m pytest -v tests/milestones/test_m1_foundation.py
"""

import subprocess
import sys

M1_TEST_FILES = [
    "tests/test_events.py",
    "tests/test_contracts.py",
    "tests/test_event_bus.py",
    "tests/test_state_manager.py",
    "tests/test_resource_manager.py",
    "tests/test_convergence.py",
    "tests/test_config.py",
    "tests/test_logging.py",
    "tests/test_bootstrap.py",
    "tests/test_regression_guard.py",
]


def test_m1_foundation_milestone_suite() -> None:
    """M1 milestone foundation test suite entrypoint runner."""
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *M1_TEST_FILES],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"M1 Foundation suite failed:\n{res.stdout}\n{res.stderr}"

