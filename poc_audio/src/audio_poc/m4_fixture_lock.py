"""Create and validate the controlled 20-WAV input lock for formal M4 runs."""

from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Any

from .m3_packet import sha256_file
from .m4_packet import PACKET_ID, SESSION_ROWS
from .validation import GIT_SHA_RE, SHA256_RE


LOCK_ID = "M4-COMBINED-20-FIXTURE-LOCK-001"


def _wav_metadata(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (16_000, 1, 2, "NONE"):
            raise ValueError(f"M4 fixture format mismatch: {path.name}")
        frames = source.getnframes()
    if frames <= 0:
        raise ValueError(f"M4 fixture is empty: {path.name}")
    return {
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "duration_seconds": round(frames / 16_000, 6),
    }


def build_fixture_lock(
    repo_root: Path,
    fixture_dir: Path,
    output: Path,
    audio_execution_sha: str,
) -> dict[str, Any]:
    """Lock the approved controlled WAVs without emitting audio or transcripts."""

    if output.exists():
        raise ValueError("M4 fixture-lock output path must be new")
    if not GIT_SHA_RE.fullmatch(audio_execution_sha):
        raise ValueError("M4 fixture lock requires a full Audio execution SHA")
    plan_path = repo_root / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    utterances = {item["fixture_id"]: item for item in plan["utterances"]}
    records: list[dict[str, Any]] = []
    for session_id, category, fixture_id, tts_fixture_id in SESSION_ROWS:
        path = fixture_dir / f"{fixture_id}.wav"
        if not path.is_file():
            raise ValueError(f"M4 controlled fixture is unavailable: {path.name}")
        if fixture_id not in utterances:
            raise ValueError(f"M4 fixture is absent from frozen recording plan: {fixture_id}")
        records.append({
            "session_id": session_id,
            "category": category,
            "fixture_id": fixture_id,
            "tts_fixture_id": tts_fixture_id,
            "reference_sha256": hashlib.sha256(
                utterances[fixture_id]["reference_text"].encode("utf-8")
            ).hexdigest(),
            **_wav_metadata(path),
        })
    document = {
        "schema_version": "1.0",
        "lock_id": LOCK_ID,
        "packet_id": PACKET_ID,
        "audio_execution_sha": audio_execution_sha,
        "fixture_count": len(records),
        "pcm": "16000_HZ_MONO_S16_LE",
        "records": records,
    }
    validate_fixture_lock(document)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as destination:
        json.dump(document, destination, indent=2, sort_keys=True)
        destination.write("\n")
    return document


def load_fixture_lock(path: Path, audio_execution_sha: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("M4 controlled fixture lock is unavailable")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("M4 fixture lock must be a JSON object")
    validate_fixture_lock(document, audio_execution_sha)
    return document


def validate_fixture_lock(document: dict[str, Any], audio_execution_sha: str | None = None) -> None:
    if document.get("schema_version") != "1.0" or document.get("lock_id") != LOCK_ID:
        raise ValueError("M4 fixture lock identity is invalid")
    if document.get("packet_id") != PACKET_ID or document.get("pcm") != "16000_HZ_MONO_S16_LE":
        raise ValueError("M4 fixture lock packet/PCM identity is invalid")
    source_sha = document.get("audio_execution_sha")
    if not isinstance(source_sha, str) or not GIT_SHA_RE.fullmatch(source_sha):
        raise ValueError("M4 fixture lock Audio execution SHA is invalid")
    if audio_execution_sha is not None and source_sha != audio_execution_sha:
        raise ValueError("M4 fixture lock does not match the formal Audio SHA")
    records = document.get("records")
    if not isinstance(records, list) or document.get("fixture_count") != 20:
        raise ValueError("M4 fixture lock must contain 20 records")
    expected = [(row[0], row[1], row[2], row[3]) for row in SESSION_ROWS]
    observed = [
        (item.get("session_id"), item.get("category"), item.get("fixture_id"), item.get("tts_fixture_id"))
        for item in records if isinstance(item, dict)
    ]
    if observed != expected:
        raise ValueError("M4 fixture lock catalog/order mismatch")
    for item in records:
        if (
            not isinstance(item.get("filename"), str)
            or item["filename"] != f"{item['fixture_id']}.wav"
            or not SHA256_RE.fullmatch(str(item.get("sha256")))
            or not SHA256_RE.fullmatch(str(item.get("reference_sha256")))
            or not isinstance(item.get("size_bytes"), int)
            or item["size_bytes"] <= 0
            or not isinstance(item.get("duration_seconds"), (int, float))
            or item["duration_seconds"] <= 0
        ):
            raise ValueError(f"M4 fixture lock record is invalid: {item.get('session_id')}")


def verify_fixture_files(lock: dict[str, Any], fixture_dir: Path) -> None:
    """Fail closed if controlled WAV bytes drift after the lock is generated."""

    validate_fixture_lock(lock)
    for record in lock["records"]:
        path = fixture_dir / record["filename"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"M4 controlled fixture checksum mismatch: {record['filename']}")
        metadata = _wav_metadata(path)
        if (
            metadata["size_bytes"] != record["size_bytes"]
            or metadata["duration_seconds"] != record["duration_seconds"]
        ):
            raise ValueError(f"M4 controlled fixture metadata drift: {record['filename']}")
