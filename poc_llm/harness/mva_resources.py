"""Read-only Linux/Pi resource probes, no fallback or synthetic success values."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess


class ResourceError(RuntimeError):
    pass


def _fields(path: Path) -> dict[str, int]:
    return {line.split(":")[0]: int(line.split()[1]) for line in path.read_text().splitlines()
            if ":" in line and len(line.split()) >= 2 and line.split()[1].isdigit()}


def stop_reason(sample: dict, initial_swap: int) -> str | None:
    required = {"mem_total_mib", "mem_available_mib", "system_used_mib", "swap_used_kib",
                "temperature_c", "throttled", "oom_or_kernel_fault"}
    if any(sample.get(key) is None for key in required):
        return "SAMPLER_FAILED"
    if (sample["mem_available_mib"] < 512 or sample["swap_used_kib"] > initial_swap
            or sample["temperature_c"] >= 80 or sample["throttled"] != "0x0"
            or sample["oom_or_kernel_fault"]):
        return "RESOURCE_STOP"
    return None


class PiSampler:
    def __init__(self):
        self.initial_kernel = self._kernel()
        self.initial_oom = self._oom()
        self.initial_swap = self.sample([])["swap_used_kib"]

    @staticmethod
    def _kernel() -> str:
        result = subprocess.run(["dmesg", "--color=never"], capture_output=True, text=True, timeout=3)
        if result.returncode:
            raise ResourceError("SAMPLER_FAILED")
        return result.stdout

    @staticmethod
    def _oom() -> int:
        values = dict(line.split() for line in Path("/proc/vmstat").read_text().splitlines())
        return int(values["oom_kill"])

    def sample(self, owners: list[int]) -> dict:
        memory = _fields(Path("/proc/meminfo"))
        pss = rss = 0
        for pid in set(owners):
            values = _fields(Path(f"/proc/{pid}/smaps_rollup"))
            pss += values["Pss"]
            rss += values["Rss"]
        temp = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=3, check=True)
        throttle = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3, check=True)
        temperature = re.fullmatch(r"temp=([0-9.]+)'C\s*", temp.stdout)
        mask = re.fullmatch(r"throttled=(0x[0-9a-f]+)\s*", throttle.stdout)
        if temperature is None or mask is None:
            raise ResourceError("SAMPLER_FAILED")
        kernel = self._kernel()
        if not kernel.startswith(self.initial_kernel):
            raise ResourceError("SAMPLER_FAILED")  # ring buffer loss cannot prove absence
        delta = kernel[len(self.initial_kernel):]
        return {
            "owner_pss_mib": pss / 1024 if owners else None,
            "owner_rss_mib": rss / 1024 if owners else None,
            "mem_total_mib": memory["MemTotal"] / 1024,
            "mem_available_mib": memory["MemAvailable"] / 1024,
            "system_used_mib": (memory["MemTotal"] - memory["MemAvailable"]) / 1024,
            "swap_used_kib": memory["SwapTotal"] - memory["SwapFree"],
            "temperature_c": float(temperature.group(1)), "throttled": mask.group(1),
            "oom_or_kernel_fault": self._oom() > self.initial_oom or bool(re.search(
                r"out of memory|oom-kill|kernel panic|Oops:|BUG:|segfault", delta, re.I)),
        }
