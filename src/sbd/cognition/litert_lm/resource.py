"""Linux process-group PSS and MemAvailable sampler for M4b."""

from __future__ import annotations

import os
from pathlib import Path

from sbd.cognition.llm import LLMResourceSample


class ProcLLMResourceSampler:
    def __init__(self, proc_root: Path = Path("/proc")) -> None:
        self._proc = proc_root

    @staticmethod
    def _kib(path: Path, field: str) -> int:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            data = os.read(descriptor, 1024 * 1024).decode("ascii")
        finally:
            os.close(descriptor)
        for line in data.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[0] == f"{field}:" and parts[2] == "kB":
                value = int(parts[1])
                if value < 0:
                    break
                return value
        raise RuntimeError("required resource field is unavailable")

    def sample(self, *, child_pid: int, child_pgid: int) -> LLMResourceSample:
        members: set[int] = set()
        for entry in self._proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                # /proc/<pid>/stat: pgrp is field 5; the comm field may contain spaces.
                tail = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
                if int(tail[2]) == child_pgid:
                    members.add(int(entry.name))
            except (OSError, ValueError, IndexError):
                continue
        if child_pid not in members:
            raise RuntimeError("LLM owner process is absent")
        pss = sum(self._kib(self._proc / str(pid) / "smaps_rollup", "Pss") for pid in members)
        available = self._kib(self._proc / "meminfo", "MemAvailable")
        return LLMResourceSample(pss * 1024, available * 1024)


__all__ = ["ProcLLMResourceSampler"]
