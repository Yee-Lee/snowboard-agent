"""M4A-RES-001 — system memory and process-tree collector support."""

from __future__ import annotations

import pytest

from scripts.m4a_target_metrics import MetricsError, descendants, system_used_mib


def test_m4a_res_001_uses_memtotal_minus_memavailable_not_process_rss() -> None:
    snapshot = "MemTotal: 4194304 kB\nMemAvailable: 1048576 kB\n"
    assert system_used_mib(snapshot) == 3072


@pytest.mark.parametrize(
    "snapshot",
    [
        "MemTotal: 4194304 kB\n",
        "MemAvailable: 4194304 kB\n",
        "MemTotal: value kB\nMemAvailable: 1 kB\n",
        "MemTotal: 1 kB\nMemAvailable: 2 kB\n",
    ],
)
def test_m4a_res_001_rejects_malformed_memory_snapshot(snapshot: str) -> None:
    with pytest.raises(MetricsError):
        system_used_mib(snapshot)


def test_m4a_res_001_descendant_closure_includes_nested_native_worker() -> None:
    parents = {101: 100, 102: 101, 103: 102, 200: 1}
    assert descendants(parents, 100) == {101, 102, 103}
