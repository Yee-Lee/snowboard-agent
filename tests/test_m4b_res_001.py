"""M4B-RES-001 — frozen r14 formula regression."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.m4b_target_metrics import (
    MetricsError,
    kernel_resource_sample,
    load_gate3_catalog,
    owner_resource_accounting,
    process_group_members,
    verify_r14_vector,
)


VECTOR = Path(__file__).parent.parent / "requirements/m4b/r14-sanitized-vector.json"


def test_m4b_res_001_frozen_vector_reproduces_attempt_006_outputs() -> None:
    actual = verify_r14_vector(json.loads(VECTOR.read_text(encoding="utf-8")))
    assert actual == pytest.approx({
        "combined_pss_slope_mib_per_session": 5.900893,
        "combined_pss_late_minus_early_median_delta_mib": 131.578,
        "system_used_slope_mib_per_session": 0.101957,
        "system_used_late_minus_early_median_delta_mib": 32.750,
    }, abs=1e-6)


def test_m4b_res_001_rejects_missing_sample_instead_of_resegmenting() -> None:
    value = json.loads(VECTOR.read_text(encoding="utf-8"))
    value["combined_pss_mib"].pop()
    with pytest.raises(MetricsError, match="20"):
        verify_r14_vector(value)


def test_m4b_res_001_gate3_catalog_identity_and_three_generic_intents() -> None:
    catalog = load_gate3_catalog(VECTOR.with_name("gate3-product-catalog.json"))
    assert catalog["resource_marker_profile"]["session_count"] == 20
    assert [case["expected_kind"] for case in catalog["intent_cases"]] == [
        "speak", "tool", "rest",
    ]


def test_m4b_res_001_kernel_sample_uses_real_swap_oom_thermal_throttle_fields() -> None:
    actual = kernel_resource_sample(
        "MemTotal: 4194304 kB\nMemAvailable: 2097152 kB\n"
        "SwapTotal: 1024 kB\nSwapFree: 1024 kB\n",
        "pswpin 0\noom_kill 7\n",
        "55000\n",
        "throttled=0x0\n",
    )
    assert actual == {
        "mem_total_mib": 4096,
        "mem_available_mib": 2048,
        "system_used_mib": 2048,
        "swap_used_mib": 0,
        "oom_kill": 7,
        "thermal_celsius": 55,
        "throttled_bits": 0,
    }


@pytest.mark.parametrize(("vmstat", "thermal", "throttled"), [
    ("pswpin 0\n", "55000", "throttled=0x0"),
    ("oom_kill 0\n", "unknown", "throttled=0x0"),
    ("oom_kill 0\n", "55000", "unavailable"),
])
def test_m4b_res_001_kernel_sample_rejects_missing_or_fabricated_counter(
    vmstat: str, thermal: str, throttled: str,
) -> None:
    meminfo = "MemTotal: 4096 kB\nMemAvailable: 2048 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n"
    with pytest.raises(MetricsError):
        kernel_resource_sample(meminfo, vmstat, thermal, throttled)


def _proc(root: Path, pid: int, ppid: int, pgid: int, pss: int) -> None:
    target = root / str(pid)
    target.mkdir(parents=True)
    tail = [
        "S", str(ppid), str(pgid), "0", "0", "0", "0", "0", "0", "0", "0",
        "10", "5", "0", "0", "0", "0", "2",
    ]
    (target / "stat").write_text(f"{pid} (owner {pid}) " + " ".join(tail), encoding="ascii")
    (target / "smaps_rollup").write_text(
        f"Rss: {pss * 2} kB\nPss: {pss} kB\n", encoding="ascii",
    )


def test_m4b_res_001_owner_accounting_is_unique_pid_pss_rss_cpu_thread(
    tmp_path: Path,
) -> None:
    owners = {name: {100 + index} for index, name in enumerate(("core", "vad", "asr", "tts", "llm"))}
    for index, pids in enumerate(owners.values(), 1):
        _proc(tmp_path, next(iter(pids)), 1, 77, index * 1024)
    actual = owner_resource_accounting(owners, proc_root=tmp_path, clock_ticks=100)
    assert actual["combined_pss_mib"] == 15
    assert actual["unique_pid_count"] == 5
    assert actual["llm"] == {
        "pids": [104], "pss_mib": 5, "rss_mib": 10,
        "cpu_seconds": 0.15, "threads": 2,
    }
    assert process_group_members(77, tmp_path) == {100, 101, 102, 103, 104}


def test_m4b_res_001_owner_accounting_rejects_pid_overlap(tmp_path: Path) -> None:
    _proc(tmp_path, 100, 1, 77, 1024)
    owners = {name: {100} for name in ("core", "vad", "asr", "tts", "llm")}
    with pytest.raises(MetricsError, match="overlap"):
        owner_resource_accounting(owners, proc_root=tmp_path, clock_ticks=100)
