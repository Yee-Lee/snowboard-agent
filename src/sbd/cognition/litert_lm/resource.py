"""Validated unique-process observations and profile-owned memory admission."""
from __future__ import annotations

import math
import os
import time
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

OWNERS = frozenset({"core", "vad", "asr", "tts", "llm"})


class ResourceSampleError(RuntimeError):
    def __init__(self, reason: str = "unspecified") -> None:
        super().__init__("M4B_RESOURCE_INVALID")
        self.reason = reason


def _integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


@dataclass(frozen=True, slots=True)
class ProcessResource:
    pid: int
    owner: str | frozenset[str]
    start_time_ticks: int
    pss_bytes: int
    rss_bytes: int
    cpu_seconds: float
    threads: int

    @property
    def owners(self) -> frozenset[str]:
        return frozenset({self.owner}) if isinstance(self.owner, str) else self.owner


@dataclass(frozen=True, slots=True)
class SystemResourceSample:
    monotonic_ns: int
    processes: tuple[ProcessResource, ...]
    mem_total_bytes: int
    mem_available_bytes: int
    swap_used_bytes: int
    oom_kill: int
    temperature_c: float
    throttled_bits: int

    @property
    def combined_pss_bytes(self) -> int:
        return sum(row.pss_bytes for row in self.processes)

    @property
    def system_used_bytes(self) -> int:
        return self.mem_total_bytes - self.mem_available_bytes

    def owner_pss_bytes(self, owner: str) -> int:
        return sum(row.pss_bytes for row in self.processes if owner in row.owners)

    def validate(self, previous: SystemResourceSample | None = None) -> None:
        integers = (self.monotonic_ns, self.mem_available_bytes, self.swap_used_bytes,
                    self.oom_kill, self.throttled_bits)
        if (not all(_integer(v) for v in integers)
                or not _integer(self.mem_total_bytes, 1)
                or self.mem_available_bytes > self.mem_total_bytes
                or type(self.temperature_c) not in (float, int)
                or not math.isfinite(self.temperature_c) or not 0 <= self.temperature_c < 80
                or self.throttled_bits != 0 or type(self.processes) is not tuple
                or not self.processes):
            raise ResourceSampleError("system_fields_or_thermal_health")
        pids: set[int] = set()
        for row in self.processes:
            if isinstance(row, ProcessResource) and _integer(row.pss_bytes) and _integer(row.rss_bytes) and row.pss_bytes > row.rss_bytes:
                raise ResourceSampleError(f"pss_exceeds_rss_pid_{row.pid}")
            if (not isinstance(row, ProcessResource) or not _integer(row.pid, 1)
                    or row.pid in pids or type(row.owners) is not frozenset
                    or not row.owners or not row.owners.issubset(OWNERS)
                    or not _integer(row.start_time_ticks, 1)
                    or not _integer(row.pss_bytes) or not _integer(row.rss_bytes)
                    or row.pss_bytes > row.rss_bytes or not _integer(row.threads, 1)
                    or type(row.cpu_seconds) not in (float, int)
                    or not math.isfinite(row.cpu_seconds) or row.cpu_seconds < 0):
                raise ResourceSampleError(f"process_fields_pid_{getattr(row, 'pid', 'invalid')}")
            pids.add(row.pid)
        if (frozenset().union(*(row.owners for row in self.processes)) != OWNERS
                or self.combined_pss_bytes > self.mem_total_bytes):
            raise ResourceSampleError("owner_coverage_or_total_pss")
        if previous is None:
            if self.oom_kill:
                raise ResourceSampleError("initial_oom_counter")
        else:
            if not isinstance(previous, SystemResourceSample):
                raise ResourceSampleError("previous_sample_type")
            previous.validate()
            if (self.monotonic_ns <= previous.monotonic_ns
                    or self.mem_total_bytes != previous.mem_total_bytes
                    or self.oom_kill != previous.oom_kill):
                raise ResourceSampleError("clock_memory_or_oom_changed")
            old = {p.pid: p for p in previous.processes}
            if pids != set(old):
                raise ResourceSampleError("process_set_changed")
            if any(p.pid in old and (p.start_time_ticks != old[p.pid].start_time_ticks
                   or p.owner != old[p.pid].owner) for p in self.processes):
                raise ResourceSampleError("process_identity_changed")


class MemoryDecision(str, Enum):
    GENERATE = "GENERATE"
    NOTICE = "NOTICE"
    SILENT = "SILENT"


def memory_decision(sample: SystemResourceSample, *, min_mem_available_speak_bytes: int,
                    min_mem_available_generate_bytes: int,
                    previous: SystemResourceSample | None = None) -> MemoryDecision:
    speak, generate = min_mem_available_speak_bytes, min_mem_available_generate_bytes
    if not _integer(speak, 1) or not _integer(generate, speak):
        raise ResourceSampleError()
    if not isinstance(sample, SystemResourceSample):
        raise ResourceSampleError()
    sample.validate(previous)
    if sample.mem_available_bytes < speak:
        return MemoryDecision.SILENT
    if sample.mem_available_bytes < generate:
        return MemoryDecision.NOTICE
    return MemoryDecision.GENERATE


class ProcLLMResourceSampler:
    """Require composition-owned process and platform-health sources.

    Each process start time is reread around sampling to detect exits/PID reuse.
    No missing source is replaced with fabricated zero counters.
    """

    def __init__(self, proc_root: Path = Path("/proc"), *,
                 ownership_registry: Callable[[], Mapping[str, Collection[int]]] | None = None,
                 temperature: Callable[[], float] | None = None,
                 throttled: Callable[[], int] | None = None,
                 clock: Callable[[], int] = time.monotonic_ns,
                 clock_ticks: int | None = None) -> None:
        self._proc = proc_root
        self._registry = ownership_registry
        self._temperature = temperature
        self._throttled = throttled
        self._clock = clock
        self._ticks = clock_ticks or os.sysconf("SC_CLK_TCK")
        self._previous: SystemResourceSample | None = None

    @staticmethod
    def _read(path: Path) -> str:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                             | getattr(os, "O_NOFOLLOW", 0))
        try:
            return os.read(descriptor, 1024 * 1024).decode("ascii")
        finally:
            os.close(descriptor)

    @classmethod
    def _kib(cls, path: Path, field: str) -> int:
        return cls._parse_kib(cls._read(path), field)

    @staticmethod
    def _parse_kib(contents: str, field: str) -> int:
        matches = [line.split() for line in contents.splitlines()
                   if line.split() and line.split()[0] == f"{field}:"]
        if len(matches) != 1 or len(matches[0]) != 3 or matches[0][2] != "kB":
            raise ResourceSampleError()
        result = int(matches[0][1])
        if result < 0:
            raise ResourceSampleError()
        return result * 1024

    def sample(self, *, child_pid: int, child_pgid: int) -> SystemResourceSample:
        try:
            return self._sample(child_pid, child_pgid)
        except ResourceSampleError:
            raise
        except Exception:
            raise ResourceSampleError() from None

    def rebase_llm_owner(self, *, child_pid: int, child_pgid: int) -> SystemResourceSample:
        """Private READY-after-authorized-rebuild hook; retain the system health baseline."""
        try:
            return self._sample(child_pid, child_pgid, authorized_replacement=True)
        except ResourceSampleError:
            raise
        except Exception:
            raise ResourceSampleError() from None

    def validate_sample(self, sample: SystemResourceSample,
                        previous: SystemResourceSample | None) -> None:
        """Validate health continuously across composition-proven audio replacement."""
        try:
            adjusted = previous
            rebase = getattr(self._registry, "rebase_previous", None)
            if previous is not None and callable(rebase):
                adjusted = rebase(previous, sample)
                if (not isinstance(adjusted, SystemResourceSample)
                        or replace(adjusted, processes=previous.processes) != previous):
                    raise ResourceSampleError()
                # Composition can authenticate audio-owner replacement only.
                immutable = {"core", "llm"}
                old_fixed = {(p.pid, p.start_time_ticks, p.owners)
                             for p in previous.processes if p.owners & immutable}
                new_fixed = {(p.pid, p.start_time_ticks, p.owners)
                             for p in adjusted.processes if p.owners & immutable}
                if old_fixed != new_fixed:
                    raise ResourceSampleError()
            sample.validate(adjusted)
        except Exception as error:
            failure = ResourceSampleError(getattr(error, "reason", type(error).__name__))
            failure.sample = sample
            failure.previous = previous
            raise failure from None

    def _sample(self, child_pid: int, child_pgid: int, *, authorized_replacement=False) -> SystemResourceSample:
        if (self._registry is None or self._temperature is None or self._throttled is None
                or not _integer(child_pid, 1) or not _integer(child_pgid, 1)):
            raise ResourceSampleError()
        owners = {owner: tuple(sorted(pids)) for owner, pids in self._registry().items()}
        if set(owners) != OWNERS or child_pid not in owners["llm"]:
            raise ResourceSampleError()
        membership: dict[int, set[str]] = {}
        for owner, pids in owners.items():
            if not pids or len(set(pids)) != len(pids):
                raise ResourceSampleError()
            for pid in pids:
                membership.setdefault(pid, set()).add(owner)
        rows = []
        for pid, roles in membership.items():
                if not _integer(pid, 1):
                    raise ResourceSampleError()
                directory = self._proc / str(pid)
                before = self._read(directory / "stat").rsplit(")", 1)[1].split()
                if before[0] == "Z" or ("llm" in roles and int(before[2]) != child_pgid):
                    raise ResourceSampleError()
                # Both fields must come from one kernel snapshot. Separate reads
                # can straddle native memory release and produce Pss > Rss.
                rollup = self._read(directory / "smaps_rollup")
                pss = self._parse_kib(rollup, "Pss")
                rss = self._parse_kib(rollup, "Rss")
                after = self._read(directory / "stat").rsplit(")", 1)[1].split()
                if before[19] != after[19] or before[2] != after[2]:
                    raise ResourceSampleError()
                rows.append(ProcessResource(pid, frozenset(roles), int(after[19]), pss, rss,
                    (int(after[11]) + int(after[12])) / self._ticks, int(after[17])))
        current = {owner: tuple(sorted(pids)) for owner, pids in self._registry().items()}
        if current != owners:
            raise ResourceSampleError()
        live_group = set()
        for directory in self._proc.iterdir():
            if not directory.name.isdigit():
                continue
            try:
                fields = self._read(directory / "stat").rsplit(")", 1)[1].split()
            except FileNotFoundError:
                continue
            if int(fields[2]) == child_pgid and fields[0] != "Z":
                live_group.add(int(directory.name))
        if live_group != set(owners["llm"]):
            raise ResourceSampleError()
        meminfo = self._proc / "meminfo"
        swap_total = self._kib(meminfo, "SwapTotal")
        swap_free = self._kib(meminfo, "SwapFree")
        counters = dict(line.split() for line in self._read(self._proc / "vmstat").splitlines())
        sample = SystemResourceSample(self._clock(), tuple(rows),
            self._kib(meminfo, "MemTotal"), self._kib(meminfo, "MemAvailable"),
            swap_total - swap_free, int(counters["oom_kill"]), self._temperature(), self._throttled())
        previous = self._previous
        if authorized_replacement and previous is not None:
            old_other = tuple(p for p in previous.processes if "llm" not in p.owners)
            new_llm = tuple(p for p in sample.processes if "llm" in p.owners)
            if (any(p.owners != frozenset({"llm"}) for p in (*new_llm,
                    *(p for p in previous.processes if "llm" in p.owners)))
                    or not new_llm):
                raise ResourceSampleError()
            # Only authenticated new LLM identity changes. All old system counters
            # and all non-LLM owner identities remain the validation baseline.
            previous = replace(previous, processes=(*old_other, *new_llm))
        self.validate_sample(sample, previous)
        self._previous = sample
        return sample


__all__ = ["ProcessResource", "SystemResourceSample", "ResourceSampleError",
           "MemoryDecision", "memory_decision", "ProcLLMResourceSampler"]
