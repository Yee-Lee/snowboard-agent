"""Derive and lock the exact M2A 8+12 PCM fixture set without candidate execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave
from typing import Any

from .m4a_m2a_packet import (
    COMMON_VOICE_SOURCE_LOCK_ID,
    INTERNAL_SOURCE_LOCK_ID,
    LABEL_INDEX_SHA256,
    PACKET_ID,
    PLAN_SHA256,
    load_json,
    repo_root,
    select_internal_fixtures,
    sha256_file,
    validate_common_voice_source_lock,
    validate_internal_source_lock,
    validate_packet,
)


FIXTURE_LOCK_ID = "M4A-M2A-FIXTURE-LOCK-001"
DELIVERED_MANIFEST_SHA256 = "1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2"
SAMPLE_RATE_HZ = 16_000
GSTREAMER_VERSION = "1.24.2"
GSTREAMER_COMPONENTS = {
    "/usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstmpg123.so":
        "ea45afa94259b3298cd80b3e385e16fb057652db6de353cabac7a1bb228aa2c1",
    "/usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstaudioresample.so":
        "e4ff626919e0d4ba9a4a105dd0d4acbb0608e80d759a513509c0f3ec6a70d1b7",
    "/usr/lib/x86_64-linux-gnu/gstreamer-1.0/libgstwavenc.so":
        "d4e487b72a09808d46f78d764948800dd33a9070f03d38430bebf46e97a2d6a1",
    "/usr/lib/x86_64-linux-gnu/libmpg123.so.0.48.2":
        "af6e041af88719710b77d83b7deb8ecbe10bdf67a255fcadcfae7eec1d19eea6",
    "/usr/lib/x86_64-linux-gnu/libgstreamer-1.0.so.0.2402.0":
        "4207e0d9abcbcf3245aecc582c543d456cea131c4ed3a1d7033eea84150704b0",
}
CAPS = "audio/x-raw,format=S16LE,rate=16000,channels=1,layout=interleaved"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_gstreamer_runtime() -> dict[str, Any]:
    completed = subprocess.run(
        ["gst-launch-1.0", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0 or f"version {GSTREAMER_VERSION}" not in completed.stdout:
        raise ValueError("pinned GStreamer runtime is unavailable")
    for raw_path, expected in GSTREAMER_COMPONENTS.items():
        path = Path(raw_path)
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"GStreamer runtime component identity mismatch: {path.name}")
    return {
        "runtime": "GStreamer",
        "version": GSTREAMER_VERSION,
        "architecture": "x86_64",
        "components": [
            {"path": path, "sha256": digest}
            for path, digest in GSTREAMER_COMPONENTS.items()
        ],
        "pipeline": [
            "filesrc",
            "mpegaudioparse",
            "mpg123audiodec",
            "audioconvert",
            "audioresample quality=10",
            CAPS,
            "wavenc",
            "filesink",
        ],
    }


def _validate_wav(path: Path) -> tuple[int, float]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(),
            source.getnchannels(),
            source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (SAMPLE_RATE_HZ, 1, 2, "NONE"):
            raise ValueError(f"derived WAV identity mismatch: {path.name}")
        frames = source.getnframes()
    if frames <= 0:
        raise ValueError(f"derived WAV is empty: {path.name}")
    return frames, frames / SAMPLE_RATE_HZ


def _controlled_reference_records(
    source_lock: dict[str, Any], controlled_selection: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    if controlled_selection.get("git_safety") != "CONTROLLED_REFERENCE_TEXT_DO_NOT_COMMIT":
        raise ValueError("Common Voice controlled selection safety marker mismatch")
    if controlled_selection.get("source_lock_id") != COMMON_VOICE_SOURCE_LOCK_ID:
        raise ValueError("Common Voice controlled selection source-lock mismatch")
    raw_records = controlled_selection.get("records")
    if not isinstance(raw_records, list) or len(raw_records) != 12:
        raise ValueError("Common Voice controlled selection must contain twelve records")
    by_id: dict[str, dict[str, Any]] = {}
    expected = {
        str(record["clip_id"]): record
        for record in source_lock["selection"]["records"]
    }
    for record in raw_records:
        if not isinstance(record, dict):
            raise ValueError("invalid Common Voice controlled-selection record")
        clip_id = str(record.get("clip_id", ""))
        reference = str(record.get("reference_text", ""))
        locked = expected.get(clip_id)
        if locked is None or clip_id in by_id:
            raise ValueError("unknown or duplicate controlled Common Voice clip")
        for field in (
            "archive_member_path",
            "selection_rank_sha256",
            "reference_sha256",
            "source_mp3_size_bytes",
            "source_mp3_sha256",
        ):
            if record.get(field) != locked.get(field):
                raise ValueError(f"controlled Common Voice identity mismatch: {clip_id}")
        if not reference or _sha256_text(reference) != locked["reference_sha256"]:
            raise ValueError(f"controlled Common Voice reference mismatch: {clip_id}")
        by_id[clip_id] = record
    if set(by_id) != set(expected):
        raise ValueError("controlled Common Voice clip set differs from source lock")
    return by_id


def _derive_internal(
    internal_lock: dict[str, Any], plan: dict[str, Any], labels: dict[str, Any],
    fixture_dir: Path, output_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = select_internal_fixtures(plan, labels)
    locked = internal_lock["selection"]["records"]
    if [item["fixture_id"] for item in selected] != [item["fixture_id"] for item in locked]:
        raise ValueError("current internal selection differs from source lock")
    label_by_id = {
        str(record["fixture_id"]): record
        for record in labels["records"]
    }
    manifest_path = fixture_dir / "delivered_fixture_manifest.json"
    if sha256_file(manifest_path) != DELIVERED_MANIFEST_SHA256:
        raise ValueError("delivered fixture manifest checksum mismatch")
    manifest = load_json(manifest_path)
    controlled: list[dict[str, Any]] = []
    sanitized: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True)
    for item, source_identity in zip(selected, locked, strict=True):
        fixture_id = str(item["fixture_id"])
        source_record = manifest["records"].get(fixture_id)
        if not isinstance(source_record, dict):
            raise ValueError(f"delivered fixture record missing: {fixture_id}")
        source_path = fixture_dir / str(source_record["file"])
        if (
            source_path.stat().st_size != source_identity["source_wav_size_bytes"]
            or sha256_file(source_path) != source_identity["source_wav_sha256"]
        ):
            raise ValueError(f"internal source WAV identity mismatch: {fixture_id}")
        intervals = label_by_id[fixture_id]["speech_intervals_ms"]
        start_ms, end_ms = intervals[0][0], intervals[-1][1]
        if end_ms - start_ms != item["bounded_duration_ms"]:
            raise ValueError(f"internal bounded duration mismatch: {fixture_id}")
        start_frame = start_ms * SAMPLE_RATE_HZ // 1000
        end_frame = end_ms * SAMPLE_RATE_HZ // 1000
        with wave.open(str(source_path), "rb") as source:
            if (
                source.getframerate(), source.getnchannels(), source.getsampwidth(),
                source.getcomptype(),
            ) != (SAMPLE_RATE_HZ, 1, 2, "NONE"):
                raise ValueError(f"internal source PCM identity mismatch: {fixture_id}")
            if end_frame > source.getnframes() or start_frame >= end_frame:
                raise ValueError(f"internal frozen bounds are outside source: {fixture_id}")
            source.setpos(start_frame)
            payload = source.readframes(end_frame - start_frame)
        destination = output_dir / f"{fixture_id}.wav"
        with destination.open("xb") as destination_file:
            with wave.open(destination_file, "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(SAMPLE_RATE_HZ)
                target.writeframes(payload)
        frames, duration = _validate_wav(destination)
        record = {
            "fixture_id": fixture_id,
            "group": item["group"],
            "reference_sha256": item["reference_sha256"],
            "source_wav_sha256": source_identity["source_wav_sha256"],
            "derived_wav_sha256": sha256_file(destination),
            "derived_wav_size_bytes": destination.stat().st_size,
            "frames": frames,
            "duration_seconds": round(duration, 6),
            "derivation": "contiguous_first_speech_start_to_last_speech_end_preserve_pause",
        }
        sanitized.append(record)
        controlled.append({
            **record,
            "reference_text": next(
                str(plan_item["reference_text"])
                for plan_item in plan["utterances"]
                if plan_item["fixture_id"] == fixture_id
            ),
            "relative_wav_path": f"internal/{destination.name}",
        })
    return controlled, sanitized


def _convert_common_voice(
    source_lock: dict[str, Any], controlled_selection: dict[str, Any],
    clips_dir: Path, output_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    references = _controlled_reference_records(source_lock, controlled_selection)
    controlled: list[dict[str, Any]] = []
    sanitized: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True)
    for source_identity in source_lock["selection"]["records"]:
        clip_id = str(source_identity["clip_id"])
        source_path = clips_dir / clip_id
        if (
            source_path.stat().st_size != source_identity["source_mp3_size_bytes"]
            or sha256_file(source_path) != source_identity["source_mp3_sha256"]
        ):
            raise ValueError(f"Common Voice source MP3 identity mismatch: {clip_id}")
        destination = output_dir / f"{Path(clip_id).stem}.wav"
        command = [
            "gst-launch-1.0", "-q",
            "filesrc", f"location={source_path}", "!",
            "mpegaudioparse", "!", "mpg123audiodec", "!",
            "audioconvert", "!", "audioresample", "quality=10", "!",
            CAPS, "!", "wavenc", "!", "filesink", f"location={destination}",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Common Voice conversion failed: {clip_id}")
        frames, duration = _validate_wav(destination)
        record = {
            "clip_id": clip_id,
            "selection_rank_sha256": source_identity["selection_rank_sha256"],
            "reference_sha256": source_identity["reference_sha256"],
            "source_mp3_sha256": source_identity["source_mp3_sha256"],
            "derived_wav_sha256": sha256_file(destination),
            "derived_wav_size_bytes": destination.stat().st_size,
            "frames": frames,
            "duration_seconds": round(duration, 6),
            "derivation": "gstreamer_mpg123_decode_resample_16k_mono_s16le",
        }
        sanitized.append(record)
        controlled.append({
            **record,
            "reference_text": references[clip_id]["reference_text"],
            "relative_wav_path": f"common_voice/{destination.name}",
        })
    return controlled, sanitized


def validate_fixture_lock(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0" or document.get("fixture_lock_id") != FIXTURE_LOCK_ID:
        raise ValueError("M2A fixture-lock identity mismatch")
    if document.get("status") != "LOCKED_NOT_EXECUTED":
        raise ValueError("M2A fixture-lock status mismatch")
    if document.get("packet_id") != PACKET_ID:
        raise ValueError("M2A fixture-lock packet mismatch")
    if document.get("source_locks") != {
        "internal": INTERNAL_SOURCE_LOCK_ID,
        "common_voice": COMMON_VOICE_SOURCE_LOCK_ID,
    }:
        raise ValueError("M2A fixture-lock source identities mismatch")
    records = document.get("records", {})
    internal = records.get("internal")
    external = records.get("common_voice")
    if not isinstance(internal, list) or len(internal) != 8:
        raise ValueError("M2A fixture lock must contain eight internal records")
    if not isinstance(external, list) or len(external) != 12:
        raise ValueError("M2A fixture lock must contain twelve Common Voice records")
    all_records = internal + external
    identities: set[str] = set()
    for record in all_records:
        if any(key in record for key in ("reference_text", "transcript", "relative_wav_path")):
            raise ValueError("tracked M2A fixture lock contains controlled data")
        for field in ("reference_sha256", "derived_wav_sha256"):
            value = str(record.get(field, ""))
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"invalid M2A fixture-lock {field}")
        if record.get("frames", 0) <= 0 or record.get("duration_seconds", 0) <= 0:
            raise ValueError("invalid M2A derived fixture duration")
        if record.get("derived_wav_size_bytes", 0) <= 44:
            raise ValueError("invalid M2A derived fixture byte size")
        identity = str(record.get("fixture_id", record.get("clip_id", "")))
        if not identity or identity in identities:
            raise ValueError("invalid or duplicate M2A fixture identity")
        identities.add(identity)
    pcm = document.get("pcm")
    if pcm != {"sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE"}:
        raise ValueError("M2A fixture-lock PCM identity mismatch")
    if document.get("candidate_execution") != "NOT_STARTED":
        raise ValueError("M2A fixture lock cannot claim candidate execution")
    runtime = document.get("conversion_runtime", {})
    if runtime.get("runtime") != "GStreamer" or runtime.get("version") != GSTREAMER_VERSION:
        raise ValueError("M2A fixture-lock conversion runtime mismatch")
    components = runtime.get("components")
    if not isinstance(components, list) or len(components) != len(GSTREAMER_COMPONENTS):
        raise ValueError("M2A fixture-lock conversion component count mismatch")
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("M2A fixture-lock conversion component mismatch")
        component_path = str(component.get("path", ""))
        if component_path not in GSTREAMER_COMPONENTS:
            raise ValueError("M2A fixture-lock conversion component mismatch")
        if component.get("sha256") != GSTREAMER_COMPONENTS[component_path]:
            raise ValueError("M2A fixture-lock conversion component checksum mismatch")
    controlled = document.get("controlled_manifest", {})
    controlled_sha = str(controlled.get("sha256", ""))
    if (
        len(controlled_sha) != 64
        or any(character not in "0123456789abcdef" for character in controlled_sha)
        or controlled.get("size_bytes", 0) <= 0
        or controlled.get("git_policy") != "CONTROLLED_DO_NOT_COMMIT"
    ):
        raise ValueError("M2A controlled-manifest identity mismatch")


def build_fixture_lock(
    packet_path: Path, internal_lock_path: Path, common_voice_lock_path: Path,
    plan_path: Path, label_path: Path, fixture_dir: Path,
    controlled_selection_path: Path, common_voice_clips_dir: Path,
    output_dir: Path, sanitized_output: Path,
) -> dict[str, Any]:
    packet = load_json(packet_path)
    internal_lock = load_json(internal_lock_path)
    common_voice_lock = load_json(common_voice_lock_path)
    validate_packet(packet)
    validate_internal_source_lock(internal_lock)
    validate_common_voice_source_lock(common_voice_lock)
    if sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("frozen recording-plan checksum mismatch")
    if sha256_file(label_path) != LABEL_INDEX_SHA256:
        raise ValueError("frozen VAD-label checksum mismatch")
    if output_dir.exists():
        raise ValueError("controlled M2A fixture-lock output must be new")
    if sanitized_output.exists():
        raise ValueError("sanitized M2A fixture-lock output already exists")
    runtime = validate_gstreamer_runtime()
    plan = load_json(plan_path)
    labels = load_json(label_path)
    controlled_selection = load_json(controlled_selection_path)
    output_dir.mkdir(parents=True)
    internal_controlled, internal_sanitized = _derive_internal(
        internal_lock, plan, labels, fixture_dir, output_dir / "internal"
    )
    external_controlled, external_sanitized = _convert_common_voice(
        common_voice_lock, controlled_selection, common_voice_clips_dir,
        output_dir / "common_voice",
    )
    controlled = {
        "schema_version": "1.0",
        "fixture_lock_id": FIXTURE_LOCK_ID,
        "git_safety": "CONTROLLED_REFERENCE_TEXT_AND_AUDIO_PATHS_DO_NOT_COMMIT",
        "records": {
            "internal": internal_controlled,
            "common_voice": external_controlled,
        },
    }
    controlled_path = output_dir / "fixture_lock.controlled.json"
    controlled_path.write_text(
        json.dumps(controlled, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sanitized = {
        "schema_version": "1.0",
        "fixture_lock_id": FIXTURE_LOCK_ID,
        "status": "LOCKED_NOT_EXECUTED",
        "packet_id": PACKET_ID,
        "source_locks": {
            "internal": INTERNAL_SOURCE_LOCK_ID,
            "common_voice": COMMON_VOICE_SOURCE_LOCK_ID,
        },
        "pcm": {"sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE"},
        "conversion_runtime": runtime,
        "controlled_manifest": {
            "sha256": sha256_file(controlled_path),
            "size_bytes": controlled_path.stat().st_size,
            "git_policy": "CONTROLLED_DO_NOT_COMMIT",
        },
        "records": {
            "internal": internal_sanitized,
            "common_voice": external_sanitized,
        },
        "candidate_execution": "NOT_STARTED",
    }
    validate_fixture_lock(sanitized)
    sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    sanitized_output.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "result": "PASS",
        "fixture_lock_id": FIXTURE_LOCK_ID,
        "status": "LOCKED_NOT_EXECUTED",
        "internal_count": len(internal_sanitized),
        "common_voice_count": len(external_sanitized),
        "sanitized_manifest_sha256": sha256_file(sanitized_output),
    }


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=root / "poc_audio/manifests/m4a_m2a_common_packet.json")
    parser.add_argument("--internal-source-lock", type=Path, default=root / "poc_audio/manifests/m4a_m2a_internal_source_lock.json")
    parser.add_argument("--common-voice-source-lock", type=Path, default=root / "poc_audio/manifests/m4a_m2a_common_voice_source_lock.json")
    parser.add_argument("--recording-plan", type=Path, default=root / "poc_audio/fixtures/authorized/recording_plan_v1.json")
    parser.add_argument("--vad-label-index", type=Path, required=True)
    parser.add_argument("--internal-fixture-dir", type=Path, required=True)
    parser.add_argument("--common-voice-controlled-selection", type=Path, required=True)
    parser.add_argument("--common-voice-clips-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_fixture_lock(
        args.packet,
        args.internal_source_lock,
        args.common_voice_source_lock,
        args.recording_plan,
        args.vad_label_index,
        args.internal_fixture_dir,
        args.common_voice_controlled_selection,
        args.common_voice_clips_dir,
        args.output_dir,
        args.sanitized_output,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
