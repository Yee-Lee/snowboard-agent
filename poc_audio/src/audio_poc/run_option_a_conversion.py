"""Run deterministic P4-A03 through A05 conversion validation."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any, Iterable

from .option_a_conversion import (
    OptionAStreamConverter,
    ValidBitMapping,
    float_to_s16le,
)
from .option_a_fixtures import IRREGULAR_CHUNK_SAMPLES, generate_fixtures


def encode_left_aligned_s32_stereo(samples: Any, numpy_module: Any) -> bytes:
    scale = 1 << 23
    clipped = numpy_module.clip(samples, -1.0, 1.0 - (1.0 / scale))
    valid = numpy_module.rint(clipped * scale).astype(numpy_module.int64)
    containers = (valid << 8).astype("<i4")
    stereo = numpy_module.zeros((containers.size, 2), dtype="<i4")
    stereo[:, 0] = containers
    return stereo.tobytes()


def irregular_byte_chunks(payload: bytes) -> Iterable[bytes]:
    sample_bytes = 8
    offset = 0
    index = 0
    while offset < len(payload):
        samples = IRREGULAR_CHUNK_SAMPLES[index % len(IRREGULAR_CHUNK_SAMPLES)]
        nominal = samples * sample_bytes
        # Add non-container-aligned boundaries; feed() must retain those bytes.
        size = max(1, nominal + (-3 if index % 2 else 5))
        yield payload[offset : offset + size]
        offset += size
        index += 1


def rms(values: Any, numpy_module: Any) -> float:
    if not values.size:
        return 0.0
    return float(numpy_module.sqrt(numpy_module.mean(values.astype("float64") ** 2)))


def run(output_dir: Path) -> dict[str, Any]:
    import numpy

    output_dir.mkdir(parents=True, exist_ok=False)
    fixture_dir = output_dir / "fixtures"
    fixture_manifest = generate_fixtures(fixture_dir)
    mapping = ValidBitMapping(channel_index=0, valid_bits=24, alignment="left")
    results = []
    for fixture in fixture_manifest["fixtures"]:
        source = numpy.fromfile(fixture_dir / fixture["path"], dtype="<f4")
        raw = encode_left_aligned_s32_stereo(source, numpy)
        converter = OptionAStreamConverter(mapping, converter_type="sinc_best")
        frames = []
        chunks = irregular_byte_chunks(raw)
        for chunk in chunks:
            frames.extend(converter.feed(chunk))
        flushed = converter.flush()
        frames.extend(flushed.frames)
        pcm = b"".join(frames) + flushed.partial_pcm
        output = numpy.frombuffer(pcm, dtype="<i2")
        record: dict[str, Any] = {
            "fixture_id": fixture["fixture_id"],
            "input_samples": converter.total_input_samples,
            "resampled_samples": converter.total_resampled_samples,
            "filter_drain_input_samples": converter.drain_input_samples,
            "full_frame_count": len(frames),
            "frame_bytes_all_640": all(len(frame) == 640 for frame in frames),
            "partial_output_samples": len(flushed.partial_pcm) // 2,
            "output_samples": int(output.size),
            "output_min": int(output.min(initial=0)),
            "output_max": int(output.max(initial=0)),
        }
        if fixture["fixture_id"] in {"sine-1khz", "sine-12khz"}:
            steady = output[1000:-1000]
            output_rms = rms(steady, numpy)
            reference_rms = (0.5 / math.sqrt(2.0)) * 32768.0
            record["steady_rms"] = output_rms
            record["relative_db"] = 20.0 * math.log10(
                max(output_rms, 1e-12) / reference_rms
            )
        results.append(record)

    saturation = numpy.frombuffer(
        float_to_s16le(numpy.array([-2.0, -1.0, 0.0, 1.0, 2.0]), numpy),
        dtype="<i2",
    ).tolist()
    by_id = {record["fixture_id"]: record for record in results}
    failures = []
    for record in results:
        if record["input_samples"] != 48_000:
            failures.append(f"{record['fixture_id']}: input sample loss")
        if not record["frame_bytes_all_640"]:
            failures.append(f"{record['fixture_id']}: non-640-byte full frame")
        if record["output_samples"] != 16_000:
            failures.append(f"{record['fixture_id']}: output ratio mismatch")
        if record["full_frame_count"] != 50 or record["partial_output_samples"] != 0:
            failures.append(f"{record['fixture_id']}: incomplete final framing")
    if by_id["sine-12khz"]["relative_db"] > -40.0:
        failures.append("sine-12khz: alias attenuation below 40 dB")
    if saturation != [-32768, -32768, 0, 32767, 32767]:
        failures.append("S16 conversion wrapped instead of saturating")
    summary = {
        "schema_version": "1.0",
        "mapping": {
            "scope": "deterministic seam only; P4-A02 target mapping pending",
            "channel_index": 0,
            "valid_bits": 24,
            "alignment": "left",
        },
        "converter_type": "sinc_best",
        "ratio": 1.0 / 3.0,
        "frame_samples": 320,
        "saturation_vector": saturation,
        "results": results,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
    }
    (output_dir / "conversion-results.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    summary = run(args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
