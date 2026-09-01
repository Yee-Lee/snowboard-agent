"""Fail-closed validation for the controlled AR1M1 smoke fixture."""

from __future__ import annotations

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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_controlled_smoke_fixture(
    repo_root: Path,
    controlled_wav: Path,
    manifest_relative: str = DEFAULT_MANIFEST,
) -> FixtureIdentity:
    """Verify an operator-supplied external WAV against the frozen manifest."""

    manifest_path = resolve_repo_resource(repo_root, manifest_relative)
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    controlled_wav = controlled_wav.expanduser().resolve()
    repo_root = repo_root.resolve()
    try:
        controlled_wav.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise ValueError("controlled audio must remain outside the repository")
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
    return FixtureIdentity(
        fixture_id=manifest["fixture_id"],
        path=controlled_wav,
        sha256=actual_sha256,
        size_bytes=actual_size,
        frames=frames,
        duration_seconds=duration_seconds,
    )
