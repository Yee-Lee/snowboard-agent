"""Separate, allowlisted public observations; never accept free-form error detail."""
from __future__ import annotations

import re
import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Mapping

from sbd.cognition.litert_lm.resource import OWNERS, SystemResourceSample

LIFECYCLE_POINTS = frozenset({"engine_ready", "conversation_preparation", "conversation_ready",
    "pre_generate", "post_generate", "pre_speak", "audio_completion", "primary_completion",
    "pre_replacement", "post_replacement", "post_session_close"})
TIMING_NODES = ("conversation_ready", "asr_final", "llm_send", "first_safe_text",
                "llm_terminal", "tts_pcm_ready", "audio_first_write")
NULL_REASONS = frozenset({"NOT_APPLICABLE", "NOT_OBSERVED", "CANCELLED", "FAILED"})
RUNTIME_FIELDS = frozenset({"conversation_generation", "turn_index", "input_codepoints",
    "user_tokens", "current_kv_tokens", "rendered_incremental_tokens", "runtime_prefill_tokens",
    "output_reserve_tokens", "projected_total_tokens", "admission_result", "decode_tokens",
    "terminal_conversation_kv_tokens"})


class ObservationError(ValueError):
    def __init__(self) -> None:
        super().__init__("M4B_OBSERVATION_INVALID")


def _counter(value: object) -> bool:
    return type(value) is int and value >= 0


def runtime_row(values: Mapping[str, object], *,
                null_reasons: Mapping[str, str] | None = None) -> dict[str, object]:
    reasons = {} if null_reasons is None else null_reasons
    absent = {key for key, value in values.items() if value is None}
    equation = ("current_kv_tokens", "rendered_incremental_tokens", "output_reserve_tokens",
                "projected_total_tokens")
    if (set(values) != RUNTIME_FIELDS
            or set(reasons) != absent or any(v not in NULL_REASONS for v in reasons.values())
            or any(values[k] is not None and not _counter(values[k])
                   for k in RUNTIME_FIELDS - {"admission_result"})
            or values["admission_result"] not in {"GENERATE", "R1", "R2", "NOTICE", "SILENT", "E1"}
            or (all(values[k] is not None for k in equation)
                and values["projected_total_tokens"] != values["current_kv_tokens"]
                + values["rendered_incremental_tokens"] + values["output_reserve_tokens"])):
        raise ObservationError()
    return dict(values)


def memory_row(sample: SystemResourceSample, *, conversation_generation: int,
               lifecycle_point: str) -> dict[str, object]:
    sample.validate()
    if not _counter(conversation_generation) or lifecycle_point not in LIFECYCLE_POINTS:
        raise ObservationError()
    owners = {}
    for owner in sorted(OWNERS):
        rows = [p for p in sample.processes if owner in p.owners]
        owners[owner] = {"pid_count": len(rows), "pss_bytes": sum(p.pss_bytes for p in rows),
            "rss_bytes": sum(p.rss_bytes for p in rows),
            "cpu_seconds": sum(p.cpu_seconds for p in rows), "threads": sum(p.threads for p in rows)}
    return {"monotonic_ns": sample.monotonic_ns, "owners": owners,
        "unique_pid_count": len(sample.processes), "combined_pss_bytes": sample.combined_pss_bytes,
        "owner_attribution_may_overlap": True,
        "mem_total_bytes": sample.mem_total_bytes, "mem_available_bytes": sample.mem_available_bytes,
        "system_used_bytes": sample.system_used_bytes, "swap_used_bytes": sample.swap_used_bytes,
        "temperature_c": sample.temperature_c, "throttled_bits": sample.throttled_bits,
        "oom_kill": sample.oom_kill, "conversation_generation": conversation_generation,
        "lifecycle_point": lifecycle_point}


@dataclass(slots=True)
class PromptDashboard:
    """Emission is once per authenticated profile identity, not per turn."""
    _seen: set[str] = field(default_factory=set, init=False)

    def record(self, *, profile_id: str, counts: Mapping[str, int],
               hashes: Mapping[str, str]) -> dict[str, object] | None:
        names = {"core", "personality", "combined"}
        if (profile_id != "core-m4b-cognition-001" or set(counts) != names
                or set(hashes) != names or any(not _counter(v) for v in counts.values())
                or dict(counts) != {"core": 57, "personality": 9, "combined": 66}
                or dict(hashes) != {
                    "core": "8caba35159407882407c1ac1be22c66791ac66236e323bc1b63fa072c1340eec",
                    "personality": "57191898561df177e820a10eed88ad9d47649ba9e5e19c059b554acedda777e5",
                    "combined": "872ae6b6418761b271cd6762c08eeaabe1f20d3a1c4aa72602a09eab1f1eb643"}
                or any(type(v) is not str or re.fullmatch(r"[0-9a-f]{64}", v) is None
                       for v in hashes.values())):
            raise ObservationError()
        if profile_id in self._seen:
            return None
        self._seen.add(profile_id)
        return {"profile_id": profile_id, **{f"{k}_tokens": counts[k] for k in sorted(names)},
                **{f"{k}_sha256": hashes[k] for k in sorted(names)}}


def timing_row(*, clock_domain: str, events: Mapping[str, int | None],
               null_reasons: Mapping[str, str]) -> dict[str, object]:
    # Only controller-mapped monotonic stamps may reach this public schema.
    if clock_domain != "controller_monotonic" or set(events) != set(TIMING_NODES):
        raise ObservationError()
    absent = {name for name, value in events.items() if value is None}
    if set(null_reasons) != absent or any(v not in NULL_REASONS for v in null_reasons.values()):
        raise ObservationError()
    present = [events[name] for name in TIMING_NODES if events[name] is not None]
    if any(not _counter(v) for v in present) or present != sorted(present):
        raise ObservationError()
    return {"clock_domain": clock_domain, "events": {
        name: {"monotonic_ns": events[name], "null_reason": null_reasons.get(name)}
        for name in TIMING_NODES}}


def failure_row(*, code: str, stage: str, request_id: int,
                conversation_generation: int, cleanup_proven: bool) -> dict[str, object]:
    if (code not in {"E1", "R1", "R2", "INVALID_TERMINAL", "TIMEOUT", "CANCELLED",
                     "M4B_RESOURCE_INVALID", "M4B_OBSERVATION_INVALID"}
            or stage not in {"OPEN", "MEASURE", "GENERATE", "CANCEL", "CLOSE", "CLEANUP", "SAMPLE"}
            or not _counter(request_id) or not _counter(conversation_generation)
            or type(cleanup_proven) is not bool):
        raise ObservationError()
    return dict(code=code, stage=stage, request_id=request_id,
                conversation_generation=conversation_generation, cleanup_proven=cleanup_proven)


def _log_observation(row: dict[str, object]) -> None:
    logging.getLogger("sbd.cognition.observation").info("%s", json.dumps(row, sort_keys=True))


class CognitionObserver:
    """Controller-owned live observations. Private payloads/child clocks are never stored.

    Audio's native write callback shares this process's monotonic clock. Callbacks
    may run on its native worker thread, hence serialized timestamp/state updates.
    Missing operations stay null rather than becoming fabricated zero counts.
    """

    def __init__(self, *, sink: Callable[[dict[str, object]], None] | None = None,
                 clock: Callable[[], int] = time.monotonic_ns) -> None:
        self._sink = sink or _log_observation
        self._clock = clock
        self._native_clock_compatible = clock is time.monotonic_ns
        self._lock = threading.RLock()
        self._prompt = PromptDashboard()
        self._ready: int | None = None
        self._generation = 0
        self._events: dict[str, int | None] = dict.fromkeys(TIMING_NODES)
        self._values: dict[str, object] | None = None

    def _emit(self, dashboard: str, values: dict[str, object], **metadata: object) -> None:
        try:
            self._sink({"dashboard": dashboard, "values": values, **metadata})
        except Exception:
            raise ObservationError() from None

    def prompt(self, profile: Mapping[str, object]) -> None:
        with self._lock:
            try:
                row = self._prompt.record(profile_id=profile["profile_id"],
                    counts={"core": profile["core_prompt_tokens"],
                            "personality": profile["personality_prompt_tokens"],
                            "combined": profile["prompt_tokens"]},
                    hashes={"core": profile["core_prompt_sha256"],
                            "personality": profile["personality_prompt_sha256"],
                            "combined": profile["prompt_sha256"]})
            except Exception:
                raise ObservationError() from None
            if row is not None:
                self._emit("prompt", row)

    def conversation_ready(self, generation: int) -> None:
        if not _counter(generation):
            raise ObservationError()
        with self._lock:
            self._generation = generation
            self._ready = self._clock()
            # A replacement READY may precede publication/playback of its R2
            # notice. Preserve that turn's original preparation timestamps.
            if self._values is None:
                self._events = dict.fromkeys(TIMING_NODES)
                self._events["conversation_ready"] = self._ready

    def begin_turn(self, generation: int, turn_index: int,
                   input_codepoints: int | None = None) -> None:
        if (not _counter(generation) or not _counter(turn_index)
                or (input_codepoints is not None and not _counter(input_codepoints))):
            raise ObservationError()
        with self._lock:
            if self._values is not None:
                raise ObservationError()
            self._generation = generation
            self._values = dict.fromkeys(RUNTIME_FIELDS)
            self._values.update(conversation_generation=generation, turn_index=turn_index,
                                input_codepoints=input_codepoints, admission_result="E1")
            self._events["conversation_ready"] = self._ready

    def mark(self, node: str) -> None:
        if node not in TIMING_NODES:
            raise ObservationError()
        with self._lock:
            if self._events[node] is None:
                stamp = self._clock()
                if not _counter(stamp):
                    raise ObservationError()
                self._events[node] = stamp

    def input_codepoints(self, value: int | None) -> None:
        if value is not None and not _counter(value):
            raise ObservationError()
        with self._lock:
            if self._values is not None:
                self._values["input_codepoints"] = value

    def measured(self, snapshot: object) -> None:
        with self._lock:
            if self._values is None:
                return
            fields = ("user_tokens", "current_kv_tokens", "rendered_incremental_tokens",
                      "runtime_prefill_tokens", "output_reserve_tokens")
            counters = {name: getattr(snapshot, name, None) for name in fields}
            if any(not _counter(value) for value in counters.values()):
                raise ObservationError()
            self._values.update(counters)
            self._values["projected_total_tokens"] = (counters["current_kv_tokens"]
                + counters["rendered_incremental_tokens"] + counters["output_reserve_tokens"])

    def generated(self, metrics: object, *, clock_mapped: bool = False) -> None:
        with self._lock:
            if self._values is None:
                return
            counters = {name: getattr(metrics, source, None) for name, source in (
                ("runtime_prefill_tokens", "runtime_prefill_tokens"),
                ("decode_tokens", "decode_tokens"),
                ("terminal_conversation_kv_tokens", "conversation_kv_tokens"))}
            if any(not _counter(value) for value in counters.values()):
                raise ObservationError()
            self._values.update(counters)
            if clock_mapped is True:
                self.native_timing(llm_send=getattr(metrics, "llm_send_monotonic_ns", None),
                    first_safe_text=getattr(metrics, "first_safe_text_monotonic_ns", None),
                    llm_terminal=getattr(metrics, "terminal_monotonic_ns", None),
                    clock_mapped=True)

    def native_timing(self, *, llm_send: int | None = None,
                      first_safe_text: int | None = None, llm_terminal: int | None = None,
                      clock_mapped: bool = False) -> None:
        """Native event stamps require an independently proved clock mapping.

        Wire transmission/reception timestamps are not model execution times.
        The adapter owns the Linux time-namespace/process identity proof.
        """
        if clock_mapped is not True or not self._native_clock_compatible:
            return
        with self._lock:
            for name, value in (("llm_send", llm_send), ("first_safe_text", first_safe_text),
                                ("llm_terminal", llm_terminal)):
                if value is not None:
                    if not _counter(value):
                        raise ObservationError()
                    self._events[name] = value

    def outcome(self, code: str) -> None:
        if code not in {"GENERATE", "R1", "R2", "NOTICE", "SILENT", "E1"}:
            raise ObservationError()
        with self._lock:
            if self._values is not None:
                self._values["admission_result"] = code

    def memory(self, sample: SystemResourceSample, *, generation: int,
               lifecycle_point: str) -> None:
        self._emit("memory", memory_row(sample, conversation_generation=generation,
                                        lifecycle_point=lifecycle_point))

    def finish(self, reason: str = "NOT_OBSERVED") -> None:
        if reason not in NULL_REASONS:
            raise ObservationError()
        with self._lock:
            values = self._values
            if values is None:
                return
            self._values = None
            reasons = {name: reason for name, value in values.items() if value is None}
            self._emit("runtime", runtime_row(values, null_reasons=reasons), null_reasons=reasons)
            self._emit("timing", timing_row(clock_domain="controller_monotonic",
                events=self._events, null_reasons={name: reason for name, value
                                                  in self._events.items() if value is None}),
                conversation_generation=values["conversation_generation"],
                turn_index=values["turn_index"])
            self._events = dict.fromkeys(TIMING_NODES)
            self._events["conversation_ready"] = self._ready
