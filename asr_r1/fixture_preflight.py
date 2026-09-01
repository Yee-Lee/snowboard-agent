"""Fail-closed validation for the controlled AR1M1 smoke fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path

from .paths import resolve_repo_resource


DEFAULT_MANIFEST = "asr_r1/manifests/m1_smoke_fixture.json"


@dataclass(frozen=True)
class FixtureIdentity:
    fixture_id: str
    path: Path
    sha256: str
    size_bytes: int
    frames: int
    duration_seconds: float
    speech_start_offset_ms: int
    speech_end_offset_ms: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _external_path(repo_root: Path, path: Path, kind: str) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{kind} must remain outside the repository")


def verify_controlled_smoke_fixture(
    repo_root: Path,
    controlled_wav: Path,
    manifest_relative: str = DEFAULT_MANIFEST,
) -> FixtureIdentity:
    """Verify an operator-supplied external WAV against the frozen manifest."""

    manifest_path = resolve_repo_resource(repo_root, manifest_relative)
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    repo_root = repo_root.resolve()
    controlled_wav = _external_path(repo_root, controlled_wav, "controlled audio")
    if not controlled_wav.is_file():
        raise FileNotFoundError(controlled_wav)

    expected = manifest["pcm"]
    actual_size = controlled_wav.stat().st_size
    if actual_size != expected["size_bytes"]:
        raise ValueError(
            f"fixture size mismatch: expected {expected['size_bytes']}, got {actual_size}"
        )
    actual_sha256 = _sha256(controlled_wav)
    if actual_sha256 != expected["sha256"]:
        raise ValueError("fixture SHA-256 mismatch")

    with wave.open(str(controlled_wav), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frames = source.getnframes()
        compression = source.getcomptype()
    actual_format = (channels, sample_width, sample_rate, frames, compression)
    expected_format = (
        expected["channels"],
        2,
        expected["sample_rate_hz"],
        expected["frames"],
        "NONE",
    )
    if actual_format != expected_format:
        raise ValueError(
            f"fixture WAV format mismatch: expected {expected_format}, got {actual_format}"
        )

    duration_seconds = frames / sample_rate
    if abs(duration_seconds - expected["duration_seconds"]) > 0.000001:
        raise ValueError("fixture duration mismatch")

    speech = manifest["speech_interval"]
    source_interval = speech["source_end_ms"] - speech["source_start_ms"]
    derived_interval = speech["derived_end_ms"] - speech["derived_start_ms"]
    duration_ms = frames * 1_000 // sample_rate
    if (
        speech["annotation_status"] != "HUMAN_REVIEWED_FROZEN"
        or speech["source_start_ms"] != expected["crop_start_ms"]
        or speech["source_end_ms"] != expected["crop_end_ms"]
        or speech["derived_start_ms"] != 0
        or source_interval != derived_interval
        or speech["derived_end_ms"] != duration_ms
    ):
        raise ValueError("fixture speech interval mismatch")
    return FixtureIdentity(
        fixture_id=manifest["fixture_id"],
        path=controlled_wav,
        sha256=actual_sha256,
        size_bytes=actual_size,
        frames=frames,
        duration_seconds=duration_seconds,
        speech_start_offset_ms=speech["derived_start_ms"],
        speech_end_offset_ms=speech["derived_end_ms"],
    )


def restore_controlled_smoke_fixture(
    repo_root: Path,
    source_wav: Path,
    output_wav: Path,
    manifest_relative: str = DEFAULT_MANIFEST,
) -> FixtureIdentity:
    """Reproduce the frozen crop from an exact external historical source WAV."""

    repo_root = repo_root.resolve()
    source_wav = _external_path(repo_root, source_wav, "source audio")
    output_wav = _external_path(repo_root, output_wav, "derived audio")
    if output_wav.exists():
        raise FileExistsError(output_wav)
    manifest_path = resolve_repo_resource(repo_root, manifest_relative)
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected = manifest["pcm"]
    if not source_wav.is_file():
        raise FileNotFoundError(source_wav)
    if source_wav.stat().st_size != expected["source_size_bytes"]:
        raise ValueError("source fixture size mismatch")
    if _sha256(source_wav) != expected["source_fixture_sha256"]:
        raise ValueError("source fixture SHA-256 mismatch")

    with wave.open(str(source_wav), "rb") as source:
        source_format = (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
            source.getnframes(),
            source.getcomptype(),
        )
        expected_source_format = (
            expected["channels"],
            2,
            expected["sample_rate_hz"],
            expected["source_frames"],
            "NONE",
        )
        if source_format != expected_source_format:
            raise ValueError("source fixture WAV format mismatch")
        start_frame = (
            expected["crop_start_ms"] * expected["sample_rate_hz"] // 1_000
        )
        end_frame = expected["crop_end_ms"] * expected["sample_rate_hz"] // 1_000
        if end_frame - start_frame != expected["frames"]:
            raise ValueError("frozen crop frame count mismatch")
        source.setpos(start_frame)
        payload = source.readframes(end_frame - start_frame)

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_wav.open("xb") as destination:
            with wave.open(destination, "wb") as target:
                target.setnchannels(expected["channels"])
                target.setsampwidth(2)
                target.setframerate(expected["sample_rate_hz"])
                target.writeframes(payload)
        return verify_controlled_smoke_fixture(
            repo_root, output_wav, manifest_relative=manifest_relative
        )
    except Exception:
        output_wav.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    identity = restore_controlled_smoke_fixture(repo_root, args.source, args.output)
    print(
        json.dumps(
            {
                "fixture_id": identity.fixture_id,
                "sha256": identity.sha256,
                "size_bytes": identity.size_bytes,
                "frames": identity.frames,
                "duration_seconds": identity.duration_seconds,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
