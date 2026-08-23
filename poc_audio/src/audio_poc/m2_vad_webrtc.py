"""Run the single authorized WebRTC VAD M2 scorecard."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import resource
import threading
import time
import wave
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable


CANDIDATE_ID = "vad-webrtc-2.0.10"
SOURCE_SIZE_BYTES = 66156
SOURCE_SHA256 = "f1bed2fb25b63fb7b1a55d64090c993c9c9167b28485ae0bcdd81cf6ede96aea"
LABEL_INDEX_SHA256 = "85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74"
PLAN_SHA256 = "d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920"
FRAME_MS = 20
FRAME_BYTES = 640
STARTUP_MASK_MS = 160
ONSET_WINDOW_MS = 300
ONSET_WINDOW_FRAMES = ONSET_WINDOW_MS // FRAME_MS
ONSET_VOICED_FRAMES = math.ceil(ONSET_WINDOW_FRAMES * 0.9)
END_SILENCE_MS = 500
PRE_PADDING_MS = 500
POST_PADDING_MS = 600
MODE = 3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nearest_rank_p95(values: Iterable[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def detect_events(
    frames: Iterable[bytes],
    is_speech: Callable[[bytes], bool],
) -> tuple[list[tuple[int, int]], int]:
    """Return debounced raw boundaries after the device-start mask."""
    events: list[tuple[int, int]] = []
    event_start: int | None = None
    last_speech_end: int | None = None
    onset: deque[tuple[int, int, bool]] = deque(maxlen=ONSET_WINDOW_FRAMES)
    triggered = False
    positive_frames = 0
    for frame_count, frame in enumerate(frames, 1):
        start_ms = (frame_count - 1) * FRAME_MS
        end_ms = start_ms + FRAME_MS
        if end_ms <= STARTUP_MASK_MS:
            continue
        speech = is_speech(frame)
        if speech:
            positive_frames += 1
        if not triggered:
            onset.append((start_ms, end_ms, speech))
            if len(onset) == ONSET_WINDOW_FRAMES and sum(item[2] for item in onset) >= ONSET_VOICED_FRAMES:
                event_start = next(item[0] for item in onset if item[2])
                last_speech_end = max(item[1] for item in onset if item[2])
                triggered = True
                onset.clear()
        elif speech:
            last_speech_end = end_ms
        elif event_start is not None and last_speech_end is not None:
            if end_ms - last_speech_end >= END_SILENCE_MS:
                events.append((event_start, last_speech_end))
                event_start = None
                last_speech_end = None
                triggered = False
                onset.clear()
    if triggered and event_start is not None and last_speech_end is not None:
        events.append((event_start, last_speech_end))
    return events, positive_frames


def padded_and_merged_events(
    events: Iterable[tuple[int, int]], duration_ms: int,
) -> list[list[int]]:
    padded = [
        [max(0, start - PRE_PADDING_MS), min(duration_ms, end + POST_PADDING_MS)]
        for start, end in events
    ]
    merged: list[list[int]] = []
    for start, end in padded:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def match_boundaries(
    references: list[int], candidates: list[int], early_ms: int, late_ms: int,
) -> tuple[int, list[int], list[int]]:
    unused = set(range(len(candidates)))
    errors: list[int] = []
    unmatched: list[int] = []
    for reference in references:
        eligible = [
            index for index in unused
            if early_ms <= candidates[index] - reference <= late_ms
        ]
        if not eligible:
            unmatched.append(reference)
            continue
        selected = min(eligible, key=lambda index: abs(candidates[index] - reference))
        unused.remove(selected)
        errors.append(candidates[selected] - reference)
    return len(errors), errors, sorted(candidates[index] for index in unused),


def score_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_start_errors: list[int] = []
    all_end_errors: list[int] = []
    reference_starts = reference_ends = matched_starts = matched_ends = 0
    complete_utterances = 0
    false_starts = 0
    nonspeech_seconds = 0.0

    for record in records:
        by_class[record["class"]].append(record)
        expected = record["reference_intervals_ms"]
        events = record["candidate_events_ms"]
        if record["class"] in {"clear_speech", "pause"}:
            starts = [expected[0][0]]
            ends = [expected[-1][1]]
            candidate_starts = [interval[0] for interval in events]
            candidate_ends = [interval[1] for interval in events]
            captures = record["capture_intervals_ms"]
            start_count = int(any(start <= starts[0] <= end for start, end in captures))
            end_count = int(any(start <= ends[0] <= end for start, end in captures))
            complete = int(any(start <= starts[0] and end >= ends[0] for start, end in captures))
            if candidate_starts:
                start_errors = [min(candidate_starts, key=lambda value: abs(value - starts[0])) - starts[0]]
                end_errors = [min(candidate_ends, key=lambda value: abs(value - ends[0])) - ends[0]]
            else:
                start_errors = []
                end_errors = []
            reference_starts += len(starts)
            reference_ends += len(ends)
            matched_starts += start_count
            matched_ends += end_count
            complete_utterances += complete
            all_start_errors.extend(start_errors)
            all_end_errors.extend(end_errors)
            record["matched_starts"] = start_count
            record["matched_ends"] = end_count
            record["complete_utterance_coverage"] = bool(complete)
            record["raw_start_error_ms"] = start_errors[0] if start_errors else None
            record["raw_end_error_ms"] = end_errors[0] if end_errors else None
        else:
            false_starts += len(events)
            nonspeech_seconds += record["duration_seconds"]

    def class_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        speech_items = [item for item in items if item["reference_intervals_ms"]]
        starts = len(speech_items)
        matched_start_count = sum(item.get("matched_starts", 0) for item in items)
        ends = starts
        matched_end_count = sum(item.get("matched_ends", 0) for item in items)
        return {
            "fixtures": len(items),
            "reference_starts": starts,
            "matched_starts": matched_start_count,
            "start_recall_percent": round(100 * matched_start_count / starts, 6) if starts else None,
            "reference_ends": ends,
            "matched_ends": matched_end_count,
            "end_recall_percent": round(100 * matched_end_count / ends, 6) if ends else None,
            "candidate_events": sum(len(item["candidate_events_ms"]) for item in items),
            "complete_utterances": sum(item.get("complete_utterance_coverage", False) for item in items),
        }

    start_recall = 100 * matched_starts / reference_starts
    end_recall = 100 * matched_ends / reference_ends
    start_p95 = nearest_rank_p95(abs(value) for value in all_start_errors)
    end_p95 = nearest_rank_p95(abs(value) for value in all_end_errors)
    false_start_rate = false_starts / (nonspeech_seconds / 60) * 10
    gates = {
        "speech_start_recall_gte_95": start_recall >= 95,
        "speech_end_recall_gte_90": end_recall >= 90,
        "silence_noise_false_start_lte_1_per_10_min": false_start_rate <= 1,
    }
    return {
        "overall": {
            "reference_starts": reference_starts,
            "matched_starts": matched_starts,
            "speech_start_recall_percent": round(start_recall, 6),
            "reference_ends": reference_ends,
            "matched_ends": matched_ends,
            "speech_end_recall_percent": round(end_recall, 6),
            "start_boundary_abs_error_p95_ms": start_p95,
            "end_boundary_abs_error_p95_ms": end_p95,
            "silence_noise_false_starts": false_starts,
            "nonspeech_minutes": round(nonspeech_seconds / 60, 6),
            "false_starts_per_10_min": round(false_start_rate, 6),
            "complete_utterances": complete_utterances,
            "reference_utterances": reference_starts,
            "complete_utterance_percent": round(100 * complete_utterances / reference_starts, 6),
        },
        "by_class": {name: class_summary(by_class[name]) for name in (
            "clear_speech", "pause", "silence", "noise"
        )},
        "gates": gates,
        "quality_pass": all(gates.values()),
        "boundary_note": "Raw model boundary errors are diagnostic; padded capture coverage drives recall.",
    }


def load_inputs(
    fixture_dir: Path, label_path: Path, plan_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if sha256_file(label_path) != LABEL_INDEX_SHA256:
        raise ValueError("frozen VAD label checksum mismatch")
    if sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("recording plan checksum mismatch")
    labels = json.loads(label_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifest_path = fixture_dir / "delivered_fixture_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest.get("records", {})) != 100 or len(labels.get("records", [])) != 50:
        raise ValueError("authorized 100-item fixture or 50-item label set is incomplete")
    return labels, plan, manifest


def child_pids() -> list[int]:
    path = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")
    if not path.exists():
        return []
    return [int(value) for value in path.read_text().split()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--runtime-wheel", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--label-index", type=Path, required=True)
    parser.add_argument("--recording-plan", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise ValueError("output must be a new path")
    if args.source_artifact.stat().st_size != SOURCE_SIZE_BYTES:
        raise ValueError("WebRTC source size mismatch")
    if sha256_file(args.source_artifact) != SOURCE_SHA256:
        raise ValueError("WebRTC source checksum mismatch")
    labels, plan, manifest = load_inputs(args.fixture_dir, args.label_index, args.recording_plan)
    if importlib.metadata.version("webrtcvad") != "2.0.10":
        raise ValueError("WebRTC runtime version mismatch")
    import _webrtcvad  # type: ignore[import-not-found]

    if not _webrtcvad.valid_rate_and_frame_length(16000, 320):
        raise ValueError("WebRTC native runtime rejects the frozen frame contract")
    labels_by_id = {record["fixture_id"]: record for record in labels["records"]}
    plan_classes = {item["fixture_id"]: item["vad_class"] for item in plan["utterances"]}
    for vad_class in ("silence", "noise"):
        plan_classes.update({f"vad-{vad_class}-{index:03d}": vad_class for index in range(1, 26)})
    before = {
        "threads": threading.active_count(),
        "fds": len(list(Path("/proc/self/fd").iterdir())),
        "children": child_pids(),
    }
    wall_started = time.monotonic()
    cpu_started = time.process_time()
    records: list[dict[str, Any]] = []
    total_audio_seconds = 0.0
    positive_frames = total_frames = 0
    for fixture_id, fixture in sorted(manifest["records"].items()):
        if fixture_id not in plan_classes:
            raise ValueError(f"unexpected fixture identity: {fixture_id}")
        wav_path = args.fixture_dir / fixture["file"]
        if sha256_file(wav_path) != fixture["derived_sha256"]:
            raise ValueError(f"fixture checksum mismatch: {fixture_id}")
        with wave.open(str(wav_path), "rb") as source:
            if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (16000, 1, 2):
                raise ValueError(f"fixture PCM mismatch: {fixture_id}")
            payload = source.readframes(source.getnframes())
        if len(payload) % FRAME_BYTES:
            raise ValueError(f"fixture is not an exact 20 ms frame multiple: {fixture_id}")
        frames = [payload[index:index + FRAME_BYTES] for index in range(0, len(payload), FRAME_BYTES)]
        native_vad = _webrtcvad.create()
        _webrtcvad.init(native_vad)
        _webrtcvad.set_mode(native_vad, MODE)
        events, positives = detect_events(
            frames, lambda frame: _webrtcvad.process(native_vad, 16000, frame, 320),
        )
        duration_seconds = len(payload) / 2 / 16000
        total_audio_seconds += duration_seconds
        positive_frames += positives
        total_frames += len(frames)
        label = labels_by_id.get(fixture_id)
        reference = label["speech_intervals_ms"] if label else []
        duration_ms = round(duration_seconds * 1000)
        records.append({
            "fixture_id": fixture_id,
            "class": plan_classes[fixture_id],
            "duration_seconds": duration_seconds,
            "reference_intervals_ms": reference,
            "candidate_events_ms": [list(event) for event in events],
            "capture_intervals_ms": padded_and_merged_events(events, duration_ms),
            "positive_frames": positives,
            "total_frames": len(frames),
        })
    wall_seconds = time.monotonic() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    scoring = score_records(records)
    after = {
        "threads": threading.active_count(),
        "fds": len(list(Path("/proc/self/fd").iterdir())),
        "children": child_pids(),
    }
    cleanup_pass = before == after and not after["children"]
    gates = dict(scoring["gates"])
    gates["cleanup_zero_delta"] = cleanup_pass
    passed = all(gates.values())
    report = {
        "schema_version": "1.0",
        "report_id": "M2-VAD-WEBRTC-BOUNDED-001",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_sha": args.source_sha,
        "candidate_id": CANDIDATE_ID,
        "candidate": {
            "engine": "py-webrtcvad",
            "version": "2.0.10",
            "runtime_api": "official wheel native _webrtcvad extension",
            "source_size_bytes": SOURCE_SIZE_BYTES,
            "source_sha256": SOURCE_SHA256,
            "runtime_wheel_sha256": sha256_file(args.runtime_wheel),
        },
        "profile": {
            "sample_rate_hz": 16000,
            "channels": 1,
            "sample_format": "S16_LE",
            "frame_ms": FRAME_MS,
            "aggressiveness": MODE,
            "startup_mask_ms": STARTUP_MASK_MS,
            "event_start": "14 voiced frames in a complete rolling 15-frame / 300 ms window",
            "event_end": "last positive frame before 500 ms consecutive non-speech",
            "pre_speech_padding_ms": PRE_PADDING_MS,
            "post_speech_padding_ms": POST_PADDING_MS,
            "fixture_state": "fresh engine and endpoint state per independent WAV",
            "pause_scoring": "one utterance envelope from first annotated start to final annotated end",
        },
        "inputs": {
            "recording_plan_sha256": PLAN_SHA256,
            "label_index_sha256": LABEL_INDEX_SHA256,
            "delivered_manifest_sha256": sha256_file(args.fixture_dir / "delivered_fixture_manifest.json"),
            "fixture_count": len(records),
        },
        "score": {**scoring, "gates": gates, "quality_pass": passed},
        "observations": {
            "audio_seconds": round(total_audio_seconds, 6),
            "wall_seconds": round(wall_seconds, 6),
            "rtf": round(wall_seconds / total_audio_seconds, 9),
            "cpu_percent_one_core": round(cpu_seconds / wall_seconds * 100, 6),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 6),
            "positive_frame_percent": round(positive_frames / total_frames * 100, 6),
        },
        "cleanup": {"before": before, "after": after, "pass": cleanup_pass},
        "records": records,
        "status": "DRAFT_WEBRTC_GATE_MET_USER_CONFIRMATION_PENDING" if passed else "DRAFT_WEBRTC_GATE_NOT_MET_USER_CONFIRMATION_PENDING",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "score": report["score"]["overall"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
