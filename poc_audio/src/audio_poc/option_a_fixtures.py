"""Generate deterministic float32 fixtures for P4 conversion validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


INPUT_RATE_HZ = 48_000
SAMPLE_COUNT = 48_000
IRREGULAR_CHUNK_SAMPLES = (1, 317, 2, 997, 41, 1600, 13, 479, 5, 809)


@dataclass(frozen=True, slots=True)
class FixtureCase:
    fixture_id: str
    purpose: str
    waveform: str


FIXTURE_CASES = (
    FixtureCase("sine-1khz", "pass-band amplitude and framing", "sine_1000"),
    FixtureCase("sine-12khz", "alias attenuation", "sine_12000"),
    FixtureCase("silence", "zero preservation", "silence"),
    FixtureCase("impulse", "filter state and delay", "impulse"),
    FixtureCase("clipping", "saturating S16 conversion without wrap", "clipping"),
    FixtureCase("irregular-chunks", "cross-chunk state and partial-frame handling", "sine_1000"),
)


def samples(case: FixtureCase) -> Iterable[float]:
    for index in range(SAMPLE_COUNT):
        if case.waveform == "silence":
            yield 0.0
        elif case.waveform == "impulse":
            yield 1.0 if index == 0 else 0.0
        elif case.waveform == "clipping":
            yield 1.25 if index % 2 == 0 else -1.25
        else:
            frequency = 1_000 if case.waveform == "sine_1000" else 12_000
            yield 0.5 * math.sin(2.0 * math.pi * frequency * index / INPUT_RATE_HZ)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_fixtures(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=False)
    records = []
    for case in FIXTURE_CASES:
        path = output_dir / f"{case.fixture_id}.f32le"
        with path.open("wb") as destination:
            for value in samples(case):
                destination.write(struct.pack("<f", value))
        records.append(
            {
                **asdict(case),
                "path": path.name,
                "sha256": sha256_file(path),
                "sample_format": "FLOAT32_LE_MONO",
                "sample_rate_hz": INPUT_RATE_HZ,
                "sample_count": SAMPLE_COUNT,
                "irregular_chunk_samples": (
                    list(IRREGULAR_CHUNK_SAMPLES)
                    if case.fixture_id == "irregular-chunks"
                    else None
                ),
            }
        )
    manifest = {"schema_version": "1.0", "fixtures": records}
    (output_dir / "fixture_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    manifest = generate_fixtures(args.output_dir)
    print(f"Generated {len(manifest['fixtures'])} deterministic fixtures: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
