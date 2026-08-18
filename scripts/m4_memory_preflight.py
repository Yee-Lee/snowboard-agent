#!/usr/bin/env python3
"""Run one M4 target smoke command under a lightweight memory preflight."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


KIB_PER_MIB = 1024
DEFAULT_MAX_SYSTEM_USED_MIB = 3584


class PreflightError(RuntimeError):
    """The preflight could not execute or reconcile its child process."""


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    mem_total_kib: int
    mem_available_kib: int
    swap_used_kib: int
    pswpin: int
    pswpout: int
    pressure_full_total_us: int | None
    oom_kill: int | None

    @property
    def system_used_kib(self) -> int:
        return self.mem_total_kib - self.mem_available_kib


@dataclass(frozen=True, slots=True)
class ProcessUsage:
    pids: tuple[int, ...] = ()
    pss_kib: int = 0
    rss_kib: int = 0


@dataclass(frozen=True, slots=True)
class Sample:
    system: SystemSnapshot
    processes: ProcessUsage = ProcessUsage()


def _read_fields(path: Path, separator: str | None = None) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split(separator, 1) if separator else line.split(None, 1)
        if len(parts) != 2:
            continue
        key, raw = parts
        token = raw.strip().split()[0]
        try:
            values[key.rstrip(":")] = int(token)
        except ValueError:
            continue
    return values


def _pressure_full_total(path: Path) -> int | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("full "):
                for field in line.split()[1:]:
                    if field.startswith("total="):
                        return int(field.removeprefix("total="))
    except (OSError, ValueError):
        return None
    return None


def _current_cgroup_memory_events(proc_root: Path, cgroup_root: Path) -> dict[str, int]:
    try:
        unified = next(
            line.split("::", 1)[1]
            for line in (proc_root / "self/cgroup").read_text(encoding="utf-8").splitlines()
            if line.startswith("0::")
        )
        path = cgroup_root / unified.lstrip("/") / "memory.events"
        return _read_fields(path)
    except (OSError, StopIteration):
        return {}


def take_system_snapshot(
    proc_root: Path = Path("/proc"),
    cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> SystemSnapshot:
    try:
        memory = _read_fields(proc_root / "meminfo", ":")
        vmstat = _read_fields(proc_root / "vmstat")
    except OSError as error:
        raise PreflightError(f"cannot read system memory counters: {error}") from error
    required = ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")
    missing = [key for key in required if key not in memory]
    if missing:
        raise PreflightError("missing /proc/meminfo fields: " + ", ".join(missing))
    events = _current_cgroup_memory_events(proc_root, cgroup_root)
    return SystemSnapshot(
        mem_total_kib=memory["MemTotal"],
        mem_available_kib=memory["MemAvailable"],
        swap_used_kib=memory["SwapTotal"] - memory["SwapFree"],
        pswpin=vmstat.get("pswpin", 0),
        pswpout=vmstat.get("pswpout", 0),
        pressure_full_total_us=_pressure_full_total(proc_root / "pressure/memory"),
        oom_kill=events.get("oom_kill"),
    )


def process_group_pids(pgid: int, proc_root: Path = Path("/proc")) -> tuple[int, ...]:
    pids: list[int] = []
    try:
        entries = tuple(proc_root.iterdir())
    except OSError:
        return ()
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            tail = stat[stat.rfind(")") + 1 :].split()
            if len(tail) >= 3 and int(tail[2]) == pgid:
                pids.append(int(entry.name))
        except (OSError, ValueError):
            continue
    return tuple(sorted(pids))


def sample_process_group(pgid: int, proc_root: Path = Path("/proc")) -> ProcessUsage:
    pids = process_group_pids(pgid, proc_root)
    pss_kib = 0
    rss_kib = 0
    visible: list[int] = []
    for pid in pids:
        try:
            rollup = _read_fields(proc_root / str(pid) / "smaps_rollup", ":")
        except OSError:
            continue
        visible.append(pid)
        pss_kib += rollup.get("Pss", 0)
        rss_kib += rollup.get("Rss", 0)
    return ProcessUsage(tuple(visible), pss_kib, rss_kib)


def evaluate(
    samples: Sequence[Sample],
    initial: SystemSnapshot,
    final: SystemSnapshot,
    *,
    max_system_used_mib: int,
    command_exit_code: int,
    timed_out: bool,
    post_exit_pids: Sequence[int],
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if timed_out:
        reasons.append("smoke command timed out")
    elif command_exit_code != 0:
        reasons.append(f"smoke command exited {command_exit_code}")
    if post_exit_pids:
        reasons.append("process group remained after smoke command: " + ",".join(map(str, post_exit_pids)))

    observed = [initial, *(sample.system for sample in samples), final]
    limit_kib = max_system_used_mib * KIB_PER_MIB
    if max(snapshot.system_used_kib for snapshot in observed) > limit_kib:
        reasons.append(f"system used memory exceeded {max_system_used_mib} MiB")
    if any(snapshot.swap_used_kib != 0 for snapshot in observed):
        reasons.append("swap usage was nonzero")
    if final.pswpin > initial.pswpin or final.pswpout > initial.pswpout:
        reasons.append("swap-in or swap-out activity increased")
    if (
        initial.pressure_full_total_us is not None
        and final.pressure_full_total_us is not None
        and final.pressure_full_total_us > initial.pressure_full_total_us
    ):
        reasons.append("full memory-pressure stall increased")
    if initial.oom_kill is not None and final.oom_kill is not None and final.oom_kill > initial.oom_kill:
        reasons.append("cgroup OOM kill count increased")
    return ("PREFLIGHT_RISK", tuple(reasons)) if reasons else ("PREFLIGHT_OK", ())


def _terminate_group(pgid: int, grace_seconds: float) -> tuple[int, ...]:
    survivors = process_group_pids(pgid)
    if not survivors:
        return ()
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return ()
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        survivors = process_group_pids(pgid)
        if not survivors:
            return ()
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return ()
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        survivors = process_group_pids(pgid)
        if not survivors:
            return ()
        time.sleep(0.05)
    return process_group_pids(pgid)


def run_preflight(args: argparse.Namespace) -> dict[str, object]:
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise PreflightError("a smoke command is required after --")
    if (
        args.max_system_used_mib <= 0
        or args.sample_interval_ms <= 0
        or args.timeout_seconds <= 0
        or args.terminate_grace_seconds <= 0
    ):
        raise PreflightError("memory limit, sample interval, timeout and cleanup grace must be greater than zero")

    initial = take_system_snapshot()
    process = subprocess.Popen(command, start_new_session=True)
    pgid = process.pid
    samples: list[Sample] = []
    timed_out = False
    deadline = time.monotonic() + args.timeout_seconds
    while process.poll() is None:
        samples.append(Sample(take_system_snapshot(), sample_process_group(pgid)))
        if time.monotonic() >= deadline:
            timed_out = True
            break
        time.sleep(args.sample_interval_ms / 1000)

    if timed_out:
        _terminate_group(pgid, args.terminate_grace_seconds)
    command_exit_code = process.wait()
    post_exit_pids = process_group_pids(pgid)
    unreconciled_pids = _terminate_group(pgid, args.terminate_grace_seconds) if post_exit_pids else ()
    final = take_system_snapshot()
    status, reasons = evaluate(
        samples,
        initial,
        final,
        max_system_used_mib=args.max_system_used_mib,
        command_exit_code=command_exit_code,
        timed_out=timed_out,
        post_exit_pids=post_exit_pids,
    )
    if unreconciled_pids:
        status = "PREFLIGHT_RISK"
        reasons = (*reasons, "cleanup could not terminate process group: " + ",".join(map(str, unreconciled_pids)))

    systems = [initial, *(sample.system for sample in samples), final]
    processes = [sample.processes for sample in samples]
    return {
        "status": status,
        "reasons": list(reasons),
        "command": command,
        "command_exit_code": command_exit_code,
        "timed_out": timed_out,
        "sample_count": len(samples),
        "max_system_used_mib": args.max_system_used_mib,
        "minimum_memavailable_mib": round(min(item.mem_available_kib for item in systems) / KIB_PER_MIB, 3),
        "peak_system_used_mib": round(max(item.system_used_kib for item in systems) / KIB_PER_MIB, 3),
        "peak_process_pss_mib": round(max((item.pss_kib for item in processes), default=0) / KIB_PER_MIB, 3),
        "peak_process_rss_mib": round(max((item.rss_kib for item in processes), default=0) / KIB_PER_MIB, 3),
        "initial": asdict(initial),
        "final": asdict(final),
        "post_exit_pids": list(post_exit_pids),
        "cleanup_unreconciled_pids": list(unreconciled_pids),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-system-used-mib", type=int, default=DEFAULT_MAX_SYSTEM_USED_MIB)
    parser.add_argument("--sample-interval-ms", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--terminate-grace-seconds", type=float, default=3)
    parser.add_argument("--output", type=Path, help="optional debug JSON; stdout is always emitted")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_preflight(args)
    except (OSError, PreflightError) as error:
        print(f"memory preflight error: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    return 0 if result["status"] == "PREFLIGHT_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
