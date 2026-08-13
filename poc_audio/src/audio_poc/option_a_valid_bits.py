"""Analyze authorized native WAVs for P4-A02 channel and valid-bit evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path
from typing import Any


def analyze_fixture_directory(fixture_dir: Path, output_path: Path) -> dict[str, Any]:
    import numpy

    manifest_path = fixture_dir / "fixture_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["records"]
    channel_count = 2
    counts = numpy.zeros(channel_count, dtype=numpy.int64)
    nonzero = numpy.zeros(channel_count, dtype=numpy.int64)
    low8_or = numpy.zeros(channel_count, dtype=numpy.int64)
    decoded_low8_or = numpy.zeros(channel_count, dtype=numpy.int64)
    right_aligned_matches = numpy.zeros(channel_count, dtype=numpy.int64)
    near_full_scale = numpy.zeros(channel_count, dtype=numpy.int64)
    minimum = numpy.full(channel_count, 2**31 - 1, dtype=numpy.int64)
    maximum = numpy.full(channel_count, -(2**31), dtype=numpy.int64)
    square_sum = numpy.zeros(channel_count, dtype=numpy.float64)
    analyzed_ids = []

    for fixture_id, record in sorted(records.items()):
        path = fixture_dir / record["file"]
        with wave.open(str(path), "rb") as source:
            metadata = (
                source.getframerate(),
                source.getnchannels(),
                source.getsampwidth(),
            )
            if metadata != (48_000, 2, 4):
                raise ValueError(f"unexpected native format for {fixture_id}: {metadata}")
            values = numpy.frombuffer(
                source.readframes(source.getnframes()), dtype="<i4"
            ).reshape(-1, 2).astype(numpy.int64)
        counts += values.shape[0]
        nonzero += (values != 0).sum(axis=0)
        low8_or = numpy.bitwise_or(
            low8_or, numpy.bitwise_or.reduce(values & 0xFF, axis=0)
        )
        decoded_low8_or = numpy.bitwise_or(
            decoded_low8_or,
            numpy.bitwise_or.reduce((values >> 8) & 0xFF, axis=0),
        )
        low24 = values & 0xFFFFFF
        sign_extended_24 = (low24 ^ 0x800000) - 0x800000
        right_aligned_matches += (values == sign_extended_24).sum(axis=0)
        near_full_scale += (numpy.abs(values) >= int(0.99 * (2**31 - 1))).sum(
            axis=0
        )
        minimum = numpy.minimum(minimum, values.min(axis=0))
        maximum = numpy.maximum(maximum, values.max(axis=0))
        square_sum += (values.astype(numpy.float64) ** 2).sum(axis=0)
        analyzed_ids.append(fixture_id)

    channels = []
    for index in range(channel_count):
        rms = math.sqrt(float(square_sum[index]) / int(counts[index]))
        rms_dbfs = 20.0 * math.log10(max(rms, 1e-12) / (2**31 - 1))
        channels.append(
            {
                "channel_index": index,
                "sample_count": int(counts[index]),
                "nonzero_samples": int(nonzero[index]),
                "container_low8_or": int(low8_or[index]),
                "decoded_low8_or": int(decoded_low8_or[index]),
                "right_aligned_24_match_count": int(right_aligned_matches[index]),
                "near_full_scale_samples": int(near_full_scale[index]),
                "minimum": int(minimum[index]),
                "maximum": int(maximum[index]),
                "rms_dbfs": rms_dbfs,
            }
        )

    active = channels[0]
    silent = channels[1]
    mapping_supported = (
        active["nonzero_samples"] > 0
        and silent["nonzero_samples"] == 0
        and active["container_low8_or"] == 0
        and active["decoded_low8_or"] == 0xFF
        and active["right_aligned_24_match_count"] < active["sample_count"]
    )
    speech_ids = [
        fixture_id
        for fixture_id, record in sorted(records.items())
        if record["vad_class"] in {"clear_speech", "pause"}
    ]
    result = {
        "schema_version": "1.0",
        "source_sha": manifest["source_sha"],
        "authorization_confirmed": bool(manifest["authorization_confirmed"]),
        "file_count": len(analyzed_ids),
        "speech_label_count": len(speech_ids),
        "native_format": {
            "rate_hz": 48_000,
            "channels": 2,
            "container": "S32_LE",
        },
        "channels": channels,
        "supported_mapping": {
            "channel_index": 0,
            "valid_bits": 24,
            "alignment": "left",
            "sign": "two's-complement arithmetic right shift",
            "normalized_formula": "float32(s32_container >> 8) / 8388608",
            "s16_formula": "clip(round(normalized * 32768), -32768, 32767)",
        },
        "mapping_supported_by_raw_analysis": mapping_supported,
        "known_signal_basis": (
            "authorized speech/pause fixtures with prior representative human label review"
        ),
        "raw_audio_emitted": False,
        "result": "PASS" if mapping_supported and speech_ids else "INCONCLUSIVE",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze_fixture_directory(args.fixture_dir, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
