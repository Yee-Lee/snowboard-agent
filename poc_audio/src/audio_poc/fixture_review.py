"""Sanitized technical review for an authorized M1 fixture collection."""

from __future__ import annotations

import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path
from typing import Any

from .fixture_recorder import (
    build_capture_items,
    load_plan,
    read_manifest,
    select_stage_items,
    validate_wav,
)


def _dbfs(value: float) -> float:
    return round(20 * math.log10(max(value, 1e-12)), 2)


def _channel_metrics(samples: array.array[int], rate: int) -> dict[str, int | float]:
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum((sample / 2147483648.0) ** 2 for sample in samples) / len(samples))
    block_size = max(1, rate // 10)
    block_dbfs = []
    for offset in range(0, len(samples), block_size):
        block = samples[offset : offset + block_size]
        block_rms = math.sqrt(
            sum((sample / 2147483648.0) ** 2 for sample in block) / len(block)
        )
        block_dbfs.append(_dbfs(block_rms))
    block_dbfs.sort()
    tenth = block_dbfs[max(0, int(0.1 * (len(block_dbfs) - 1)))]
    ninetieth = block_dbfs[int(0.9 * (len(block_dbfs) - 1))]
    return {
        "rms_dbfs": _dbfs(rms),
        "peak_dbfs": _dbfs(peak / 2147483648.0),
        "dynamic_range_db": round(ninetieth - tenth, 2),
        "near_full_scale_events": sum(abs(sample) >= 2147483392 for sample in samples),
        "nonzero_samples": sum(sample != 0 for sample in samples),
    }


def review_fixture(path: Path, native_capture: dict[str, Any], expected_duration: int) -> dict[str, Any]:
    metadata = validate_wav(path, native_capture, expected_duration)
    with wave.open(str(path), "rb") as source:
        payload = source.readframes(source.getnframes())
    values = array.array("i")
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    left = values[0::2]
    right = values[1::2]
    if not left:
        raise ValueError(f"{path.name} has no channel-0 samples")
    result = _channel_metrics(left, int(metadata["sample_rate_hz"]))
    result.update(
        {
            "duration_seconds": metadata["duration_seconds"],
            "right_channel_nonzero_samples": sum(sample != 0 for sample in right),
        }
    )
    return result


def review_collection(plan_path: Path, artifact_dir: Path, stage_id: str) -> dict[str, Any]:
    plan = load_plan(plan_path)
    plan["_path"] = str(plan_path)
    items = build_capture_items(plan)
    selected = select_stage_items(plan, items, stage_id)
    manifest = read_manifest(artifact_dir / "fixture_manifest.json", plan)
    records = manifest.get("records", {})
    rows = []
    issues = []
    for item in selected:
        record = records.get(item.fixture_id, {})
        path = artifact_dir / str(record.get("file", ""))
        try:
            metrics = review_fixture(path, plan["native_capture"], item.duration_seconds)
        except (OSError, ValueError, wave.Error) as error:
            issues.append({"fixture_id": item.fixture_id, "reason": str(error)})
            continue
        rows.append({"fixture_id": item.fixture_id, "vad_class": item.vad_class, "category": item.category, **metrics})

    sample_ids = []
    for vad_class in ("clear_speech", "pause"):
        for category in ("taiwan_mandarin", "code_switch", "number", "date", "product_term"):
            sample_ids.append(next(row["fixture_id"] for row in rows if row["vad_class"] == vad_class and row["category"] == category))
    for vad_class in ("silence", "noise"):
        class_ids = [row["fixture_id"] for row in rows if row["vad_class"] == vad_class]
        sample_ids.extend((class_ids[0], class_ids[-1]))

    sample = [row for row in rows if row["fixture_id"] in set(sample_ids)]
    near_full_scale = [
        {"fixture_id": row["fixture_id"], "events": row["near_full_scale_events"]}
        for row in rows
        if row["near_full_scale_events"]
    ]
    right_channel_nonzero = [
        row["fixture_id"] for row in rows if row["right_channel_nonzero_samples"]
    ]
    result = "PASS" if len(rows) == len(selected) and not issues and not right_channel_nonzero else "REVIEW"
    return {
        "schema_version": "1.0",
        "plan_id": plan["plan_id"],
        "stage_id": stage_id,
        "reviewed_fixture_count": len(rows),
        "result": result,
        "issues": issues,
        "right_channel_nonzero_fixture_ids": right_channel_nonzero,
        "near_full_scale_events": near_full_scale,
        "stratified_sample": sample,
        "semantic_content_review": "requires_authorized_human_listener",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("poc_audio/fixtures/authorized/recording_plan_v1.json"))
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=("pilot", "formal"), default="formal")
    arguments = parser.parse_args(argv)
    print(json.dumps(review_collection(arguments.plan, arguments.artifact_dir, arguments.stage), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
