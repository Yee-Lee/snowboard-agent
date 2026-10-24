from __future__ import annotations

from scripts.m4_memory_preflight import ProcessUsage, Sample, SystemSnapshot, evaluate


def snapshot(
    *,
    available_mib: int = 1024,
    swap_used_mib: int = 0,
    pswpin: int = 0,
    pswpout: int = 0,
    pressure: int | None = 10,
    oom_kill: int | None = 0,
) -> SystemSnapshot:
    return SystemSnapshot(
        mem_total_kib=4096 * 1024,
        mem_available_kib=available_mib * 1024,
        swap_used_kib=swap_used_mib * 1024,
        pswpin=pswpin,
        pswpout=pswpout,
        pressure_full_total_us=pressure,
        oom_kill=oom_kill,
    )


def decision(
    samples: list[Sample],
    *,
    initial: SystemSnapshot | None = None,
    final: SystemSnapshot | None = None,
    exit_code: int = 0,
    timed_out: bool = False,
    survivors: tuple[int, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    baseline = initial or snapshot()
    return evaluate(
        samples,
        baseline,
        final or baseline,
        max_system_used_mib=3584,
        command_exit_code=exit_code,
        timed_out=timed_out,
        post_exit_pids=survivors,
    )


def test_capacity_uses_system_memavailable_not_summed_rss() -> None:
    # Large summed RSS may double-count shared pages. It is diagnostic and cannot fail capacity.
    sample = Sample(snapshot(available_mib=700), ProcessUsage((101, 102), pss_kib=3500 * 1024, rss_kib=6000 * 1024))
    status, reasons = decision([sample])
    assert status == "PREFLIGHT_OK"
    assert reasons == ()


def test_memory_pressure_or_swap_activity_reports_risk() -> None:
    initial = snapshot(pressure=10, pswpin=3)
    final = snapshot(pressure=11, pswpin=4)
    status, reasons = decision([Sample(final)], initial=initial, final=final)
    assert status == "PREFLIGHT_RISK"
    assert "full memory-pressure stall increased" in reasons
    assert "swap-in or swap-out activity increased" in reasons


def test_cleanup_survivor_reports_risk() -> None:
    status, reasons = decision([], survivors=(314, 315))
    assert status == "PREFLIGHT_RISK"
    assert "process group remained after smoke command: 314,315" in reasons


def test_system_used_limit_is_memtotal_minus_memavailable() -> None:
    status, reasons = decision([Sample(snapshot(available_mib=500))])
    assert status == "PREFLIGHT_RISK"
    assert "system used memory exceeded 3584 MiB" in reasons
