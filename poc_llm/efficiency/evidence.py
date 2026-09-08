"""Sanitized append-only engineering/formal evidence boundary."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any

from poc_llm.harness.mva_surface import canonical_bytes


HEX64 = re.compile(r"[0-9a-f]{64}")
SHA40 = re.compile(r"[0-9a-f]{40}")
TERMINALS = {
    "RESULT", "SESSION_CLOSED", "READY", "CANCELLED", "TOKEN_LIMIT",
    "INVALID_OUTPUT", "GENERATION_FAILED", "TIMEOUT", "RESOURCE_STOP",
    "IDENTITY_DRIFT", "SAMPLER_FAILED", "CLEANUP_FAILED", "UNSUPPORTED",
}
STATUSES = {"PASS", "FAIL", "INCONCLUSIVE", "UNSUPPORTED"}
TIMING_KEYS = {
    "startup_to_engine_ready", "interaction_ready", "preparation", "hold_elapsed",
    "request_to_first_text", "request_to_first_chunk", "request_to_full_result",
    "runtime_ttft", "runtime_ttc", "caller_ttc", "open", "close",
    "speech_end_to_audible_onset",
}
TOKEN_KEYS = {"new_user", "rendered", "incremental", "kv", "output", "frame_overhead"}
RESOURCE_KEYS = {
    "owner_pss_mib", "mem_available_mib", "system_used_mib", "swap_used_kib",
    "temperature_c", "throttled", "oom_or_kernel_fault",
}


class EvidenceError(ValueError):
    pass


def _number_or_none(value: object) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                             and math.isfinite(float(value)) and value >= 0)


def validate_sample(sample: object) -> dict[str, Any]:
    required = {
        "format", "run_id", "case_id", "experiment", "pair", "variant",
        "implementation_sha", "surface_sha256", "profile_sha256", "terminal", "status",
        "timing_ms", "token_metrics", "resources", "cleanup", "missing_reasons",
        "raw_sanitized_log_path", "audio_onset_reason",
    }
    if not isinstance(sample, dict) or set(sample) != required:
        raise EvidenceError("sample fields are not exact")
    if sample["format"] != "m4b-mva-efficiency-sample-v1":
        raise EvidenceError("sample format mismatch")
    if (not isinstance(sample["run_id"], str) or not re.fullmatch(r"EFF-[A-Z0-9-]{1,96}", sample["run_id"])
            or sample["case_id"] not in FULL_CASES
            or sample["experiment"] not in {"A", "B", "F"}
            or not isinstance(sample["pair"], int) or isinstance(sample["pair"], bool)
            or sample["pair"] not in range(0, 6)
            or not isinstance(sample["variant"], str) or sample["variant"] not in {"J", "P", "D", "H", "F"}
            or not SHA40.fullmatch(str(sample["implementation_sha"]))
            or not HEX64.fullmatch(str(sample["surface_sha256"]))
            or not HEX64.fullmatch(str(sample["profile_sha256"]))
            or sample["terminal"] not in TERMINALS or sample["status"] not in STATUSES):
        raise EvidenceError("sample identity or disposition is invalid")
    if (not isinstance(sample["timing_ms"], dict) or set(sample["timing_ms"]) != TIMING_KEYS
            or any(not _number_or_none(value) for value in sample["timing_ms"].values())):
        raise EvidenceError("timing metrics are invalid")
    if (not isinstance(sample["token_metrics"], dict) or set(sample["token_metrics"]) != TOKEN_KEYS
            or any(not _number_or_none(value) for value in sample["token_metrics"].values())):
        raise EvidenceError("token metrics are invalid")
    resources = sample["resources"]
    if not isinstance(resources, dict) or set(resources) != RESOURCE_KEYS:
        raise EvidenceError("resource metrics are invalid")
    for key in RESOURCE_KEYS - {"throttled", "oom_or_kernel_fault"}:
        if not _number_or_none(resources[key]):
            raise EvidenceError("resource metrics are invalid")
    if resources["throttled"] is not None and not isinstance(resources["throttled"], str):
        raise EvidenceError("throttled value is invalid")
    if resources["oom_or_kernel_fault"] is not None and not isinstance(resources["oom_or_kernel_fault"], bool):
        raise EvidenceError("kernel fault value is invalid")
    cleanup = sample["cleanup"]
    if (not isinstance(cleanup, dict) or set(cleanup) != {"status", "owners_absent"}
            or cleanup["status"] not in {"PASS", "FAIL", "INCONCLUSIVE"}
            or cleanup["owners_absent"] not in {True, False, None}):
        raise EvidenceError("cleanup is invalid")
    locator = sample["raw_sanitized_log_path"]
    relative = PurePosixPath(locator) if isinstance(locator, str) else PurePosixPath("/")
    if (not isinstance(locator, str) or relative.is_absolute() or ".." in relative.parts
            or str(relative) != locator or len(relative.parts) != 2
            or relative.parts[1] != "samples.jsonl"):
        raise EvidenceError("raw locator must be neutral and relative")
    if sample["audio_onset_reason"] != "NO_AUDIO_PROOF":
        raise EvidenceError("Audio onset claim is forbidden")
    reasons = sample["missing_reasons"]
    if not isinstance(reasons, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in reasons.items()):
        raise EvidenceError("missing reasons are invalid")
    encoded = canonical_bytes(sample).decode("utf-8")
    for forbidden in ("answer", "prompt", "credential", "/home/", "/var/", "private_key"):
        if forbidden in encoded.lower():
            raise EvidenceError("sample contains forbidden raw or host data")
    return json.loads(encoded)


from poc_llm.efficiency.plan import FULL_ORDER as FULL_CASES  # noqa: E402


class EvidenceWriter:
    def __init__(self, root: Path, run_id: str) -> None:
        self.directory = root / run_id
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.path = self.directory / "samples.jsonl"
        self.path.touch(mode=0o600, exist_ok=False)

    def append(self, sample: object) -> None:
        value = validate_sample(sample)
        with self.path.open("ab", buffering=0) as output:
            output.write(canonical_bytes(value) + b"\n")
            os.fsync(output.fileno())
