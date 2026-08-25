"""Validation helpers for the User-approved M4 combined packet."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .m3_packet import sha256_file
from .validation import GIT_SHA_RE, SHA256_RE


PACKET_ID = "M4-COMBINED-VALIDATION-TEST-PACKET-001"
PACKET_STATUS = "USER_APPROVED_LOCAL_IMPLEMENTATION_AUTHORIZED"
PUBLICATION_STATUS = "DRAFT_USER_CONFIRMATION_PENDING"
AUDIO_M3_SHA = "f7b9694d1477f26513880526e0718d2b3c5766b3"
CORE_HAL_SHA = "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf"
M3_ACK_SHA = "5aac035d25f6498c3c0affe1ace4afd7de8f7254"
P9_ACK_SHA = "caf4f7ba867e4ebc1972df0ade86c605a873a286"
RECORDING_PLAN_SHA256 = "d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920"
TTS_PROMPT_SHA256 = "1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739"
P9_SHA256 = {
    "runner": "311466f963bce806b2c89a1c4f5b3275134312e307386c35631eabfb3d21be76",
    "schema": "d5de8fe4144a6c759445f7e45e8867a6bad928177cb28f96d908bbcd59ddb8fe",
    "lock": "d8310132072e822a316521e3bd1cd21e7f0c8396dd49d82c1c6a64a247b7f7f0",
}
P9_PROFILE = {
    "reserve_mib": 2304,
    "cpu_workers": 4,
    "startup_delay_s": 6.0,
    "inference_duration_s": 6.0,
    "ready_timeout_s": 10.0,
    "shutdown_timeout_s": 5.0,
}
P9_1_TEST_ID = "M4-P9.1-REALISTIC-TURN-RESIDENCY-001"
P9_1_POLICY = "VAD_ASR_THEN_P9_INFER_THEN_REASONER_TTS"
SESSION_ROWS = (
    ("M4-SESSION-01", "taiwan_mandarin", "asr-clear-002", "tts-001"),
    ("M4-SESSION-02", "taiwan_mandarin", "asr-clear-003", "tts-002"),
    ("M4-SESSION-03", "taiwan_mandarin", "asr-pause-026", "tts-003"),
    ("M4-SESSION-04", "taiwan_mandarin", "asr-pause-031", "tts-004"),
    ("M4-SESSION-05", "code_switch", "asr-clear-011", "tts-005"),
    ("M4-SESSION-06", "code_switch", "asr-clear-012", "tts-006"),
    ("M4-SESSION-07", "code_switch", "asr-pause-036", "tts-007"),
    ("M4-SESSION-08", "code_switch", "asr-pause-038", "tts-008"),
    ("M4-SESSION-09", "number", "asr-clear-016", "tts-009"),
    ("M4-SESSION-10", "number", "asr-clear-017", "tts-010"),
    ("M4-SESSION-11", "number", "asr-pause-041", "tts-011"),
    ("M4-SESSION-12", "number", "asr-pause-043", "tts-012"),
    ("M4-SESSION-13", "date", "asr-clear-020", "tts-013"),
    ("M4-SESSION-14", "date", "asr-clear-021", "tts-014"),
    ("M4-SESSION-15", "date", "asr-pause-045", "tts-015"),
    ("M4-SESSION-16", "date", "asr-pause-046", "tts-016"),
    ("M4-SESSION-17", "product_term", "asr-clear-023", "tts-017"),
    ("M4-SESSION-18", "product_term", "asr-clear-024", "tts-018"),
    ("M4-SESSION-19", "product_term", "asr-pause-048", "tts-019"),
    ("M4-SESSION-20", "product_term", "asr-pause-049", "tts-020"),
)
FAILURE_ROWS = tuple(
    (f"M4-FI-{domain.upper()}-{scenario.replace('_', '-').upper()}", domain, scenario)
    for domain in ("vad", "asr", "tts")
    for scenario in ("error", "timeout", "cancel", "force_abort")
)
P9_PATHS = {
    "runner": "docs/pm_handoff/artifacts/M4B-P9-RESIDENCY-SURROGATE-001/poc_llm/tools/run_p9_residency_surrogate.py",
    "schema": "docs/pm_handoff/artifacts/M4B-P9-RESIDENCY-SURROGATE-001/poc_llm/schemas/p9_residency_surrogate_protocol.schema.json",
    "lock": "docs/pm_handoff/artifacts/M4B-P9-RESIDENCY-SURROGATE-001/poc_llm/harness/p9-residency-surrogate-lock-v1.json",
}


def load_packet(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("M4 packet must be a JSON object")
    validate_packet(document)
    return document


def _rows(value: object, name: str, width: int) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        raise ValueError(f"M4 {name} must be a list")
    rows: list[tuple[str, ...]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != width or not all(
            isinstance(field, str) and field for field in item
        ):
            raise ValueError(f"M4 {name} row shape is invalid")
        rows.append(tuple(item))
    return tuple(rows)


def validate_packet(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0" or document.get("packet_id") != PACKET_ID:
        raise ValueError("M4 packet identity is invalid")
    if document.get("status") != PACKET_STATUS:
        raise ValueError("M4 packet is not at the User-approved local implementation state")
    if document.get("publication_status") != PUBLICATION_STATUS:
        raise ValueError("M4 packet publication boundary is invalid")
    authority = document.get("authority", {})
    if authority.get("user_approval_date") != "2026-08-25":
        raise ValueError("M4 packet User approval is absent")
    if authority.get("formal_execution_authorized") is not False:
        raise ValueError("M4 planning packet must fail closed for formal execution")
    if (
        authority.get("p9_1_user_approval_date") != "2026-08-25"
        or authority.get("p9_1_design") != "SEQUENTIAL_VAD_ASR_LLM_TTS_RESIDENCY"
    ):
        raise ValueError("M4 P9.1 User design approval is absent")
    if authority.get("m3_gate2a_ack_commit") != M3_ACK_SHA:
        raise ValueError("M4 packet M3 Gate 2A ACK mismatch")
    if authority.get("p9_core_ack_commit") != P9_ACK_SHA:
        raise ValueError("M4 packet P9 ACK mismatch")
    source = document.get("source", {})
    if source.get("audio_m3_execution_baseline_sha") != AUDIO_M3_SHA:
        raise ValueError("M4 packet Audio M3 baseline mismatch")
    if source.get("audio_m4_execution_sha") is not None:
        raise ValueError("M4 draft execution SHA must remain null until candidate cut")
    if source.get("core_hal_execution_sha") != CORE_HAL_SHA:
        raise ValueError("M4 packet Core HAL SHA mismatch")

    fixtures = document.get("fixtures", {})
    if fixtures.get("recording_plan_sha256") != RECORDING_PLAN_SHA256:
        raise ValueError("M4 recording-plan identity mismatch")
    if fixtures.get("tts_prompt_sha256") != TTS_PROMPT_SHA256:
        raise ValueError("M4 TTS prompt identity mismatch")
    if fixtures.get("controlled_fixture_lock_required") is not True:
        raise ValueError("M4 formal run requires a controlled fixture lock")
    if fixtures.get("catalog_correction") != "M4-P9.1-CATALOG-CORRECTION-001":
        raise ValueError("M4 P9.1 catalog correction identity mismatch")
    sessions = _rows(fixtures.get("sessions"), "session catalog", 4)
    if sessions != SESSION_ROWS:
        raise ValueError("M4 20-session catalog mismatch")
    categories = Counter(row[1] for row in sessions)
    if categories != Counter({name: 4 for name in (
        "taiwan_mandarin", "code_switch", "number", "date", "product_term",
    )}):
        raise ValueError("M4 session category balance mismatch")
    if len({row[0] for row in sessions}) != 20 or len({row[2] for row in sessions}) != 20:
        raise ValueError("M4 session IDs and ASR fixtures must be distinct")

    pipeline = document.get("pipeline", {})
    if pipeline.get("order") != ["vad", "asr", "reasoner", "tts", "audio_output_completion"]:
        raise ValueError("M4 pipeline order mismatch")
    expected_pcm = {
        "pcm": "16000_HZ_MONO_S16_LE", "frame_samples": 320,
        "frame_bytes": 640, "frame_duration_ms": 20,
    }
    if any(pipeline.get(name) != value for name, value in expected_pcm.items()):
        raise ValueError("M4 PCM/frame contract mismatch")
    if pipeline.get("network_disabled") is not True:
        raise ValueError("M4 formal pipeline must be offline")
    if pipeline.get("persistent_domains") != ["vad", "asr", "tts"]:
        raise ValueError("M4 persistent-domain set mismatch")
    if pipeline.get("reasoner") != "DETERMINISTIC_SESSION_ID_TO_FROZEN_TTS_ID_NO_TRANSCRIPT_MUTATION":
        raise ValueError("M4 deterministic Reasoner boundary mismatch")

    candidates = document.get("candidates", {})
    expected_candidate_ids = {
        "vad": "vad-silero-onnx-6.2.1",
        "asr": "asr-whispercpp-base-q8_0-1.9.2-m2b",
        "tts": "tts-sherpa-matcha-zh-en-1.13.5",
    }
    if {name: candidates.get(name, {}).get("id") for name in expected_candidate_ids} != expected_candidate_ids:
        raise ValueError("M4 finalist identity mismatch")
    for domain in expected_candidate_ids:
        identity = candidates[domain]
        hashes = [value for key, value in identity.items() if key.endswith("sha256")]
        if not hashes or any(not SHA256_RE.fullmatch(str(value)) for value in hashes):
            raise ValueError(f"M4 {domain} checksum identity is invalid")

    p9 = document.get("p9", {})
    if (
        p9.get("test_id") != P9_1_TEST_ID
        or p9.get("supersedes_test_id") != "M4-P9-RESIDENCY-001"
        or p9.get("orchestration_policy") != P9_1_POLICY
        or p9.get("controller_thread_policy") != {"OPENBLAS_NUM_THREADS": "1"}
    ):
        raise ValueError("M4 P9.1 orchestration policy mismatch")
    if (
        p9.get("artifact_id") != "M4B-P9-RESIDENCY-SURROGATE-001"
        or p9.get("source_sha") != "f18f823146727b50cb3ef15e9e14b51983643406"
        or p9.get("protocol_version") != "1.0"
    ):
        raise ValueError("M4 P9 identity mismatch")
    if p9.get("sha256") != P9_SHA256 or p9.get("profile") != P9_PROFILE:
        raise ValueError("M4 P9 artifact/profile lock mismatch")
    if p9.get("capacity_gate_mib") != 3584:
        raise ValueError("M4 P9 capacity gate mismatch")
    if p9.get("catalog") != [row[0] for row in SESSION_ROWS]:
        raise ValueError("M4 P9.1 residency catalog mismatch")
    if p9.get("execution_status") != "Pending":
        raise ValueError("M4 planning packet cannot claim P9 execution")

    failures = _rows(document.get("failure_injections"), "failure catalog", 3)
    if failures != FAILURE_ROWS:
        raise ValueError("M4 failure-injection catalog mismatch")
    timeouts = document.get("timeouts_seconds", {})
    expected_timeout_names = {
        "ready", "operation", "failure_terminal", "p9_ready", "p9_shutdown",
        "combined_phase", "failure_phase",
    }
    if set(timeouts) != expected_timeout_names or any(
        not isinstance(value, int) or value <= 0 for value in timeouts.values()
    ):
        raise ValueError("M4 packet timeout set is incomplete or invalid")


def validate_repo_inputs(packet: dict[str, Any], repo_root: Path) -> None:
    plan_path = repo_root / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    prompts_path = repo_root / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(plan_path) != packet["fixtures"]["recording_plan_sha256"]:
        raise ValueError("repository recording plan does not match M4 packet")
    if sha256_file(prompts_path) != packet["fixtures"]["tts_prompt_sha256"]:
        raise ValueError("repository TTS prompts do not match M4 packet")
    plan_ids = {
        item["fixture_id"]
        for item in json.loads(plan_path.read_text(encoding="utf-8"))["utterances"]
    }
    prompt_ids = {
        item["fixture_id"]
        for item in json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
    }
    if {row[2] for row in SESSION_ROWS} - plan_ids:
        raise ValueError("M4 ASR catalog is absent from the frozen recording plan")
    if {row[3] for row in SESSION_ROWS} - prompt_ids:
        raise ValueError("M4 TTS catalog is absent from the frozen prompt set")
    for name, relative in P9_PATHS.items():
        path = repo_root / relative
        if not path.is_file() or sha256_file(path) != P9_SHA256[name]:
            raise ValueError(f"M4 P9 {name} artifact checksum mismatch")


def validate_fake_result(document: dict[str, Any], packet: dict[str, Any]) -> None:
    required = {
        "schema_version", "packet_id", "run_id", "run_mode", "evidence_eligible",
        "publication_status", "source_sha", "core_sha", "network_policy",
        "model_load_counts", "sessions", "failure_injections", "cleanup",
        "proposed_disposition", "decision_boundary",
    }
    if set(document) != required:
        raise ValueError("M4 fake result keys are incomplete or unexpected")
    if document["schema_version"] != "1.0" or document["packet_id"] != PACKET_ID:
        raise ValueError("M4 fake result identity mismatch")
    if document["run_mode"] != "fake" or document["evidence_eligible"] is not False:
        raise ValueError("M4 fake result must remain hardware-ineligible")
    if document["publication_status"] != PUBLICATION_STATUS:
        raise ValueError("M4 fake publication boundary mismatch")
    if not GIT_SHA_RE.fullmatch(str(document["source_sha"])) or document["core_sha"] is not None:
        raise ValueError("M4 fake source/Core SHA boundary mismatch")
    if document["network_policy"] != "FAKE_NO_CANDIDATE_OR_HARDWARE_RUNTIME":
        raise ValueError("M4 fake network boundary mismatch")
    if document["model_load_counts"] != {"vad": 1, "asr": 1, "tts": 1}:
        raise ValueError("M4 fake combined run did not retain one persistent load per domain")
    sessions = document["sessions"]
    if not isinstance(sessions, list) or [item.get("session_id") for item in sessions] != [
        row[0] for row in SESSION_ROWS
    ]:
        raise ValueError("M4 fake result session catalog/order mismatch")
    for item, expected in zip(sessions, SESSION_ROWS, strict=True):
        if item != {
            "session_id": expected[0], "asr_fixture_id": expected[2],
            "tts_fixture_id": expected[3], "stage_events": [
                "vad:success", "asr:success", "reasoner:success",
                "tts:success", "audio_output_completion:fake_success",
            ],
        }:
            raise ValueError(f"M4 fake session result mismatch: {expected[0]}")
    failures = document["failure_injections"]
    if not isinstance(failures, list) or [
        (item.get("test_id"), item.get("domain"), item.get("scenario")) for item in failures
    ] != list(FAILURE_ROWS):
        raise ValueError("M4 fake failure result catalog/order mismatch")
    for item in failures:
        if item.get("case_pass") is not True or item.get("recovery_pass") is not True:
            raise ValueError(f"M4 fake failure/recovery case failed: {item.get('test_id')}")
        if item.get("cleanup") != _zero_cleanup():
            raise ValueError(f"M4 fake failure cleanup residue: {item.get('test_id')}")
    if document["cleanup"] != _zero_cleanup():
        raise ValueError("M4 fake combined cleanup residue")
    if document["proposed_disposition"] != "NOT_HARDWARE_EVIDENCE":
        raise ValueError("M4 fake result cannot propose a hardware disposition")
    if "not Pi, P9 or Gate 2B evidence" not in document["decision_boundary"]:
        raise ValueError("M4 fake result decision boundary is incomplete")


def _zero_cleanup() -> dict[str, Any]:
    return {
        "child_processes": 0, "threads": 0, "file_descriptors": 0,
        "iterators": 0, "streams": 0, "device_owners": 0, "clean": True,
    }
