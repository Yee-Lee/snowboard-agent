"""Dependency-free validation for tracked Audio POC JSON documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .models import TerminalStatus


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GATE_1B_DISPOSITIONS = {
    "REQUEST_AUTHORIZE",
    "REQUEST_REJECT",
    "REQUEST_DEFER",
}


def validate_run_result(document: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "source_sha",
        "candidate_id",
        "candidate_kind",
        "scenario",
        "started_at_utc",
        "duration_ms",
        "terminal_status",
        "worker_exit_code",
        "error_code",
        "force_abort_used",
        "cleanup",
    }
    _require_keys(document, required, "result")
    if not GIT_SHA_RE.fullmatch(str(document["source_sha"])):
        raise ValueError("result source_sha must be a full Git SHA")
    if document["terminal_status"] not in {status.value for status in TerminalStatus}:
        raise ValueError("result terminal_status is invalid")
    cleanup = document["cleanup"]
    _require_keys(
        cleanup,
        {"child_processes", "threads", "iterators", "streams", "device_owners", "clean"},
        "cleanup",
    )
    if cleanup["clean"] != all(
        cleanup[name] == 0
        for name in ("child_processes", "threads", "iterators", "streams", "device_owners")
    ):
        raise ValueError("cleanup clean flag disagrees with cleanup counts")


def validate_m4a_conformance_result(document: dict[str, Any]) -> None:
    """Validate the fake-only WP2 protocol result without candidate imports."""

    required = {
        "schema_version", "run_id", "source_sha", "candidate_id", "domain",
        "scenario", "protocol_version", "events", "started_at_utc", "duration_ms",
        "terminal_status", "worker_exit_code", "error_code", "force_abort_used", "cleanup",
    }
    _require_keys(document, required, "M4a conformance result")
    if document["schema_version"] != "1.0" or document["protocol_version"] != 1:
        raise ValueError("M4a conformance schema or protocol version is invalid")
    if not GIT_SHA_RE.fullmatch(str(document["source_sha"])):
        raise ValueError("M4a conformance source_sha must be a full Git SHA")
    if document["domain"] not in {"asr", "tts"}:
        raise ValueError("M4a conformance domain is invalid")
    events = document["events"]
    if not isinstance(events, list) or events[:2] != ["ready", "started"]:
        raise ValueError("M4a conformance must begin READY then STARTED")
    terminal = str(document["terminal_status"])
    if terminal not in {status.value for status in TerminalStatus}:
        raise ValueError("M4a conformance terminal status is invalid")
    event_for_terminal = {
        "success": "result", "error": "error", "timeout": "timeout",
        "cancelled": "cancelled", "force_aborted": "force_aborted",
    }[terminal]
    if events[-1] != event_for_terminal:
        raise ValueError("M4a conformance terminal event disagrees with status")
    cleanup = document["cleanup"]
    _require_keys(
        cleanup,
        {"child_processes", "threads", "iterators", "streams", "device_owners", "clean"},
        "M4a conformance cleanup",
    )
    if cleanup["clean"] != all(cleanup[name] == 0 for name in ("child_processes", "threads", "iterators", "streams", "device_owners")):
        raise ValueError("M4a conformance cleanup flag disagrees with counts")


def validate_m4a_authorized_preflight(document: dict[str, Any]) -> None:
    """Validate an artifact-only report for the two focused Gate 1B rows."""

    required = {
        "schema_version", "report_id", "generated_at_utc", "poc_source_sha",
        "core_gate1b_ack_commit", "poc_gate1b_proposal_commit", "network_policy",
        "candidate_reports",
    }
    _require_keys(document, required, "M4a authorized preflight")
    if document["schema_version"] != "1.0" or document["report_id"] != "M4A-G1B-AUTHORIZED-PREFLIGHT":
        raise ValueError("M4a authorized preflight identity is invalid")
    if not GIT_SHA_RE.fullmatch(str(document["poc_source_sha"])):
        raise ValueError("M4a authorized preflight source SHA is invalid")
    if document["core_gate1b_ack_commit"] != "790c0f86e12422542ef94cacd3c4dd850e346bca":
        raise ValueError("M4a authorized preflight Core ACK binding is invalid")
    if document["poc_gate1b_proposal_commit"] != "756ded69dd7b4661fcbac272d4d234c387890fc8":
        raise ValueError("M4a authorized preflight proposal binding is invalid")
    if document["network_policy"] != "offline_from_hashed_inputs":
        raise ValueError("M4a authorized preflight network policy is invalid")
    allowed = {"asr-sherpa-sensevoice-int8-2025-09-09", "tts-sherpa-matcha-zh-en-1.13.5"}
    reports = document["candidate_reports"]
    if not isinstance(reports, list) or not reports:
        raise ValueError("M4a authorized preflight requires candidate reports")
    ids = [item.get("candidate_id") for item in reports]
    if len(ids) != len(set(ids)) or not set(ids) <= allowed:
        raise ValueError("M4a authorized preflight has unauthorized or duplicate candidates")
    for report in reports:
        if report.get("execution_status") != "PREFLIGHT_PASS_NOT_EXECUTED":
            raise ValueError("M4a authorized preflight must not claim execution")
        artifacts = report.get("verified_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("M4a authorized preflight requires verified artifacts")
        for artifact in artifacts:
            if not SHA256_RE.fullmatch(str(artifact.get("sha256"))) or int(artifact.get("size_bytes", 0)) <= 0:
                raise ValueError("M4a authorized preflight artifact identity is invalid")


def validate_m4a_runtime_preflight(document: dict[str, Any]) -> None:
    """Validate the Pi-only offline install/import report."""

    required = {
        "schema_version", "report_id", "generated_at_utc", "poc_source_sha",
        "core_gate1b_ack_commit", "poc_gate1b_proposal_commit", "candidate_ids",
        "network_policy", "platform", "verified_artifacts", "install",
        "runtime_identity", "execution_status", "cleanup",
    }
    _require_keys(document, required, "M4a runtime preflight")
    if document["schema_version"] != "1.0" or document["report_id"] != "M4A-G1B-AUTHORIZED-RUNTIME-PREFLIGHT":
        raise ValueError("M4a runtime preflight identity is invalid")
    if not GIT_SHA_RE.fullmatch(str(document["poc_source_sha"])):
        raise ValueError("M4a runtime preflight source SHA is invalid")
    if document["core_gate1b_ack_commit"] != "790c0f86e12422542ef94cacd3c4dd850e346bca":
        raise ValueError("M4a runtime preflight Core ACK binding is invalid")
    if document["poc_gate1b_proposal_commit"] != "756ded69dd7b4661fcbac272d4d234c387890fc8":
        raise ValueError("M4a runtime preflight proposal binding is invalid")
    expected_ids = {
        "asr-sherpa-sensevoice-int8-2025-09-09",
        "tts-sherpa-matcha-zh-en-1.13.5",
    }
    if set(document["candidate_ids"]) != expected_ids:
        raise ValueError("M4a runtime preflight candidate scope is invalid")
    if document["network_policy"] != "offline_from_hashed_inputs":
        raise ValueError("M4a runtime preflight network policy is invalid")
    install = document["install"]
    if install.get("index_disabled") is not True or install.get("dependencies_disabled") is not True:
        raise ValueError("M4a runtime preflight install is not closed offline")
    if document["execution_status"] != "RUNTIME_IMPORT_PASS_NOT_INFERRED":
        raise ValueError("M4a runtime preflight must not claim inference")
    identity = document["runtime_identity"]
    if identity.get("packages") != {"sherpa-onnx": "1.13.5", "sherpa-onnx-core": "1.13.5"}:
        raise ValueError("M4a runtime preflight package identity is invalid")
    if identity.get("api") != {"OfflineRecognizer": True, "OfflineTts": True}:
        raise ValueError("M4a runtime preflight API identity is invalid")
    if not identity.get("native_libraries"):
        raise ValueError("M4a runtime preflight native identity is absent")
    cleanup = document["cleanup"]
    _require_keys(
        cleanup,
        {"child_processes", "threads", "iterators", "streams", "device_owners", "clean"},
        "M4a runtime preflight cleanup",
    )
    if cleanup["clean"] is not True or any(
        cleanup[name] != 0
        for name in ("child_processes", "threads", "iterators", "streams", "device_owners")
    ):
        raise ValueError("M4a runtime preflight cleanup is not clean")


def validate_m4a_candidate_smoke(document: dict[str, Any]) -> None:
    """Validate the two-item preliminary real-candidate smoke report."""

    required = {
        "schema_version", "report_id", "generated_at_utc", "poc_source_sha",
        "platform", "network_policy", "scope", "results", "execution_status",
        "cleanup",
    }
    _require_keys(document, required, "M4a candidate smoke")
    if document["schema_version"] != "1.0" or document["report_id"] != "M4A-G1B-AUTHORIZED-CANDIDATE-SMOKE":
        raise ValueError("M4a candidate smoke identity is invalid")
    if not GIT_SHA_RE.fullmatch(str(document["poc_source_sha"])):
        raise ValueError("M4a candidate smoke source SHA is invalid")
    if document["network_policy"] != "offline_from_hashed_inputs":
        raise ValueError("M4a candidate smoke network policy is invalid")
    if document["scope"] != "ONE_ASR_FIXTURE_AND_ONE_TTS_PROMPT_PRELIMINARY_NOT_GATE":
        raise ValueError("M4a candidate smoke scope is invalid")
    results = document["results"]
    if not isinstance(results, list) or len(results) != 2:
        raise ValueError("M4a candidate smoke requires two results")
    if document["execution_status"] == "SMOKE_PASS_PRELIMINARY_NOT_GATE":
        if any(item.get("terminal_status") != "SUCCESS" for item in results):
            raise ValueError("M4a candidate smoke PASS disagrees with a result")
        by_id = {item.get("candidate_id"): item for item in results}
        asr = by_id.get("asr-sherpa-sensevoice-int8-2025-09-09", {})
        tts = by_id.get("tts-sherpa-matcha-zh-en-1.13.5", {})
        if asr.get("raw_transcript_emitted") is not False:
            raise ValueError("M4a candidate smoke emitted an ASR transcript")
        if tts.get("pcm_emitted") is not False or tts.get("audio_device_opened") is not False:
            raise ValueError("M4a candidate smoke emitted or played TTS PCM")
        if tts.get("sample_rate_hz") != 16000 or int(tts.get("sample_count", 0)) <= 0:
            raise ValueError("M4a candidate smoke TTS native PCM is invalid")
    cleanup = document["cleanup"]
    _require_keys(
        cleanup,
        {"child_processes", "threads", "iterators", "streams", "device_owners", "clean"},
        "M4a candidate smoke cleanup",
    )
    counters_clean = all(
        cleanup[name] == 0
        for name in ("child_processes", "threads", "iterators", "streams", "device_owners")
    )
    if cleanup["clean"] != counters_clean:
        raise ValueError("M4a candidate smoke cleanup flag disagrees with counters")
    if document["execution_status"] == "SMOKE_PASS_PRELIMINARY_NOT_GATE" and not counters_clean:
        raise ValueError("M4a candidate smoke PASS requires clean cleanup")


def validate_candidate_manifest(document: dict[str, Any], repo_root: Path) -> None:
    _require_keys(
        document,
        {
            "schema_version",
            "candidate_id",
            "kind",
            "engine",
            "engine_version",
            "artifact",
            "artifact_sha256",
            "license",
            "offline",
            "entrypoint",
            "parameters",
        },
        "candidate manifest",
    )
    _validate_tracked_checksum(
        repo_root / str(document["artifact"]), str(document["artifact_sha256"])
    )


def validate_gate1b_candidate_proposal(document: dict[str, Any]) -> None:
    """Validate a provenance-only proposal without touching controlled artifacts."""

    _require_keys(
        document,
        {
            "schema_version",
            "proposal_id",
            "status",
            "language",
            "core_gate1a",
            "poc_binding",
            "controlled_artifact_policy",
            "candidates",
        },
        "Gate 1B proposal",
    )
    if document["schema_version"] != "1.0":
        raise ValueError("Gate 1B proposal schema_version must be 1.0")
    if document["status"] != "PROPOSED_NOT_AUTHORIZED":
        raise ValueError("Gate 1B proposal must remain PROPOSED_NOT_AUTHORIZED")
    if document["language"] != "zh-TW":
        raise ValueError("Gate 1B proposal language must remain frozen at zh-TW")

    core = document["core_gate1a"]
    _require_keys(core, {"delivery_id", "branch", "commit", "path"}, "Core Gate 1A")
    if not GIT_SHA_RE.fullmatch(str(core["commit"])):
        raise ValueError("Core Gate 1A commit must be a full Git SHA")

    binding = document["poc_binding"]
    _require_keys(binding, {"branch", "proposal_commit"}, "POC binding")
    if binding["proposal_commit"] is not None:
        raise ValueError("proposal_commit must be null before the proposal commit exists")

    policy = document["controlled_artifact_policy"]
    _require_keys(
        policy,
        {"tracked_in_git", "locator_prefix", "permitted_actions", "prohibited_actions"},
        "controlled artifact policy",
    )
    if policy["tracked_in_git"] is not False:
        raise ValueError("controlled artifacts must not be tracked in Git")
    if not str(policy["locator_prefix"]).startswith("controlled://"):
        raise ValueError("controlled locator prefix must use controlled://")

    candidates = document["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gate 1B proposal must contain candidate rows")
    ids: set[str] = set()
    domains: set[str] = set()
    for candidate in candidates:
        _require_keys(
            candidate,
            {
                "candidate_id",
                "domain",
                "origin",
                "requested_disposition",
                "decision_reason",
                "engine",
                "artifacts",
                "dependencies",
                "aarch64_build_proposal",
                "native_contract",
                "offline_cache",
                "risks",
            },
            "Gate 1B candidate",
        )
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in ids:
            raise ValueError(f"duplicate Gate 1B candidate_id: {candidate_id}")
        ids.add(candidate_id)
        domain = str(candidate["domain"])
        if domain not in {"vad", "asr", "tts"}:
            raise ValueError(f"invalid Gate 1B domain: {domain}")
        domains.add(domain)
        if candidate["requested_disposition"] not in GATE_1B_DISPOSITIONS:
            raise ValueError(f"invalid Gate 1B disposition for {candidate_id}")
        _validate_gate1b_engine(candidate["engine"], candidate_id)
        artifacts = candidate["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"{candidate_id} must declare at least one artifact")
        for artifact in artifacts:
            _validate_gate1b_artifact(artifact, candidate_id)
        dependencies = candidate["dependencies"]
        _require_keys(
            dependencies,
            {"status", "runtime", "build", "native"},
            f"{candidate_id} dependencies",
        )
        for key in ("runtime", "build", "native"):
            if not isinstance(dependencies[key], list):
                raise ValueError(f"{candidate_id} dependencies.{key} must be a list")
        build = candidate["aarch64_build_proposal"]
        _require_keys(
            build,
            {"platform", "status", "recipe", "network_policy"},
            f"{candidate_id} aarch64 build proposal",
        )
        if build["status"] != "NOT_EXECUTED_GATE_1B":
            raise ValueError(f"{candidate_id} build status must remain NOT_EXECUTED_GATE_1B")
        if build["network_policy"] != "offline_from_hashed_inputs":
            raise ValueError(f"{candidate_id} build must require hashed offline inputs")
        native = candidate["native_contract"]
        _require_keys(native, {"status", "input", "output"}, f"{candidate_id} native contract")
        if native["status"] != "DECLARED_UNVERIFIED_GATE_1B":
            raise ValueError(f"{candidate_id} native contract must remain unverified")
        offline = candidate["offline_cache"]
        _require_keys(offline, {"status", "locator"}, f"{candidate_id} offline cache")
        if not str(offline["locator"]).startswith("controlled://"):
            raise ValueError(f"{candidate_id} offline locator must use controlled://")
    if domains != {"vad", "asr", "tts"}:
        raise ValueError("Gate 1B proposal must cover VAD, ASR, and TTS")


def _validate_gate1b_engine(engine: Any, candidate_id: str) -> None:
    _require_keys(
        engine,
        {
            "name",
            "version",
            "upstream_url",
            "immutable_revision",
            "source_sha256",
            "source_size_bytes",
            "source_acquired_at_utc",
            "source_controlled_locator",
            "license",
            "notice",
        },
        f"{candidate_id} engine",
    )
    if not SHA256_RE.fullmatch(str(engine["source_sha256"])):
        raise ValueError(f"{candidate_id} engine source_sha256 is invalid")
    if int(engine["source_size_bytes"]) <= 0:
        raise ValueError(f"{candidate_id} engine source_size_bytes must be positive")
    if not str(engine["upstream_url"]).startswith("https://"):
        raise ValueError(f"{candidate_id} engine upstream_url must use HTTPS")
    if not str(engine["source_controlled_locator"]).startswith("controlled://"):
        raise ValueError(f"{candidate_id} engine source locator must use controlled://")


def _validate_gate1b_artifact(artifact: Any, candidate_id: str) -> None:
    _require_keys(
        artifact,
        {
            "role",
            "filename",
            "url",
            "immutable_revision",
            "sha256",
            "size_bytes",
            "acquired_at_utc",
            "license",
            "notice",
            "controlled_locator",
        },
        f"{candidate_id} artifact",
    )
    if not SHA256_RE.fullmatch(str(artifact["sha256"])):
        raise ValueError(f"{candidate_id} artifact sha256 is invalid")
    if int(artifact["size_bytes"]) <= 0:
        raise ValueError(f"{candidate_id} artifact size_bytes must be positive")
    if not str(artifact["url"]).startswith("https://"):
        raise ValueError(f"{candidate_id} artifact URL must use HTTPS")
    if not str(artifact["controlled_locator"]).startswith("controlled://"):
        raise ValueError(f"{candidate_id} artifact locator must use controlled://")


def validate_fixture_catalog(document: dict[str, Any], repo_root: Path) -> None:
    _require_keys(document, {"schema_version", "fixtures"}, "fixture catalog")
    fixtures = document["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixture catalog must contain fixtures")
    fixture_ids: set[str] = set()
    for fixture in fixtures:
        _require_keys(
            fixture,
            {"fixture_id", "kind", "path", "sha256", "source", "license", "sensitivity"},
            "fixture",
        )
        fixture_id = str(fixture["fixture_id"])
        if fixture_id in fixture_ids:
            raise ValueError(f"duplicate fixture_id: {fixture_id}")
        fixture_ids.add(fixture_id)
        _validate_tracked_checksum(repo_root / str(fixture["path"]), str(fixture["sha256"]))


def _validate_tracked_checksum(path: Path, expected: str) -> None:
    if not SHA256_RE.fullmatch(expected):
        raise ValueError(f"invalid SHA-256 for {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path}")


def _require_keys(document: Any, required: set[str], label: str) -> None:
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be an object")
    missing = sorted(required - set(document))
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")
