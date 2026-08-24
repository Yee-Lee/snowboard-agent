"""Validation helpers for the User-approved M3 qualification packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PACKET_ID = "M3-RISK-FOCUSED-QUALIFICATION-TEST-PACKET-001"
PACKET_STATUS = "USER_APPROVED_CORE_SIGNOFF_PENDING"
CORE_RESPONSE = "RESP-AUDIO-M3-RISK-FOCUSED-GATES-001"
POC_OPTION_A_SHA = "de3b0bab4daaf47f62956d4b27f6697b3d4fa823"
PREVIOUS_CORE_HAL_SHA = "5c9e5aac47e7f4f0dd168d8c75541438ee74f858"
PREVIOUS_CORE_ACCEPTANCE_SHA = "2fb2e18f934c3d06392074adba3c4518402101e9"
CORE_HAL_EXECUTION_SHA = "6c7fc8ce94c7218e4948b77c2fe79ef6e6cc3dcf"
CORE_HAL_CHANGE_REQUEST = "CR-AUDIO-M3-CORE-HAL-OUTPUT-ADAPTATION-001"
PLAN_SHA256 = "d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920"
TTS_PROMPT_SHA256 = "1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739"
PROMPT_SHA256 = "e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef"
VAD_CATEGORIES = (
    "normal_conversational_start",
    "low_volume_start",
    "natural_pause",
    "steady_silence",
    "mechanical_device_start",
    "object_impact",
    "cough",
    "playback_speech",
)
ASR_CATEGORIES = (
    "normal_taiwan_mandarin",
    "low_volume_start",
    "natural_pause",
    "code_switch",
    "domain_term",
)
TTS_IDS = ("tts-001", "tts-005", "tts-009", "tts-013", "tts-014", "tts-017")
LIFECYCLE_PATHS = (
    "start_stop",
    "reopen_5",
    "invalid_input",
    "invalid_output",
    "bounded_cancel_asr_tts",
    "force_abort",
)
P9_ARTIFACT_ID = "M4B-P9-RESIDENCY-SURROGATE-001"
P9_SOURCE_SHA = "f18f823146727b50cb3ef15e9e14b51983643406"
P9_PROTOCOL_VERSION = "1.0"
P9_ARTIFACT_SHA256 = {
    "runner": "311466f963bce806b2c89a1c4f5b3275134312e307386c35631eabfb3d21be76",
    "schema": "d5de8fe4144a6c759445f7e45e8867a6bad928177cb28f96d908bbcd59ddb8fe",
    "lock": "d8310132072e822a316521e3bd1cd21e7f0c8396dd49d82c1c6a64a247b7f7f0",
}
CAPTURE_CASES = (
    ("M3-VAD-01", "asr-clear-002.wav", 300),
    ("M3-VAD-02", "asr-clear-003.wav", 300),
    ("M3-VAD-03", "asr-pause-031.wav", 400),
    ("M3-VAD-04", "m3-steady-silence-60s.wav", 3000),
    ("M3-VAD-05", "m3-device-start-10s.wav", 500),
    ("M3-VAD-06", "m3-impact-10s.wav", 500),
    ("M3-VAD-07", "m3-cough-10s.wav", 500),
    ("M3-VAD-08", "m3-playback-speech-10s.wav", 500),
    ("M3-ASR-04", "asr-clear-012.wav", 300),
    ("M3-ASR-05", "asr-clear-023.wav", 300),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_packet(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("M3 packet must be a JSON object")
    validate_packet(document)
    return document


def _pairs(document: dict[str, Any], section: str) -> list[list[str]]:
    value = document[section]
    if not isinstance(value, list) or not all(isinstance(item, list) for item in value):
        raise ValueError(f"{section} must be a list of rows")
    return value


def validate_packet(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0":
        raise ValueError("unsupported M3 packet schema")
    if document.get("packet_id") != PACKET_ID:
        raise ValueError("unexpected M3 packet identity")
    if document.get("status") != PACKET_STATUS:
        raise ValueError("M3 packet is not at the User-approved pre-signoff state")
    authority = document.get("authority", {})
    if authority.get("core_response") != CORE_RESPONSE:
        raise ValueError("M3 packet Core authority mismatch")
    if authority.get("formal_execution_authorized") is not False:
        raise ValueError("pre-signoff packet must fail closed for formal execution")
    source = document.get("source", {})
    if source.get("poc_option_a_validation_sha") != POC_OPTION_A_SHA:
        raise ValueError("POC Option A validation SHA mismatch")
    if source.get("core_hal_previous_accepted_sha") != PREVIOUS_CORE_HAL_SHA:
        raise ValueError("previous accepted Core HAL SHA mismatch")
    if source.get("core_hal_previous_acceptance_sha") != PREVIOUS_CORE_ACCEPTANCE_SHA:
        raise ValueError("Core M3 acceptance SHA mismatch")
    if source.get("core_hal_execution_sha") != CORE_HAL_EXECUTION_SHA:
        raise ValueError("Core HAL execution SHA mismatch")
    if source.get("core_hal_change_request") != CORE_HAL_CHANGE_REQUEST:
        raise ValueError("Core HAL change-request identity mismatch")
    if source.get("execution_sha") is not None:
        raise ValueError("draft manifest execution SHA must remain null until candidate cut")
    fixtures = document.get("fixtures", {})
    if fixtures.get("recording_plan_sha256") != PLAN_SHA256:
        raise ValueError("recording-plan identity mismatch")
    if fixtures.get("tts_prompt_sha256") != TTS_PROMPT_SHA256:
        raise ValueError("TTS prompt identity mismatch")
    vad = _pairs(fixtures, "vad")
    asr = _pairs(fixtures, "asr")
    tts = _pairs(fixtures, "tts")
    if tuple(row[1] for row in vad) != VAD_CATEGORIES or len({row[0] for row in vad}) != 8:
        raise ValueError("VAD packet must contain the eight approved distinct categories")
    if tuple(row[1] for row in asr) != ASR_CATEGORIES or len({row[0] for row in asr}) != 5:
        raise ValueError("ASR packet must contain the five approved distinct categories")
    if tuple(row[1] for row in tts) != TTS_IDS or len({row[0] for row in tts}) != 6:
        raise ValueError("TTS listening set mismatch")
    candidates = document.get("candidates", {})
    if candidates.get("asr_recipe", {}).get("initial_prompt_sha256") != PROMPT_SHA256:
        raise ValueError("ASR prompt identity mismatch")
    if candidates.get("asr_fallback", {}).get("automatic_execution") is not False:
        raise ValueError("small Q8 fallback must not execute automatically")
    lifecycle = _pairs(document, "lifecycle")
    if tuple(row[1] for row in lifecycle) != LIFECYCLE_PATHS:
        raise ValueError("lifecycle coverage mismatch")
    capture_cases = document.get("capture_cases")
    if not isinstance(capture_cases, list) or tuple(
        (item.get("test_id"), item.get("filename"), item.get("frames_20ms"))
        for item in capture_cases if isinstance(item, dict)
    ) != CAPTURE_CASES:
        raise ValueError("M3 capture catalog mismatch")
    timeouts = document.get("timeouts_seconds", {})
    required_timeouts = {
        "ready", "operation", "asr_item", "preflight_capture_phase",
        "direct_pcm_phase", "vad_asr_phase", "tts_phase",
        "lifecycle_phase", "offline_phase",
    }
    if set(timeouts) != required_timeouts or any(
        not isinstance(value, int) or value <= 0 for value in timeouts.values()
    ):
        raise ValueError("M3 packet timeouts must be complete positive integers")
    p9 = document.get("p9", {})
    if p9.get("status") != "ARTIFACT_RECEIVED_CORE_ACK_PENDING_NON_BLOCKING_FOR_AUDIO_M3":
        raise ValueError("P9 disposition mismatch")
    if p9.get("artifact_id") != P9_ARTIFACT_ID or p9.get("source_sha") != P9_SOURCE_SHA:
        raise ValueError("P9 source identity mismatch")
    if p9.get("protocol_version") != P9_PROTOCOL_VERSION:
        raise ValueError("P9 protocol identity mismatch")
    if p9.get("sha256") != P9_ARTIFACT_SHA256:
        raise ValueError("P9 artifact checksum lock mismatch")
    if p9.get("core_ack_required_before_p9_integration") is not True:
        raise ValueError("P9 integration must remain pending Core ACK")
    if p9.get("allow_poc_substitute") is not False:
        raise ValueError("POC must not invent a P9 surrogate")


def validate_repo_inputs(packet: dict[str, Any], repo_root: Path) -> None:
    plan = repo_root / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    prompts = repo_root / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(plan) != packet["fixtures"]["recording_plan_sha256"]:
        raise ValueError("repository recording plan does not match M3 packet")
    if sha256_file(prompts) != packet["fixtures"]["tts_prompt_sha256"]:
        raise ValueError("repository TTS prompts do not match M3 packet")
    plan_ids = {
        item["fixture_id"]
        for item in json.loads(plan.read_text(encoding="utf-8"))["utterances"]
    }
    required_asr = {row[2] for row in packet["fixtures"]["asr"]}
    if not required_asr <= plan_ids:
        raise ValueError("M3 ASR stimulus is missing from the frozen recording plan")
    prompt_ids = {
        item["fixture_id"]
        for item in json.loads(prompts.read_text(encoding="utf-8"))["prompts"]
    }
    required_tts = {row[1] for row in packet["fixtures"]["tts"]}
    if not required_tts <= prompt_ids:
        raise ValueError("M3 TTS stimulus is missing from the frozen prompt set")
