"""Private composition-owned Linux process identity and Pi health binding."""
from __future__ import annotations

import os
import re
import subprocess
import weakref
from dataclasses import dataclass, replace
from pathlib import Path

from sbd.adaptor.framed_child import ChildState
from sbd.cognition.litert_lm.resource import ResourceSampleError, SystemResourceSample


@dataclass(frozen=True)
class _ProcessIdentity:
    pid: int
    ppid: int
    pgid: int
    start: int
    state: str


def _read_ascii(path: Path) -> str:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                 | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        data = os.read(fd, 65537)
        if len(data) > 65536:
            raise ResourceSampleError()
        return data.decode("ascii")
    finally:
        os.close(fd)


def _pi_temperature() -> float:
    try:
        value = _read_ascii(Path("/sys/class/thermal/thermal_zone0/temp")).strip()
        if not re.fullmatch(r"[0-9]{1,6}", value):
            raise ResourceSampleError()
        return int(value) / 1000.0
    except Exception:
        raise ResourceSampleError() from None


def _pi_throttled() -> int:
    try:
        result = subprocess.run(
            ["/usr/bin/vcgencmd", "get_throttled"], check=True, timeout=1.0,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
        )
        match = re.fullmatch(rb"throttled=0x([0-9a-fA-F]{1,8})\n?", result.stdout)
        if match is None:
            raise ResourceSampleError()
        return int(match.group(1), 16)
    except Exception:
        raise ResourceSampleError() from None


class _M4BResourceBinding:
    """Observe existing owners without changing Accepted audio adapters.

    Replacement authority is the actual old/new child lifecycle, not PID changes.
    The retained certificate is safe to validate against both sampler and adapter
    baselines; it cannot authorize any identities other than those it observed.
    """

    def __init__(self, *, asr: object, tts: object, native_asr: bool,
                 native_tts: bool, proc_root: Path = Path("/proc"),
                 core_pid: int | None = None) -> None:
        self._asr, self._tts = asr, tts
        self._native_asr, self._native_tts = native_asr, native_tts
        self._proc = proc_root
        self._core_pid = os.getpid() if core_pid is None else core_pid
        self._llm = None
        self._owners: dict[str, tuple[object, int, dict[int, int]]] = {}
        self._replacements: dict[frozenset[str], tuple[dict, dict]] = {}

    def bind_llm(self, adapter: object) -> None:
        if self._llm is not None:
            raise ResourceSampleError()
        self._llm = weakref.ref(adapter)

    def _processes(self) -> dict[int, _ProcessIdentity]:
        rows = {}
        for entry in self._proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                raw = _read_ascii(entry / "stat")
            except FileNotFoundError:
                continue  # An unrelated process may exit during enumeration.
            head, tail = raw.rsplit(")", 1)
            fields = tail.split()
            pid = int(entry.name)
            if int(head.split("(", 1)[0]) != pid:
                raise ResourceSampleError()
            rows[pid] = _ProcessIdentity(pid, int(fields[1]), int(fields[2]),
                                          int(fields[19]), fields[0])
        return rows

    @staticmethod
    def _group(rows: dict[int, _ProcessIdentity], pgid: int) -> dict[int, int]:
        group = {pid: row for pid, row in rows.items() if row.pgid == pgid}
        if (pgid not in group or any(row.state in {"Z", "X", "x"}
                                    or row.start <= 0 for row in group.values())):
            raise ResourceSampleError()
        return {pid: row.start for pid, row in group.items()}

    def _audio_group(self, key: str, adapter: object, rows: dict[int, _ProcessIdentity],
                     roles: frozenset[str]) -> tuple[int, dict[int, int]]:
        child = getattr(adapter, "_child", None)
        pid = getattr(child, "pid", None)
        state = getattr(child, "state", None)
        if (type(pid) is not int or pid <= 0 or state not in {ChildState.READY, ChildState.BUSY}
                or getattr(child, "returncode", None) is not None):
            raise ResourceSampleError()
        group = self._group(rows, pid)
        old = self._owners.get(key)
        if old is None:
            if state is not ChildState.READY:
                raise ResourceSampleError()
        elif old[0] is child:
            if old[1] != pid or old[2] != group:
                raise ResourceSampleError()
        else:
            old_child, old_pid, old_group = old
            if (getattr(old_child, "state", None) is not ChildState.DESTROYED
                    or type(getattr(old_child, "returncode", None)) is not int
                    or state is not ChildState.READY
                    or any(row.pgid == old_pid and row.state not in {"Z", "X", "x"}
                           for row in rows.values())
                    or set(old_group) & set(group)):
                raise ResourceSampleError()
            def identities(members: dict[int, int], leader: int) -> dict:
                return {member: (start, frozenset({"vad" if member == leader else "asr"})
                                 if key == "asr" else roles)
                        for member, start in members.items()}
            self._replacements[roles] = (identities(old_group, old_pid), identities(group, pid))
        self._owners[key] = (child, pid, group)
        return pid, group

    def __call__(self) -> dict[str, tuple[int, ...]]:
        try:
            return self._registry()
        except Exception:
            raise ResourceSampleError() from None

    def _registry(self) -> dict[str, tuple[int, ...]]:
        rows = self._processes()
        core = rows.get(self._core_pid)
        if core is None or core.state in {"Z", "X", "x"}:
            raise ResourceSampleError()
        owners = {role: (self._core_pid,) for role in ("core", "vad", "asr", "tts")}
        if self._native_asr:
            leader, group = self._audio_group("asr", self._asr, rows, frozenset({"vad", "asr"}))
            descendants = set(group) - {leader}
            if not descendants:
                raise ResourceSampleError()
            for pid in descendants:
                seen = set()
                parent = pid
                while parent != leader:
                    if parent in seen or parent not in group:
                        raise ResourceSampleError()
                    seen.add(parent)
                    parent = rows[parent].ppid
            owners["vad"], owners["asr"] = (leader,), tuple(sorted(descendants))
        if self._native_tts:
            _, group = self._audio_group("tts", self._tts, rows, frozenset({"tts"}))
            owners["tts"] = tuple(sorted(group))
        adapter = self._llm() if self._llm is not None else None
        child = getattr(adapter, "_child", None)
        pid, pgid = getattr(child, "pid", None), getattr(child, "pgid", None)
        if type(pid) is not int or pid <= 0 or pid != pgid:
            raise ResourceSampleError()
        owners["llm"] = tuple(sorted(self._group(rows, pid)))
        return owners

    def rebase_previous(self, previous: SystemResourceSample,
                        sample: SystemResourceSample) -> SystemResourceSample:
        processes = previous.processes
        for roles, (old, new) in self._replacements.items():
            before = tuple(p for p in processes if p.owners & roles)
            after = tuple(p for p in sample.processes if p.owners & roles)
            if ({p.pid: (p.start_time_ticks, p.owners) for p in before} == old
                    and {p.pid: (p.start_time_ticks, p.owners) for p in after} == new
                    and all(p.owners <= roles for p in (*before, *after))
                    and frozenset().union(*(p.owners for p in after)) == roles):
                processes = tuple(p for p in processes if not p.owners & roles) + after
        return replace(previous, processes=processes)
