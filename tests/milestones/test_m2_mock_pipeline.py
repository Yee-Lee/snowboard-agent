"""M2 Mock Pipeline milestone entrypoint.

The entrypoint refuses to report a green milestone while any signed-off M2
Test ID lacks executable pytest evidence. Running with ``--collect-only`` is
the WP-M2-01 scaffold check; the normal command becomes green only after all
M2 work packages have populated ``tests.m2_manifest``.
"""

from __future__ import annotations

import subprocess
import sys

from tests.m2_manifest import M2_TEST_FILES, incomplete_test_ids, traced_nodes


def test_m2_mock_pipeline_milestone_suite() -> None:
    """Run every explicitly traced M2 test without wildcard re-export."""
    incomplete = incomplete_test_ids()
    assert not incomplete, (
        "M2 implementation is incomplete; incomplete pytest evidence for: "
        + ", ".join(incomplete)
    )

    nodes = traced_nodes()
    assert nodes, "M2 manifest must contain executable pytest nodes"
    assert len(nodes) == len(set(nodes)), (
        "M2 manifest contains duplicate pytest nodes"
    )
    assert all(
        any(node.startswith(f"{test_file}::") for test_file in M2_TEST_FILES)
        for node in nodes
    ), "every traced node must belong to an explicit M2 test file"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *nodes],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"M2 Mock Pipeline suite failed:\n{result.stdout}\n{result.stderr}"
    )
