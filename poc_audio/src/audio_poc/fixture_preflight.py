"""Prepare the M1 Pilot for the approved observation-only ASR preflight."""

from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

from .fixture_recorder import (
    build_capture_items,
    load_plan,
    select_stage_items,
    sha256_file,
    verify_records,
    write_json_atomically,
)


MANIFEST_NAME = "asr_preflight_manifest.json"
PREPARER_ID = "m1-pilot-asr-preflight-v1"
SOURCE_RATE_HZ = 48000
DELIVERED_RATE_HZ = 16000
SOURCE_CHANNEL = 0
TAPS = 63
CUTOFF_HZ = 7200.0


def fir_coefficients() -> list[float]:
    """Return pinned Blackman-windowed low-pass coefficients."""
    cutoff = CUTOFF_HZ / SOURCE_RATE_HZ
    midpoint = TAPS // 2
    coefficients: list[float] = []
    for index in range(TAPS):
        distance = index - midpoint
        ideal = 2 * cutoff if distance == 0 else math.sin(2 * math.pi * cutoff * distance) / (math.pi * distance)
        window = 0.42 - 0.5 * math.cos(2 * math.pi * index / (TAPS - 1)) + 0.08 * math.cos(4 * math.pi * index / (TAPS - 1))
        coefficients.append(ideal * window)
    scale = sum(coefficients)
    return [coefficient / scale for coefficient in coefficients]


def convert_native_to_preflight(source: Path, destination: Path) -> dict[str, int | float]:
    """Select channel 0, low-pass, and decimate native S32 WAV to mono S16."""
    with wave.open(str(source), "rb") as input_wav:
        if (input_wav.getframerate(), input_wav.getnchannels(), input_wav.getsampwidth()) != (SOURCE_RATE_HZ, 2, 4):
            raise ValueError("source must be native 48 kHz stereo S32_LE WAV")
        payload = input_wav.readframes(input_wav.getnframes())
    interleaved = array.array("i")
    interleaved.frombytes(payload)
    if sys.byteorder != "little":
        interleaved.byteswap()
    samples = list(interleaved[SOURCE_CHANNEL::2])
    if len(samples) % 3:
        raise ValueError("source frame count must be divisible by three")
    coefficients = fir_coefficients()
    midpoint = TAPS // 2
    output = array.array("h")
    for center in range(0, len(samples), 3):
        filtered = sum(
            samples[index] * coefficient
            for offset, coefficient in enumerate(coefficients)
            if 0 <= (index := center + offset - midpoint) < len(samples)
        )
        output.append(max(-32768, min(32767, round(filtered / 65536.0))))
    if sys.byteorder != "little":
        output.byteswap()
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with wave.open(str(temporary), "wb") as output_wav:
            output_wav.setnchannels(1)
            output_wav.setsampwidth(2)
            output_wav.setframerate(DELIVERED_RATE_HZ)
            output_wav.writeframes(output.tobytes())
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    metadata = {
        "channels": 1,
        "sample_width_bytes": 2,
        "sample_rate_hz": DELIVERED_RATE_HZ,
        "frames": len(output),
        "duration_seconds": round(len(output) / DELIVERED_RATE_HZ, 3),
    }
    if len(output) != len(samples) // 3:
        raise ValueError("preflight conversion returned an unexpected frame count")
    return metadata


def _source_sha(repo_root: Path) -> str:
    return subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()


def prepare_pilot(plan: dict[str, Any], plan_path: Path, input_dir: Path, output_dir: Path, repo_root: Path, replace: bool) -> dict[str, Any]:
    items = select_stage_items(plan, build_capture_items(plan), "pilot")
    verified = verify_records(plan, input_dir, items, "pilot")
    if verified["issues"]:
        raise ValueError("Pilot native fixture validation did not pass")
    input_manifest_path = input_dir / "fixture_manifest.json"
    if not input_manifest_path.is_file():
        raise ValueError("Pilot fixture_manifest.json is unavailable")
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    if manifest_path.exists() and not replace:
        raise ValueError("preflight manifest exists; pass --replace to recreate it")
    records: dict[str, Any] = {}
    for item in items:
        source = input_dir / str(input_manifest["records"][item.fixture_id]["file"])
        destination = output_dir / f"{item.fixture_id}.wav"
        if destination.exists() and not replace:
            raise ValueError(f"derived preflight WAV exists: {destination.name}")
        metadata = convert_native_to_preflight(source, destination)
        records[item.fixture_id] = {
            "fixture_id": item.fixture_id,
            "vad_class": item.vad_class,
            "category": item.category,
            "file": destination.name,
            "native_sha256": sha256_file(source),
            "derived_sha256": sha256_file(destination),
            "metadata": metadata,
        }
    document = {
        "schema_version": "1.0", "preparer_id": PREPARER_ID,
        "purpose": "non_decisive_asr_preflight",
        "gate_effect": "observation_only_no_advance_reject_or_winner",
        "source_sha": _source_sha(repo_root), "plan_id": plan["plan_id"],
        "plan_sha256": sha256_file(plan_path),
        "pilot_native_manifest_sha256": sha256_file(input_manifest_path),
        "pilot_source_sha": input_manifest.get("source_sha", "unavailable"),
        "native_input": {"sample_rate_hz": 48000, "channels": 2, "sample_format": "S32_LE", "source_channel": SOURCE_CHANNEL},
        "delivered_preflight": {"sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE", "filter": "63_tap_blackman_sinc", "cutoff_hz": CUTOFF_HZ, "decimation_factor": 3},
        "records": records,
    }
    write_json_atomically(manifest_path, document)
    return {"result": "PASS", "purpose": document["purpose"], "gate_effect": document["gate_effect"], "valid_files": len(records), "source_sha": document["source_sha"], "preflight_manifest_sha256": sha256_file(manifest_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("poc_audio/fixtures/authorized/recording_plan_v1.json"))
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--replace", action="store_true")
    arguments = parser.parse_args(argv)
    if not arguments.prepare:
        raise SystemExit("pass --prepare to create a local Pilot preflight set")
    plan_path = arguments.plan.resolve()
    plan = load_plan(plan_path)
    plan["_path"] = str(plan_path)
    result = prepare_pilot(plan, plan_path, arguments.input_dir, arguments.output_dir, plan_path.parents[3], arguments.replace)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
