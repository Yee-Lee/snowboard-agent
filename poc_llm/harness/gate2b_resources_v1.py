"""Continuous process-tree, memory, thermal and PSI sampling for Gate 2B."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Callable


def _proc_table() -> dict[int, int]:
    table: dict[int, int] = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            text = path.read_text(encoding="utf-8")
            tail = text[text.rfind(")") + 2 :].split()
            table[int(path.parent.name)] = int(tail[1])
        except (OSError, ValueError, IndexError):
            continue
    return table


def process_tree(root: int, table: dict[int, int]) -> set[int]:
    members = {root}
    changed = True
    while changed:
        changed = False
        for pid, parent in table.items():
            if parent in members and pid not in members:
                members.add(pid)
                changed = True
    return members


def _process_values(pid: int) -> dict[str, int] | None:
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
        fields = {
            line.split(":", 1)[0]: int(line.split()[1])
            for line in status.splitlines()
            if line.startswith(("VmRSS:", "Threads:"))
        }
        pss_kib = 0
        rollup = Path(f"/proc/{pid}/smaps_rollup")
        if rollup.is_file():
            for line in rollup.read_text(encoding="utf-8").splitlines():
                if line.startswith("Pss:"):
                    pss_kib = int(line.split()[1])
                    break
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        tail = text[text.rfind(")") + 2 :].split()
        cpu_ticks = int(tail[11]) + int(tail[12])
    except (OSError, ValueError, IndexError):
        return None
    return {
        "rss_kib": fields.get("VmRSS", 0),
        "pss_kib": pss_kib,
        "threads": fields.get("Threads", 0),
        "cpu_ticks": cpu_ticks,
    }


def _meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:")):
            key, rest = line.split(":", 1)
            values[key] = int(rest.split()[0])
    return values


def _psi_full_total() -> int:
    path = Path("/proc/pressure/memory")
    if not path.is_file():
        raise RuntimeError("Gate 2B memory PSI is unavailable")
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("full "):
            values = dict(item.split("=", 1) for item in line.split()[1:])
            return int(values["total"])
    raise RuntimeError("Gate 2B full memory PSI counter is unavailable")


def oom_kill_count() -> int:
    for line in Path("/proc/vmstat").read_text(encoding="ascii").splitlines():
        if line.startswith("oom_kill "):
            return int(line.split()[1])
    raise RuntimeError("Gate 2B oom_kill counter is unavailable")


def _thermal() -> tuple[float, str]:
    temperature = Path("/sys/class/thermal/thermal_zone0/temp")
    if not temperature.is_file():
        raise RuntimeError("Gate 2B thermal sensor unavailable")
    temperature_c = int(temperature.read_text(encoding="ascii").strip()) / 1000
    if shutil.which("vcgencmd") is None:
        raise RuntimeError("Gate 2B throttling probe unavailable")
    completed = subprocess.run(
        ["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError("Gate 2B throttling probe failed")
    return temperature_c, completed.stdout.strip()


def resource_sample(owner_roots: dict[str, int], sampled_at: float) -> dict[str, Any]:
    table = _proc_table()
    trees = {
        name: process_tree(root, table) for name, root in owner_roots.items()
    }
    domain_pids: set[int] = set()
    for name, pids in trees.items():
        if name != "controller":
            domain_pids.update(pids)
    if "controller" in trees:
        trees["controller"] -= domain_pids
        trees["controller"].add(owner_roots["controller"])
    owners: dict[str, dict[str, Any]] = {}
    all_pids: set[int] = set()
    for name, root in owner_roots.items():
        pids = trees[name]
        values = [_process_values(pid) for pid in sorted(pids)]
        valid = [value for value in values if value is not None]
        all_pids.update(pid for pid in pids if pid in table or pid == root)
        owners[name] = {
            "root_pid": root,
            "root_present": root in table,
            "process_count": len(valid),
            "rss_kib": sum(value["rss_kib"] for value in valid),
            "pss_kib": sum(value["pss_kib"] for value in valid),
            "threads": sum(value["threads"] for value in valid),
            "cpu_ticks": sum(value["cpu_ticks"] for value in valid),
        }
    memory = _meminfo()
    temperature_c, throttled = _thermal()
    return {
        "monotonic_s": round(sampled_at, 6),
        "mem_total_kib": memory["MemTotal"],
        "mem_available_kib": memory["MemAvailable"],
        "swap_total_kib": memory["SwapTotal"],
        "system_used_mib": round(
            (memory["MemTotal"] - memory["MemAvailable"]) / 1024, 3
        ),
        "temperature_c": temperature_c,
        "throttled": throttled,
        "psi_full_total": _psi_full_total(),
        "owners": owners,
        "unique_process_count": len(all_pids),
    }


class ResourceSampler:
    def __init__(
        self, roots: Callable[[], dict[str, int]], interval_s: float = 0.25
    ) -> None:
        self.roots = roots
        self.interval_s = interval_s
        self.records: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._first_sample = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: BaseException | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("Gate 2B resource sampler already started")
        self._thread = threading.Thread(
            target=self._run, name="gate2b-resource-sampler", daemon=False
        )
        self._thread.start()
        if not self._first_sample.wait(timeout=2.0):
            self._stop.set()
            self._thread.join(timeout=2.0)
            if self._error is not None:
                raise RuntimeError("Gate 2B initial residency sample failed") from self._error
            raise RuntimeError("Gate 2B initial residency sample deadline exceeded")

    def stop(self) -> list[dict[str, Any]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s * 4 + 2)
            if self._thread.is_alive():
                raise RuntimeError("Gate 2B resource sampler did not stop")
        if self._error is not None:
            raise RuntimeError("Gate 2B resource sampler failed") from self._error
        return list(self.records)

    def _run(self) -> None:
        next_sample = time.monotonic()
        try:
            while not self._stop.is_set():
                sampled_at = time.monotonic()
                record = resource_sample(self.roots(), sampled_at)
                record["collection_duration_s"] = round(
                    time.monotonic() - sampled_at, 6
                )
                self.records.append(record)
                self._first_sample.set()
                next_sample += self.interval_s
                self._stop.wait(max(0.0, next_sample - time.monotonic()))
        except BaseException as error:
            self._error = error
            self._first_sample.set()


def evaluate_resources(
    records: list[dict[str, Any]], *, oom_before: int, oom_after: int
) -> tuple[bool, dict[str, Any]]:
    if len(records) < 2:
        raise ValueError("Gate 2B requires at least two resource samples")
    gaps = [
        records[index]["monotonic_s"] - records[index - 1]["monotonic_s"]
        for index in range(1, len(records))
    ]
    owner_sets_complete = all(
        set(record["owners"]) == {"controller", "vad", "asr", "tts", "llm"}
        and all(
            owner["root_present"]
            and owner["process_count"] >= 1
            and owner["rss_kib"] > 0
            and owner["pss_kib"] > 0
            and owner["threads"] > 0
            for owner in record["owners"].values()
        )
        for record in records
    )
    cpu_observed = all(
        max(record["owners"][name]["cpu_ticks"] for record in records)
        - min(record["owners"][name]["cpu_ticks"] for record in records) > 0
        for name in ("controller", "vad", "asr", "tts", "llm")
    )
    swap_zero = all(record["swap_total_kib"] == 0 for record in records)
    throttled_zero = all(
        record["throttled"] == "throttled=0x0" for record in records
    )
    summary = {
        "sample_count": len(records),
        "peak_system_used_mib": max(record["system_used_mib"] for record in records),
        "peak_temperature_c": max(record["temperature_c"] for record in records),
        "max_sample_start_gap_s": round(max(gaps), 6),
        "max_collection_duration_s": max(
            record["collection_duration_s"] for record in records
        ),
        "psi_full_total_delta": records[-1]["psi_full_total"] - records[0]["psi_full_total"],
        "oom_kill_delta": oom_after - oom_before,
        "owner_sets_complete": owner_sets_complete,
        "cpu_observed_for_all_owners": cpu_observed,
        "swap_zero_for_all_samples": swap_zero,
        "throttled_zero_for_all_samples": throttled_zero,
        "owner_peaks": {
            name: {
                "process_count": max(record["owners"][name]["process_count"] for record in records),
                "rss_mib": round(max(record["owners"][name]["rss_kib"] for record in records) / 1024, 3),
                "pss_mib": round(max(record["owners"][name]["pss_kib"] for record in records) / 1024, 3),
                "threads": max(record["owners"][name]["threads"] for record in records),
                "cpu_ticks": max(record["owners"][name]["cpu_ticks"] for record in records),
            }
            for name in ("controller", "vad", "asr", "tts", "llm")
        },
    }
    passed = (
        summary["peak_system_used_mib"] <= 3584
        and summary["peak_temperature_c"] < 80
        and summary["max_sample_start_gap_s"] <= 0.5
        and summary["psi_full_total_delta"] == 0
        and summary["oom_kill_delta"] == 0
        and owner_sets_complete
        and cpu_observed
        and swap_zero
        and throttled_zero
    )
    return passed, summary
