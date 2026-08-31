"""Frozen M4b r14 resource formulas and portable privacy/offline helpers."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections.abc import Iterable
from pathlib import Path
from typing import Mapping


R14_VERSION = "2026-08-29-r14-user-resource-adjustment"
CATALOG_SHA256 = "96fa83acae829107b4c851c3ba90d8a021bc76c7f2ef37cd47d066b46fa6a56d"


class MetricsError(ValueError):
    pass


def load_gate3_catalog(path: Path) -> dict[str, object]:
    try:
        raw_bytes = path.read_bytes()
        value = json.loads(raw_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MetricsError("Gate 3 catalog is unavailable or invalid") from error
    if hashlib.sha256(raw_bytes).hexdigest() != CATALOG_SHA256:
        raise MetricsError("Gate 3 catalog checksum mismatch")
    if type(value) is not dict or set(value) != {
        "schema_version", "catalog_id", "provenance", "resource_marker_profile",
        "intent_cases",
    }:
        raise MetricsError("Gate 3 catalog has missing or extra fields")
    if value["schema_version"] != 1 or value["catalog_id"] != "M4B-CORE-GATE3-PRODUCT-001":
        raise MetricsError("Gate 3 catalog identity mismatch")
    if value["provenance"] != {
        "execution_sha": "0c75536e6ee99b502c59438989ca852194648946",
        "source_locator": "poc_llm/fixtures/gate2/gate2a-public-catalog-002.json",
        "source_sha256": "b4a2bb2c4a9596c668b0ef19379fc546bd861771368ba0823f338b0b060b525b",
    }:
        raise MetricsError("Gate 3 catalog provenance mismatch")
    profile = value["resource_marker_profile"]
    if type(profile) is not dict or set(profile) != {
        "session_count", "current_format", "forbidden_format", "instruction_format",
    } or profile["session_count"] != 20:
        raise MetricsError("Gate 3 marker profile mismatch")
    cases = value["intent_cases"]
    if type(cases) is not list or len(cases) != 3:
        raise MetricsError("Gate 3 intent catalog mismatch")
    expected = ("speak", "tool", "rest")
    for item, kind in zip(cases, expected, strict=True):
        if (
            type(item) is not dict
            or set(item) != {"id", "expected_kind", "text", "actions", "tools"}
            or item["expected_kind"] != kind
            or type(item["id"]) is not str
            or re.fullmatch(r"CORE-OUT-[A-Z]+-001", item["id"]) is None
            or type(item["text"]) is not str
            or not item["text"].strip()
            or type(item["actions"]) is not list
            or kind not in item["actions"]
            or type(item["tools"]) is not list
        ):
            raise MetricsError("Gate 3 intent case mismatch")
    return value


def r14_slope(values: Iterable[float]) -> float:
    samples = tuple(values)
    if len(samples) != 20 or any(type(value) not in (int, float) for value in samples):
        raise MetricsError("r14 requires exactly 20 numeric samples")
    xs = tuple(range(1, 21))
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(samples)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, samples, strict=True)) / denominator


def r14_late_early_delta(values: Iterable[float]) -> float:
    samples = tuple(values)
    if len(samples) != 20:
        raise MetricsError("r14 requires exactly 20 samples")
    return statistics.median(samples[-5:]) - statistics.median(samples[:5])


def verify_r14_vector(value: object) -> dict[str, float]:
    if type(value) is not dict or set(value) != {
        "r14_formula_version", "combined_pss_mib", "system_used_mib", "expected", "tolerance",
    }:
        raise MetricsError("r14 vector has missing or extra fields")
    if value["r14_formula_version"] != R14_VERSION:
        raise MetricsError("r14 formula version mismatch")
    actual = {
        "combined_pss_slope_mib_per_session": r14_slope(value["combined_pss_mib"]),
        "combined_pss_late_minus_early_median_delta_mib": r14_late_early_delta(value["combined_pss_mib"]),
        "system_used_slope_mib_per_session": r14_slope(value["system_used_mib"]),
        "system_used_late_minus_early_median_delta_mib": r14_late_early_delta(value["system_used_mib"]),
    }
    expected = value["expected"]
    tolerance = value["tolerance"]
    if type(expected) is not dict or set(expected) != set(actual) or type(tolerance) is not float or tolerance <= 0:
        raise MetricsError("r14 expected result is invalid")
    if any(abs(actual[name] - expected[name]) > tolerance for name in actual):
        raise MetricsError("r14 formula output drift")
    return actual


def privacy_hits(blobs: Iterable[tuple[str, bytes]], sentinels: Iterable[str | bytes]) -> list[str]:
    values = tuple(value for value in sentinels if value)
    hits: list[str] = []
    for locator, blob in blobs:
        text = blob.decode("utf-8", errors="ignore")
        if any(value in blob if isinstance(value, bytes) else value in text for value in values):
            hits.append(locator)
    return hits


def network_isolated(net_dev: str, route: str) -> bool:
    interfaces = [
        line.split(":", 1)[0].strip()
        for line in net_dev.splitlines()[2:] if ":" in line
        if line.split(":", 1)[0].strip() != "lo"
    ]
    routes = [
        fields[0] for line in route.splitlines()[1:]
        if len(fields := line.split()) >= 2 and fields[0] != "lo" and fields[1] == "00000000"
    ]
    return not interfaces and not routes


def kernel_resource_sample(
    meminfo: str,
    vmstat: str,
    thermal_millicelsius: str,
    throttled: str,
) -> dict[str, float | int]:
    """Parse the mandatory Pi memory, OOM, temperature, and throttle counters."""
    memory: dict[str, int] = {}
    for line in meminfo.splitlines():
        fields = line.replace(":", " ").split()
        if len(fields) >= 2:
            try:
                memory[fields[0]] = int(fields[1])
            except ValueError as error:
                raise MetricsError("meminfo contains a non-integer value") from error
    required = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    if not required.issubset(memory):
        raise MetricsError("meminfo lacks a required field")
    if memory["MemAvailable"] > memory["MemTotal"] or memory["SwapFree"] > memory["SwapTotal"]:
        raise MetricsError("meminfo counters are inconsistent")
    counters: dict[str, int] = {}
    for line in vmstat.splitlines():
        fields = line.split()
        if len(fields) == 2:
            try:
                counters[fields[0]] = int(fields[1])
            except ValueError as error:
                raise MetricsError("vmstat contains a non-integer value") from error
    if "oom_kill" not in counters or counters["oom_kill"] < 0:
        raise MetricsError("vmstat lacks oom_kill")
    try:
        temperature = int(thermal_millicelsius.strip()) / 1000.0
    except ValueError as error:
        raise MetricsError("thermal sample is invalid") from error
    match = re.fullmatch(r"throttled=0x([0-9a-fA-F]+)", throttled.strip())
    if match is None or not (0 <= temperature < 200):
        raise MetricsError("thermal or throttled sample is invalid")
    return {
        "mem_total_mib": memory["MemTotal"] / 1024,
        "mem_available_mib": memory["MemAvailable"] / 1024,
        "system_used_mib": (memory["MemTotal"] - memory["MemAvailable"]) / 1024,
        "swap_used_mib": (memory["SwapTotal"] - memory["SwapFree"]) / 1024,
        "oom_kill": counters["oom_kill"],
        "thermal_celsius": temperature,
        "throttled_bits": int(match.group(1), 16),
    }


def process_group_members(pgid: int, proc_root: Path = Path("/proc")) -> set[int]:
    members: set[int] = set()
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            tail = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            if tail[0] != "Z" and int(tail[2]) == pgid:
                members.add(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue
    return members


def owner_resource_accounting(
    owners: Mapping[str, set[int]],
    *,
    proc_root: Path = Path("/proc"),
    clock_ticks: int,
) -> dict[str, object]:
    """Aggregate disjoint owner PIDs without double-counting combined PSS."""
    expected = {"core", "vad", "asr", "tts", "llm"}
    if set(owners) != expected or type(clock_ticks) is not int or clock_ticks <= 0:
        raise MetricsError("owner accounting input is invalid")
    all_pids: set[int] = set()
    result: dict[str, object] = {}
    combined_pss_kib = 0
    for name in sorted(expected):
        pids = owners[name]
        if type(pids) is not set or not pids or all_pids & pids:
            raise MetricsError("owner PIDs are missing or overlap")
        all_pids.update(pids)
        pss_kib = 0
        rss_kib = 0
        cpu_ticks_total = 0
        threads = 0
        for pid in sorted(pids):
            try:
                stat_tail = (proc_root / str(pid) / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
                rollup = (proc_root / str(pid) / "smaps_rollup").read_text(encoding="ascii")
                if stat_tail[0] == "Z":
                    raise MetricsError("owner process is a zombie")
                cpu_ticks_total += int(stat_tail[11]) + int(stat_tail[12])
                threads += int(stat_tail[17])
            except (OSError, ValueError, IndexError) as error:
                raise MetricsError("owner process sample is unavailable") from error
            fields: dict[str, int] = {}
            for line in rollup.splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[2] == "kB" and parts[0] in {"Pss:", "Rss:"}:
                    fields[parts[0][:-1]] = int(parts[1])
            if set(fields) != {"Pss", "Rss"} or min(fields.values()) < 0:
                raise MetricsError("owner memory sample is unavailable")
            pss_kib += fields["Pss"]
            rss_kib += fields["Rss"]
        combined_pss_kib += pss_kib
        result[name] = {
            "pids": sorted(pids),
            "pss_mib": pss_kib / 1024,
            "rss_mib": rss_kib / 1024,
            "cpu_seconds": cpu_ticks_total / clock_ticks,
            "threads": threads,
        }
    result["combined_pss_mib"] = combined_pss_kib / 1024
    result["unique_pid_count"] = len(all_pids)
    return result


__all__ = [
    "CATALOG_SHA256", "MetricsError", "R14_VERSION", "load_gate3_catalog",
    "kernel_resource_sample", "network_isolated", "owner_resource_accounting",
    "privacy_hits", "process_group_members", "r14_late_early_delta", "r14_slope",
    "verify_r14_vector",
]
