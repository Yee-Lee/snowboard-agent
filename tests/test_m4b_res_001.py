"""M4B resource acquisition, measurement and deterministic estimate coverage."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from scripts.m4b_target_metrics import (
    MetricsError,
    kernel_resource_sample,
    owner_resource_accounting,
    process_group_members,
    MeasurementHarness, MeasurementPoint, derive_thresholds, validate_authorization, MIB,
)
from tests.test_m4b_mem_001 import sample


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
        "swap_total_mib": 1,
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


def authorization():
    identity = dict(schema_version=1, harness_sha256="a" * 64, candidate_sha="b" * 40,
        profile_sha256="c" * 64, target_identity="pi5-4gb-debian13-aarch64-cp3135")
    return identity, {"authorized_tuple": identity, "approvals": [
        dict(role=role, reviewer=f"reviewer-{role}", approved_at="2026-09-12T12:00:00+08:00",
             decision="Approved", authorized_tuple=dict(identity)) for role in ("Designer", "Tester")]}


def series():
    labels = ["engine_ready", "conversation_preparation", "conversation_ready", "pre_generate",
        "post_generate", "sample", "pre_speak", "sample", "audio_completion", "primary_completion",
        "pre_replacement", "post_replacement", "post_session_close"]
    available = [1000 * MIB] * len(labels)
    available[5], available[7] = 1000 * MIB - 10 * MIB - 1, 1000 * MIB - 3 * MIB
    return [MeasurementPoint(label, 0, replace(sample(stamp=i + 1),
        mem_total_bytes=2000 * MIB, mem_available_bytes=available[i])) for i, label in enumerate(labels)]


def test_measurement_formula_uses_raw_minimum_rounding_and_complete_action_window():
    assert derive_thresholds(series(), completed=True, cleanup_proven=True) == {
        "speak_drop_bytes": 3 * MIB, "generate_drop_bytes": 10 * MIB + 1,
        "min_mem_available_speak_bytes": 515 * MIB,
        "min_mem_available_generate_bytes": 523 * MIB}
    for rows in (series()[:-1], [p for p in series() if p.lifecycle_point != "primary_completion"],
                 [p for p in series() if p.lifecycle_point != "pre_replacement"]):
        with pytest.raises(MetricsError):
            derive_thresholds(rows, completed=True, cleanup_proven=True)
    for complete, cleanup in ((False, True), (True, False)):
        with pytest.raises(MetricsError):
            derive_thresholds(series(), completed=complete, cleanup_proven=cleanup)


def test_dual_role_authorization_binds_exact_digest_tuple_and_timezone():
    expected, value = authorization()
    assert validate_authorization(value, expected) == expected
    for mutation in (
        lambda v: v["approvals"].pop(),
        lambda v: v["approvals"][0].update(decision="Pending"),
        lambda v: v["approvals"][0]["authorized_tuple"].update(candidate_sha="d" * 40),
        lambda v: v["approvals"][0].update(approved_at="2026-09-12T12:00:00"),
    ):
        expected, value = authorization()
        mutation(value)
        with pytest.raises(MetricsError):
            validate_authorization(value, expected)


@pytest.mark.asyncio
async def test_measurement_harness_executes_injected_operations_and_always_cleans_up():
    expected, auth = authorization()
    observations = iter(series())
    ledger = []
    async def cleanup():
        ledger.append("cleanup")
        return True
    harness = MeasurementHarness(authorization=auth, expected_tuple=expected,
        sample=lambda: next(observations).sample, cleanup=cleanup)
    async def scenario(h):
        for row in series():
            h.capture(row.lifecycle_point, row.operation_index)
    result = await harness.run(scenario)
    assert result["status"] == "Measured" and ledger == ["cleanup"]
    assert result["derived"]["min_mem_available_generate_bytes"] == 523 * MIB
    assert result["authorized_tuple"] == expected


@pytest.mark.asyncio
async def test_measurement_safety_floor_prevents_operation_and_derivation():
    expected, auth = authorization()
    ledger = []
    async def cleanup():
        ledger.append("cleanup")
        return True
    async def execute():
        ledger.append("FORBIDDEN_GENERATE")
    harness = MeasurementHarness(authorization=auth, expected_tuple=expected,
        sample=lambda: sample(), cleanup=cleanup)
    async def scenario(h):
        await h.operation(before="pre_generate", after="post_generate", index=0, execute=execute)
    with pytest.raises(MetricsError, match="STOPPED"):
        await harness.run(scenario)
    assert ledger == ["cleanup"] and harness.stopped and not harness.completed
