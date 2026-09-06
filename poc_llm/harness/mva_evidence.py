"""Append-only MVA evidence, with no prompt, answer or exception-text channel."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker

from poc_llm.harness.mva_surface import canonical_bytes

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "poc_llm/contracts/mva/machine-sample-v1.schema.json"
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")
ACCEPTED_RUN_SERIES = {"MVA-001", "MVA-002"}
TERMINALS = {
    "READY", "SESSION_OPENED", "RESULT", "SESSION_CLOSED", "SHUTDOWN_ACK",
    "API_PROOF", "RECOVERY_READY", "TIMEOUT", "CANCELLED", "INPUT_TOO_LARGE",
    "CONTEXT_LIMIT", "GENERATION_FAILED", "INVALID_OUTPUT", "PROTOCOL_ERROR",
    "CLEANUP_FAILED", "RESOURCE_STOP", "SAMPLER_FAILED", "IDENTITY_DRIFT",
    "PREFLIGHT_BLOCKED", "INCOMPLETE", "EARLY_END", "NOT_EXECUTED", "RESOURCE_SAMPLE",
}
REASONS = {"NOT_MEASURED", "NO_AUDIO_PROOF", "NO_ACTIVE_OWNER", "NOT_APPLICABLE",
           "RUN_INTERRUPTED", "CLEANUP_PENDING", "NOT_STARTED"}


class EvidenceError(ValueError):
    pass


def _null_paths(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if item is None:
                yield path
            else:
                yield from _null_paths(item, path)


def fill_missing_reasons(sample: dict) -> None:
    sample["missing_reasons"] = {
        path: ("NO_AUDIO_PROOF" if path in {
            "identity.audio_sha256", "timing_ms.speech_end_to_audible_onset"
        } else "NOT_MEASURED") for path in _null_paths(sample)
    }


def validate_sample(sample: dict) -> None:
    # JSON Schema accepts some non-JSON Python floats; reject before validation.
    canonical_bytes(sample)
    Draft202012Validator(json.loads(SCHEMA.read_text()), format_checker=FormatChecker()).validate(sample)
    for key in ("run_id", "case_id", "cycle_id", "session_id"):
        if sample[key] is not None and not SAFE_ID.fullmatch(sample[key]):
            raise EvidenceError("invalid evidence identity")
    expected_run_ids = {series + "-" + sample["case_id"] for series in ACCEPTED_RUN_SERIES}
    if (not re.fullmatch(r"api-proof|cold-[NO][1-3]|replacement-[NO][1-5]|memory-[1-3]|recovery-[1-3]", sample["case_id"])
            or sample["run_id"] not in expected_run_ids):
        raise EvidenceError("unfrozen case or run ID")
    if sample["session_id"] is not None and not re.fullmatch(r"session-([1-9]|1[0-9]|20)|cancel-proof", sample["session_id"]):
        raise EvidenceError("unfrozen session ID")
    expected_cycle = sample["case_id"] if sample["case_id"].startswith("memory-") else None
    if sample["cycle_id"] != expected_cycle or sample["turn_id"] not in (None, 1, 2):
        raise EvidenceError("unfrozen cycle or turn ID")
    expected_platform = {"hardware": "Raspberry Pi 5 Model B Rev 1.1", "os": "Debian 13",
                         "architecture": "aarch64", "backend": "CPU", "threads": 4}
    if any(sample["platform"][key] != value for key, value in expected_platform.items()):
        raise EvidenceError("unfrozen platform")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", sample["platform"]["python"]):
        raise EvidenceError("invalid Python version")
    if sample["terminal"] not in TERMINALS:
        raise EvidenceError("unrecognized terminal")
    if sample["scope"] != "llm_subsystem" or sample["timing_ms"]["speech_end_to_audible_onset"] is not None:
        raise EvidenceError("Audio scope is not proved by this runner")
    if sample["identity"]["audio_sha256"] is not None:
        raise EvidenceError("Audio identity not supported")
    if sample["command"] != ["python3", "-m", "poc_llm.tools.run_mva", sample["case_id"]]:
        raise EvidenceError("only canonical sanitized commands are permitted")
    if sample["raw_sanitized_log_path"] != sample["run_id"] + "/samples.jsonl":
        raise EvidenceError("invalid sanitized log path")
    if set(sample["missing_reasons"]) != set(_null_paths(sample)):
        raise EvidenceError("every null requires an explicit reason")
    if not set(sample["missing_reasons"].values()) <= REASONS:
        raise EvidenceError("free-text reasons are not accepted")
    if sample["monotonic_end_s"] < sample["monotonic_start_s"]:
        raise EvidenceError("invalid monotonic interval")
    resources = sample["resources"]
    if resources["throttled"] is not None and not re.fullmatch(r"0x[0-9a-f]+", resources["throttled"]):
        raise EvidenceError("invalid throttle bitmask")
    if all(resources[k] is not None for k in ("mem_total_mib", "mem_available_mib", "system_used_mib")):
        if not math.isclose(resources["system_used_mib"], resources["mem_total_mib"] - resources["mem_available_mib"], abs_tol=0.001):
            raise EvidenceError("inconsistent resource accounting")
    if sample["cleanup"]["status"] == "PASS" and sample["cleanup"]["owners_absent"] is not True:
        raise EvidenceError("cleanup PASS requires absent owners")
    if sample["process"]["status"] == "PASS" and sample["cleanup"]["status"] != "PASS":
        raise EvidenceError("PASS requires completed cleanup")


class EvidenceWriter:
    """Own a new private run directory; refuse retries using an existing run ID."""
    def __init__(self, root: Path, run_id: str):
        if not SAFE_ID.fullmatch(run_id):
            raise EvidenceError("invalid run ID")
        if not root.is_absolute() or root.resolve() != root:
            raise EvidenceError("evidence root must be an absolute non-symlink path")
        if root.is_relative_to(ROOT):
            raise EvidenceError("raw evidence must remain outside the checkout")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory = root / run_id
        self.directory.mkdir(mode=0o700)
        self.run_id = run_id

    def append(self, sample: dict, *, checkpoint=False) -> None:
        validate_sample(sample)
        if sample["run_id"] != self.run_id:
            raise EvidenceError("cross-run write rejected")
        name = "checkpoints.jsonl" if checkpoint else "samples.jsonl"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
        fd = os.open(self.directory / name, flags, 0o600)
        with os.fdopen(fd, "ab") as output:
            output.write(canonical_bytes(sample) + b"\n")
            output.flush()
            os.fsync(output.fileno())
