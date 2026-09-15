"""M4B resource/privacy helpers and integer-byte threshold derivation."""

from __future__ import annotations

import hashlib
import json
import re
import asyncio
import base64
from dataclasses import dataclass
from collections.abc import Iterable
from pathlib import Path
from typing import Mapping


class MetricsError(ValueError):
    pass


def privacy_hits(blobs: Iterable[tuple[str, bytes]], sentinels: Iterable[str | bytes]) -> list[str]:
    values = []
    for value in sentinels:
        raw = value if isinstance(value, bytes) else value.encode("utf-8")
        if raw:
            encoded = base64.b64encode(raw)
            urlsafe = base64.urlsafe_b64encode(raw)
            values.extend((raw, encoded, encoded.rstrip(b"="), urlsafe,
                           urlsafe.rstrip(b"="), raw.hex().encode("ascii"),
                           raw.hex().upper().encode("ascii")))
    hits: list[str] = []
    for locator, blob in blobs:
        if any(value in blob for value in values):
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
                raise MetricsError("meminfo contains a non-integer value") from None
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
                raise MetricsError("vmstat contains a non-integer value") from None
    if "oom_kill" not in counters or counters["oom_kill"] < 0:
        raise MetricsError("vmstat lacks oom_kill")
    try:
        temperature = int(thermal_millicelsius.strip()) / 1000.0
    except ValueError as error:
        raise MetricsError("thermal sample is invalid") from None
    match = re.fullmatch(r"throttled=0x([0-9a-fA-F]+)", throttled.strip())
    if match is None or not (0 <= temperature < 200):
        raise MetricsError("thermal or throttled sample is invalid")
    return {
        "mem_total_mib": memory["MemTotal"] / 1024,
        "mem_available_mib": memory["MemAvailable"] / 1024,
        "system_used_mib": (memory["MemTotal"] - memory["MemAvailable"]) / 1024,
        "swap_total_mib": memory["SwapTotal"] / 1024,
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
                raise MetricsError("owner process sample is unavailable") from None
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


MIB = 1024 ** 2
MEASUREMENT_SAFETY_FLOOR_BYTES = 512 * MIB
PORTABLE_IDS = frozenset(f"M4B-{name}-001" for name in
    ("NORM", "PROMPT", "SEM", "S2", "ADM", "PREFILL", "OUTCOME", "CONV", "MEM",
     "REC", "WIRE", "PRIV", "REG"))
TARGET_IDS = frozenset(f"M4B-PI-{name}-001" for name in
    ("ATT", "SEM", "CONV", "MEM", "WAKE", "TIME", "RES"))
AUTH_FIELDS = frozenset({"schema_version", "harness_sha256", "candidate_sha",
                         "profile_sha256", "target_identity"})


def _digest_value(value: object, length: int = 64) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None


def validate_authorization(value: object, expected: Mapping[str, object]) -> dict[str, object]:
    """Dual-role evidence sign-off, not an invented cryptographic signature."""
    from sbd.cognition.litert_lm.measurement import validate_authorization as validate_grant
    try:
        return validate_grant(value, expected)
    except Exception:
        raise MetricsError("M4B_AUTHORIZATION_INVALID") from None


@dataclass(frozen=True, slots=True)
class MeasurementPoint:
    lifecycle_point: str
    operation_index: int
    sample: object


def derive_thresholds(points: Iterable[MeasurementPoint], *, completed: bool,
                      cleanup_proven: bool) -> dict[str, int]:
    """Derive only from a complete single-session series including action minima."""
    from sbd.cognition.litert_lm.resource import SystemResourceSample
    rows = tuple(points)
    required = {"engine_ready", "conversation_preparation", "conversation_ready", "pre_generate",
        "post_generate", "primary_completion", "pre_speak", "audio_completion",
        "post_session_close"}
    optional = {"pre_replacement", "post_replacement"}
    if completed is not True or cleanup_proven is not True or not rows:
        raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
    previous = None
    try:
        for row in rows:
            if (not isinstance(row, MeasurementPoint) or not isinstance(row.sample, SystemResourceSample)
                    or type(row.operation_index) is not int or row.operation_index < 0
                    or row.lifecycle_point not in required | optional | {"sample"}):
                raise ValueError
            row.sample.validate(previous)
            previous = row.sample
    except Exception:
        raise MetricsError("M4B_MEASUREMENT_INVALID") from None
    labels = [row.lifecycle_point for row in rows]
    if (not required.issubset(labels) or labels[0] != "engine_ready"
            or labels[-1] != "post_session_close" or labels.count("engine_ready") != 1
            or labels.count("post_session_close") != 1
            or not labels.index("engine_ready") < labels.index("conversation_preparation")
                < labels.index("conversation_ready") < labels.index("pre_generate")
            or any(rows[i].operation_index > rows[i + 1].operation_index for i in range(len(rows) - 1))):
        raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
    replacement_pending = None
    for row in rows:
        if row.lifecycle_point == "pre_replacement":
            if replacement_pending is not None:
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
            replacement_pending = row.operation_index
        elif row.lifecycle_point == "post_replacement":
            if replacement_pending != row.operation_index:
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
            replacement_pending = None
    if replacement_pending is not None:
        raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
    # One operation index is one turn's generation/action window. A generation
    # includes any following speech through Audio and primary completion; a
    # context-rejection notice can have an action without GENERATE. Counting all
    # primary completions as generations confuses these two legal paths.
    operations = {}
    for index, row in enumerate(rows):
        if row.lifecycle_point in {"pre_generate", "post_generate", "pre_speak",
                                  "audio_completion", "primary_completion"}:
            points = operations.setdefault(row.operation_index, {})
            if row.lifecycle_point in points:
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
            points[row.lifecycle_point] = index
    for points in operations.values():
        primary = points.get("primary_completion")
        if primary is None:
            raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
        if "pre_generate" in points or "post_generate" in points:
            if not ("pre_generate" in points and "post_generate" in points
                    and points["pre_generate"] < points["post_generate"] < primary):
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
        if "pre_speak" in points or "audio_completion" in points:
            if not ("pre_speak" in points and "audio_completion" in points
                    and points["pre_speak"] < points["audio_completion"] <= primary
                    and points.get("post_generate", -1) < points["pre_speak"]):
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
    drops = {}
    for operation, end in (("speak", "audio_completion"), ("generate", "primary_completion")):
        intervals = []
        for index, row in enumerate(rows):
            if row.lifecycle_point != f"pre_{operation}":
                continue
            stop = next((i for i in range(index + 1, len(rows))
                if rows[i].lifecycle_point == end and rows[i].operation_index == row.operation_index), None)
            if stop is None or any(p.lifecycle_point == f"pre_{operation}"
                                   for p in rows[index + 1:stop]):
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
            if operation == "generate" and not any(p.lifecycle_point == "post_generate"
                    and p.operation_index == row.operation_index for p in rows[index + 1:stop + 1]):
                raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
            intervals.append(row.sample.mem_available_bytes
                - min(p.sample.mem_available_bytes for p in rows[index:stop + 1]))
        if not intervals:
            raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
        if operation == "speak" and labels.count("pre_speak") != labels.count("audio_completion"):
            raise MetricsError("M4B_MEASUREMENT_INCOMPLETE")
        drops[operation] = max(intervals)
    ceil_mib = lambda value: ((value + MIB - 1) // MIB) * MIB
    speak = ceil_mib(MEASUREMENT_SAFETY_FLOOR_BYTES + drops["speak"])
    generate = max(speak, ceil_mib(MEASUREMENT_SAFETY_FLOOR_BYTES + drops["generate"]))
    return {"speak_drop_bytes": drops["speak"], "generate_drop_bytes": drops["generate"],
        "min_mem_available_speak_bytes": speak, "min_mem_available_generate_bytes": generate}




class MeasurementHarness:
    """Laboratory operation wrapper with live sampling and unconditional cleanup.

    Target composition supplies actual operations, lifecycle emissions and health
    sampling. This wrapper never creates target PASS cards or production thresholds.
    """

    def __init__(self, *, authorization, expected_tuple, sample, cleanup,
                 user_authorized_diagnostic: bool = False, pv_attested: bool = False,
                 point_sink=None, error_sink=None,
                 interval_seconds: float = 0.05, cleanup_timeout_seconds: float = 10.0) -> None:
        import math
        if (type(user_authorized_diagnostic) is not bool or type(pv_attested) is not bool
                or (user_authorized_diagnostic and pv_attested)):
            raise MetricsError("M4B_MEASUREMENT_INVALID")
        self.user_authorized_diagnostic = user_authorized_diagnostic
        if pv_attested:
            from sbd.cognition.litert_lm.measurement import PV_FIELDS
            if (authorization is not None or type(expected_tuple) is not dict
                    or set(expected_tuple) != PV_FIELDS
                    or expected_tuple.get("schema_version") != 1
                    or expected_tuple.get("target_identity")
                       != "pi5-4gb-debian13-aarch64-cp3135"
                    or any(not _digest_value(expected_tuple.get(name)) for name in (
                        "harness_sha256", "content_sha256", "profile_sha256"))):
                raise MetricsError("M4B_MEASUREMENT_INVALID")
            self.authorized_tuple = dict(expected_tuple)
        else:
            self.authorized_tuple = (dict(expected_tuple) if user_authorized_diagnostic
                                     else validate_authorization(authorization, expected_tuple))
        self.pv_attested = pv_attested
        if ((point_sink is not None and not callable(point_sink))
                or (error_sink is not None and not callable(error_sink))):
            raise MetricsError("M4B_MEASUREMENT_INVALID")
        self._point_sink, self._error_sink = point_sink, error_sink
        if (type(interval_seconds) not in (float, int) or not math.isfinite(interval_seconds)
                or interval_seconds <= 0 or interval_seconds > 1):
            raise MetricsError("M4B_MEASUREMENT_INVALID")
        if (not callable(sample) or not callable(cleanup)
                or type(cleanup_timeout_seconds) not in (float, int)
                or not math.isfinite(cleanup_timeout_seconds) or cleanup_timeout_seconds <= 0):
            raise MetricsError("M4B_MEASUREMENT_INVALID")
        self._sample, self._cleanup, self._interval = sample, cleanup, interval_seconds
        self._cleanup_timeout = cleanup_timeout_seconds
        self.points: list[MeasurementPoint] = []
        self.completed = False
        self.cleanup_proven = False
        self.stopped = False
        self._active = False

    def capture(self, lifecycle_point: str, operation_index: int, *, before_operation=False) -> None:
        if self.stopped or self.completed:
            raise MetricsError("M4B_MEASUREMENT_STOPPED")
        try:
            observed = self._sample()
        except Exception as error:
            self.stopped = True
            if self._error_sink is not None:
                self._error_sink("resource_sample_failed", error)
            raise MetricsError("M4B_MEASUREMENT_STOPPED") from None
        self.record_sample(observed, lifecycle_point, operation_index,
                           before_operation=before_operation)

    def record_sample(self, sample, lifecycle_point: str, operation_index: int, *,
                      before_operation=False) -> None:
        """Record an actual adapter lifecycle sample without taking a second sample."""
        from sbd.cognition.observability import LIFECYCLE_POINTS
        if (self.stopped or self.completed or lifecycle_point not in LIFECYCLE_POINTS | {"sample"}
                or type(operation_index) is not int or operation_index < 0):
            raise MetricsError("M4B_MEASUREMENT_STOPPED")
        try:
            sample.validate(self.points[-1].sample if self.points else None)
            if before_operation and sample.mem_available_bytes < MEASUREMENT_SAFETY_FLOOR_BYTES:
                raise ValueError
            point = MeasurementPoint(lifecycle_point, operation_index, sample)
            self.points.append(point)
            if self._point_sink is not None:
                self._point_sink(point)
        except Exception as error:
            self.stopped = True
            if self._error_sink is not None:
                self._error_sink("resource_validation_failed", error)
            raise MetricsError("M4B_MEASUREMENT_STOPPED") from None

    async def operation(self, *, before: str, after: str, index: int, execute):
        if not self._active:
            raise MetricsError("M4B_MEASUREMENT_NOT_ACTIVE")
        self.capture(before, index, before_operation=True)
        task = asyncio.create_task(execute())
        try:
            while not task.done():
                await asyncio.wait({task}, timeout=self._interval)
                if not task.done():
                    self.capture("sample", index)
            result = task.result()
            self.capture(after, index)
            return result
        except BaseException:
            self.stopped = True
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def run(self, scenario, *, derive_profile=True) -> dict[str, object]:
        if not derive_profile and not (self.user_authorized_diagnostic or self.pv_attested):
            raise MetricsError("M4B_MEASUREMENT_INPUT_INVALID")
        if self._active or self.completed or self.stopped:
            raise MetricsError("M4B_MEASUREMENT_ALREADY_USED")
        self._active = True
        try:
            await asyncio.wait_for(scenario(self), timeout=3600)
        except Exception as error:
            self.stopped = True
            if self._error_sink is not None:
                self._error_sink("scenario_failed", error)
            # Native scenario/driver exceptions may contain private text or
            # paths. They are never a public harness diagnostic or result.
            raise MetricsError("M4B_MEASUREMENT_STOPPED") from None
        except BaseException:
            self.stopped = True
            raise
        finally:
            self._active = False
            try:
                self.cleanup_proven = await asyncio.wait_for(
                    self._cleanup(), timeout=self._cleanup_timeout) is True
            except BaseException as error:
                self.stopped = True
                if self._error_sink is not None:
                    self._error_sink("cleanup_failed", error)
            if not self.cleanup_proven:
                self.stopped = True
        if self.stopped:
            raise MetricsError("M4B_MEASUREMENT_STOPPED")
        values = (derive_thresholds(self.points, completed=True, cleanup_proven=self.cleanup_proven)
                  if derive_profile else None)
        self.completed = True
        result = {"authorized_tuple": dict(self.authorized_tuple),
                  "status": "Measured" if derive_profile else "DiagnosticComplete",
                  "derived": values, "sample_count": len(self.points)}
        if self.user_authorized_diagnostic:
            result["evidence_mode"] = "developer_diagnostic"
        return result
