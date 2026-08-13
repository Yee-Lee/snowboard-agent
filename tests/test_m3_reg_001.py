"""M3-REG-001 test inventory guardrails."""

from __future__ import annotations

from tests.m3_manifest import (
    M3_TEST_RECORDS,
    blocked_test_ids,
    implemented_nodes,
    pending_test_ids,
)


def test_m3_reg_001() -> None:
    """M3-REG-001: inventory stays complete while implementation is in progress."""
    ids = [record.test_id for record in M3_TEST_RECORDS]
    assert len(ids) == 47
    assert len(ids) == len(set(ids))
    assert all(record.planned_node and "::test_m3_" in record.planned_node for record in M3_TEST_RECORDS)
    assert sum(record.platform == "DEV-PY311" for record in M3_TEST_RECORDS) == 27
    assert sum(record.platform == "RPI-NATIVE" for record in M3_TEST_RECORDS) == 20
    assert len(implemented_nodes()) == 24
    assert len(blocked_test_ids()) == 23
    assert pending_test_ids() == ()
