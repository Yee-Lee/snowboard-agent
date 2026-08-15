"""Create reviewable, energy-assisted VAD label proposals for local fixtures."""

from __future__ import annotations

import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path
from typing import Any

from .fixture_recorder import build_capture_items, load_plan, read_manifest


WINDOW_MS = 10
MIN_SPEECH_MS = 50
MAX_JOIN_GAP_MS = 120
MIN_PAUSE_MS = 120


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def _merge_runs(runs: list[list[int]], max_gap_windows: int) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end in runs:
        if merged and start - merged[-1][1] <= max_gap_windows:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def propose_intervals(samples: array.array[int], sample_rate_hz: int) -> dict[str, Any]:
    """Return conservative energy-based proposals; never claim ground truth."""
    window_frames = sample_rate_hz * WINDOW_MS // 1000
    rms_dbfs = []
    for offset in range(0, len(samples), window_frames):
        window = samples[offset : offset + window_frames]
        rms = math.sqrt(sum((value / 2147483648.0) ** 2 for value in window) / len(window))
        rms_dbfs.append(20 * math.log10(max(rms, 1e-12)))
    floor = _percentile(rms_dbfs, 0.10)
    ceiling = _percentile(rms_dbfs, 0.90)
    threshold = floor + max(4.0, (ceiling - floor) * 0.35)
    active = [value >= threshold for value in rms_dbfs]
    runs: list[list[int]] = []
    start: int | None = None
    for index, value in enumerate(active + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start >= MIN_SPEECH_MS // WINDOW_MS:
                runs.append([start, index])
            start = None
    runs = _merge_runs(runs, MAX_JOIN_GAP_MS // WINDOW_MS)
    active_intervals = [[start * WINDOW_MS, end * WINDOW_MS] for start, end in runs]
    pause_candidates = [
        [left[1] * WINDOW_MS, right[0] * WINDOW_MS]
        for left, right in zip(runs, runs[1:])
        if (right[0] - left[1]) * WINDOW_MS >= MIN_PAUSE_MS
    ]
    return {
        "window_ms": WINDOW_MS,
        "energy_floor_dbfs": round(floor, 2),
        "energy_ceiling_dbfs": round(ceiling, 2),
        "energy_threshold_dbfs": round(threshold, 2),
        "raw_active_intervals_ms": active_intervals,
        "utterance_interval_ms": [active_intervals[0][0], active_intervals[-1][1]] if active_intervals else None,
        "largest_internal_pause_candidate_ms": max(
            pause_candidates, key=lambda interval: interval[1] - interval[0], default=None
        ),
        "method": "energy_assisted_proposal_requires_human_review",
    }


def propose_labels(plan_path: Path, artifact_dir: Path) -> dict[str, Any]:
    plan = load_plan(plan_path)
    plan["_path"] = str(plan_path)
    manifest = read_manifest(artifact_dir / "fixture_manifest.json", plan)
    proposals = []
    for item in build_capture_items(plan):
        if item.vad_class not in {"clear_speech", "pause"}:
            continue
        record = manifest.get("records", {}).get(item.fixture_id)
        if record is None:
            raise ValueError(f"missing fixture manifest record: {item.fixture_id}")
        source = artifact_dir / str(record["file"])
        with wave.open(str(source), "rb") as input_wav:
            if input_wav.getnchannels() != 2 or input_wav.getsampwidth() != 4:
                raise ValueError(f"unexpected native format: {source.name}")
            payload = input_wav.readframes(input_wav.getnframes())
            rate = input_wav.getframerate()
        values = array.array("i")
        values.frombytes(payload)
        if sys.byteorder != "little":
            values.byteswap()
        proposal = propose_intervals(values[0::2], rate)
        utterance = proposal.pop("utterance_interval_ms")
        pause = proposal.pop("largest_internal_pause_candidate_ms")
        if utterance is None:
            speech_intervals = []
        elif item.vad_class == "clear_speech":
            speech_intervals = [utterance]
        elif pause is None:
            speech_intervals = [utterance]
        else:
            speech_intervals = [[utterance[0], pause[0]], [pause[1], utterance[1]]]
        proposals.append(
            {
                "fixture_id": item.fixture_id,
                "class": item.vad_class,
                "category": item.category,
                "native_sha256": record["sha256"],
                "review_status": "PROPOSED_REQUIRES_HUMAN_REVIEW",
                "speech_intervals_ms": speech_intervals,
                "internal_pause_candidate_ms": pause,
                **proposal,
            }
        )
    return {
        "schema_version": "1.0",
        "label_set_id": "m1-authorized-vad-label-proposals-v1",
        "plan_id": plan["plan_id"],
        "proposal_count": len(proposals),
        "review_requirement": "A User/Designer or authorized Tester must review every proposal before this becomes a frozen label index.",
        "proposals": proposals,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("poc_audio/fixtures/authorized/recording_plan_v1.json"))
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    document = propose_labels(arguments.plan, arguments.artifact_dir)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"proposal_count": document["proposal_count"], "output": str(arguments.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
