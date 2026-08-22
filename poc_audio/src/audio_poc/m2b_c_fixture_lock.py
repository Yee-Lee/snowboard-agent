"""Derive the reviewed M2B C PCM fixture lock without candidate inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import wave
from typing import Any


LOCK_ID = "M2B-C-PCM-LOCK-001"
SELECTION_ID = "M2B-C-SOURCE-SELECTION-001"
SAMPLE_RATE_HZ = 16_000
PADDING_PROFILES_MS = (0, 300, 500)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _git_identity(root: Path) -> dict[str, Any]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
        timeout=10, check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True,
        timeout=10, check=True,
    ).stdout
    if status:
        raise ValueError("fixture lock requires a clean exact-SHA checkout")
    return {"git_sha": sha, "worktree": "CLEAN", "architecture": platform.machine()}


def _ffmpeg_identity() -> dict[str, Any]:
    binary = Path("/usr/bin/ffmpeg")
    if not binary.is_file():
        raise ValueError("required /usr/bin/ffmpeg is unavailable")
    completed = subprocess.run(
        [str(binary), "-version"], capture_output=True, text=True, timeout=10,
        check=True,
    )
    first_line = completed.stdout.splitlines()[0]
    return {
        "binary": str(binary),
        "binary_sha256": sha256_file(binary),
        "version_line": first_line,
        "version_output_sha256": sha256_text(completed.stdout),
        "command": [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i",
            "SOURCE", "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
            "-c:a", "pcm_s16le", "DESTINATION",
        ],
    }


def _wav_identity(path: Path) -> tuple[int, int]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (SAMPLE_RATE_HZ, 1, 2, "NONE"):
            raise ValueError(f"WAV is not 16 kHz mono S16_LE: {path.name}")
        frames = source.getnframes()
    if frames <= 0:
        raise ValueError(f"empty WAV: {path.name}")
    return frames, path.stat().st_size


def _validate_sources(
    tracked: dict[str, Any], controlled: dict[str, Any], selection_root: Path,
) -> list[dict[str, Any]]:
    if tracked.get("selection_id") != SELECTION_ID:
        raise ValueError("tracked C selection identity mismatch")
    if controlled.get("selection_id") != SELECTION_ID:
        raise ValueError("controlled C selection identity mismatch")
    expected_controlled = tracked.get("controlled_manifest", {})
    controlled_path = selection_root / "selection.controlled.json"
    if (
        controlled_path.stat().st_size != expected_controlled.get("size_bytes")
        or sha256_file(controlled_path) != expected_controlled.get("sha256")
    ):
        raise ValueError("controlled C selection checksum mismatch")
    records = controlled.get("records")
    if not isinstance(records, list) or len(records) != 24:
        raise ValueError("controlled C selection must contain 24 records")
    families = {"internal": 0, "common_voice": 0}
    splits = {"dev": 0, "holdout": 0}
    for record in records:
        family, split = record.get("family"), record.get("split")
        if family not in families or split not in splits:
            raise ValueError("invalid C family or split")
        families[family] += 1
        splits[split] += 1
        reference = str(record.get("selected_reference_text", ""))
        if not reference or sha256_text(reference) != record.get("selected_reference_sha256"):
            raise ValueError(f"C reference mismatch: {record.get('review_id')}")
        source = selection_root / str(record.get("source_relpath", ""))
        if (
            not source.is_file()
            or source.stat().st_size != record.get("source_size_bytes")
            or sha256_file(source) != record.get("source_sha256")
        ):
            raise ValueError(f"C source mismatch: {record.get('review_id')}")
    if families != {"internal": 16, "common_voice": 8}:
        raise ValueError("C family counts mismatch")
    if splits != {"dev": 12, "holdout": 12}:
        raise ValueError("C split counts mismatch")
    return records


def _write_wav(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as destination:
        with wave.open(destination, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(SAMPLE_RATE_HZ)
            target.writeframes(payload)


def _derive_internal(
    record: dict[str, Any], selection_root: Path, output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = selection_root / record["source_relpath"]
    start_ms, end_ms = int(record["speech_start_ms"]), int(record["speech_end_ms"])
    with wave.open(str(source_path), "rb") as source:
        if (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        ) != (SAMPLE_RATE_HZ, 1, 2, "NONE"):
            raise ValueError(f"internal source format mismatch: {record['review_id']}")
        total_frames = source.getnframes()
        variants = []
        controlled_variants = []
        for padding_ms in PADDING_PROFILES_MS:
            start_frame = max(0, (start_ms - padding_ms) * SAMPLE_RATE_HZ // 1000)
            end_frame = min(total_frames, (end_ms + padding_ms) * SAMPLE_RATE_HZ // 1000)
            source.setpos(start_frame)
            payload = source.readframes(end_frame - start_frame)
            profile = f"p{padding_ms}"
            destination = output_root / "internal" / profile / f"{record['fixture_id']}.wav"
            _write_wav(destination, payload)
            frames, size = _wav_identity(destination)
            variant = {
                "profile": profile,
                "requested_padding_ms_each_side": padding_ms,
                "start_ms": start_frame * 1000 // SAMPLE_RATE_HZ,
                "end_ms": end_frame * 1000 // SAMPLE_RATE_HZ,
                "frames": frames,
                "duration_seconds": round(frames / SAMPLE_RATE_HZ, 6),
                "derived_wav_size_bytes": size,
                "derived_wav_sha256": sha256_file(destination),
            }
            if padding_ms == 0 and (
                size != record["p0_preview_size_bytes"]
                or variant["derived_wav_sha256"] != record["p0_preview_sha256"]
            ):
                raise ValueError(f"P0 review preview mismatch: {record['review_id']}")
            variants.append(variant)
            controlled_variants.append({
                **variant,
                "relative_wav_path": str(destination.relative_to(output_root)),
            })
    base = {
        "review_id": record["review_id"],
        "split": record["split"],
        "fixture_id": record["fixture_id"],
        "category": record["category"],
        "reference_sha256": record["selected_reference_sha256"],
        "source_sha256": record["source_sha256"],
    }
    return {**base, "variants": variants}, {
        **base,
        "reference_text": record["selected_reference_text"],
        "variants": controlled_variants,
    }


def _derive_common_voice(
    record: dict[str, Any], selection_root: Path, output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = selection_root / record["source_relpath"]
    destination = output_root / "common_voice" / f"{Path(record['fixture_id']).stem}.wav"
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "/usr/bin/ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt",
        "s16", "-c:a", "pcm_s16le", str(destination),
    ]
    subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
    frames, size = _wav_identity(destination)
    base = {
        "review_id": record["review_id"],
        "split": record["split"],
        "fixture_id": record["fixture_id"],
        "category": record["category"],
        "reference_sha256": record["selected_reference_sha256"],
        "client_sha256": record["client_sha256"],
        "source_sha256": record["source_sha256"],
        "frames": frames,
        "duration_seconds": round(frames / SAMPLE_RATE_HZ, 6),
        "derived_wav_size_bytes": size,
        "derived_wav_sha256": sha256_file(destination),
        "derivation": "ffmpeg_decode_resample_full_clip_16k_mono_s16le",
    }
    return base, {
        **base,
        "reference_text": record["selected_reference_text"],
        "relative_wav_path": str(destination.relative_to(output_root)),
    }


def validate_lock(document: dict[str, Any]) -> None:
    if document.get("fixture_lock_id") != LOCK_ID or document.get("status") != "LOCKED_NOT_EXECUTED":
        raise ValueError("C PCM lock identity or status mismatch")
    records = document.get("records", {})
    internal, external = records.get("internal"), records.get("common_voice")
    if not isinstance(internal, list) or len(internal) != 16:
        raise ValueError("C PCM lock must contain 16 internal records")
    if not isinstance(external, list) or len(external) != 8:
        raise ValueError("C PCM lock must contain 8 Common Voice records")
    if sum(len(record.get("variants", [])) for record in internal) != 48:
        raise ValueError("C internal lock must contain P0/P300/P500 variants")
    if document.get("candidate_execution") != "NOT_STARTED":
        raise ValueError("C PCM lock cannot claim candidate execution")
    forbidden = {"reference_text", "transcript", "relative_wav_path"}
    if forbidden.intersection(json.dumps(document).split('"')):
        raise ValueError("sanitized C PCM lock contains controlled fields")


def build_lock(
    tracked_path: Path, controlled_path: Path, selection_root: Path,
    output_root: Path, sanitized_output: Path, repo: Path,
) -> dict[str, Any]:
    if output_root.exists() or sanitized_output.exists():
        raise ValueError("C fixture-lock outputs must be new")
    producer = _git_identity(repo)
    tracked, controlled = load_json(tracked_path), load_json(controlled_path)
    records = _validate_sources(tracked, controlled, selection_root)
    runtime = _ffmpeg_identity()
    output_root.mkdir(parents=True)
    internal, internal_controlled = [], []
    external, external_controlled = [], []
    for record in records:
        if record["family"] == "internal":
            sanitized, private = _derive_internal(record, selection_root, output_root)
            internal.append(sanitized)
            internal_controlled.append(private)
        else:
            sanitized, private = _derive_common_voice(record, selection_root, output_root)
            external.append(sanitized)
            external_controlled.append(private)
    controlled_lock = {
        "schema_version": "1.0",
        "fixture_lock_id": LOCK_ID,
        "git_policy": "CONTROLLED_REFERENCE_TEXT_AND_AUDIO_PATHS_DO_NOT_COMMIT",
        "records": {"internal": internal_controlled, "common_voice": external_controlled},
    }
    controlled_lock_path = output_root / "fixture_lock.controlled.json"
    controlled_lock_path.write_text(
        json.dumps(controlled_lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lock = {
        "schema_version": "1.0",
        "fixture_lock_id": LOCK_ID,
        "status": "LOCKED_NOT_EXECUTED",
        "source_selection_id": SELECTION_ID,
        "source_selection_manifest_sha256": sha256_file(tracked_path),
        "producer": producer,
        "pcm": {"sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE"},
        "internal_padding_profiles_ms_each_side": list(PADDING_PROFILES_MS),
        "common_voice_policy": "FULL_CLIP_NO_FROZEN_VAD_BOUNDS",
        "conversion_runtime": runtime,
        "controlled_manifest": {
            "sha256": sha256_file(controlled_lock_path),
            "size_bytes": controlled_lock_path.stat().st_size,
            "git_policy": "CONTROLLED_DO_NOT_COMMIT",
        },
        "counts": {
            "internal_records": 16,
            "internal_pcm_variants": 48,
            "common_voice_records": 8,
            "dev_records": 12,
            "holdout_records": 12,
        },
        "records": {"internal": internal, "common_voice": external},
        "candidate_execution": "NOT_STARTED",
    }
    validate_lock(lock)
    sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    sanitized_output.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "result": "PASS",
        "fixture_lock_id": LOCK_ID,
        "internal_records": 16,
        "internal_pcm_variants": 48,
        "common_voice_records": 8,
        "sanitized_manifest_sha256": sha256_file(sanitized_output),
    }


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracked-selection", type=Path, default=root / "poc_audio/manifests/m2b_c_source_selection.json")
    parser.add_argument("--controlled-selection", type=Path, required=True)
    parser.add_argument("--selection-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=root)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_lock(
        args.tracked_selection, args.controlled_selection, args.selection_root,
        args.output_root, args.sanitized_output, args.repo,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
