"""Run the authorized conditional Silero VAD M2 scorecard."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import resource
import threading
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .m2_vad_webrtc import (
    LABEL_INDEX_SHA256,
    PLAN_SHA256,
    POST_PADDING_MS,
    PRE_PADDING_MS,
    STARTUP_MASK_MS,
    child_pids,
    load_inputs,
    padded_and_merged_events,
    score_records,
    sha256_file,
)


CANDIDATE_ID = "vad-silero-onnx-6.2.1"
MANIFEST_PATH = "poc_audio/manifests/m2_vad_silero_fallback.json"
WINDOW_SAMPLES = 512
WINDOW_MS = 32
THRESHOLD = 0.5
CONTEXT_SAMPLES = 64
NEG_THRESHOLD = 0.35
MIN_SPEECH_MS = 250
END_SILENCE_MS = 500


def detect_probability_windows(
    probabilities: Iterable[float], duration_ms: int, start_offset_ms: int = STARTUP_MASK_MS,
) -> tuple[list[tuple[int, int]], int]:
    events: list[tuple[int, int]] = []
    event_start: int | None = None
    possible_end: int | None = None
    triggered = False
    positives = 0
    for index, probability in enumerate(probabilities):
        start_ms = start_offset_ms + index * WINDOW_MS
        end_ms = min(duration_ms, start_ms + WINDOW_MS)
        speech = probability >= THRESHOLD
        if speech:
            positives += 1
            if possible_end is not None:
                possible_end = None
            if not triggered:
                event_start = start_ms
                triggered = True
            continue
        if triggered and probability < NEG_THRESHOLD:
            if possible_end is None:
                possible_end = start_ms
            if start_ms - possible_end >= END_SILENCE_MS:
                if event_start is not None and possible_end - event_start > MIN_SPEECH_MS:
                    events.append((event_start, possible_end))
                event_start = None
                possible_end = None
                triggered = False
    if triggered and event_start is not None and duration_ms - event_start > MIN_SPEECH_MS:
        events.append((event_start, duration_ms))
    return events, positives


def verify_manifest_inputs(
    manifest: dict[str, Any], source: Path, model: Path, wheel_dir: Path,
) -> list[dict[str, Any]]:
    if manifest.get("status") != "LOCKED_NOT_EXECUTED" or manifest.get("candidate_id") != CANDIDATE_ID:
        raise ValueError("Silero fallback manifest is not execution eligible")
    for expected, path in ((manifest["source"], source), (manifest["model"], model)):
        if path.name != expected["filename"] or path.stat().st_size != expected["size_bytes"]:
            raise ValueError(f"Silero artifact identity mismatch: {path.name}")
        if sha256_file(path) != expected["sha256"]:
            raise ValueError(f"Silero artifact checksum mismatch: {path.name}")
    verified = []
    for expected in manifest["runtime_wheels"]:
        path = wheel_dir / expected["filename"]
        if path.stat().st_size != expected["size_bytes"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"Silero runtime wheel mismatch: {path.name}")
        verified.append({**expected})
    return verified


def task_count() -> int:
    return len(list(Path("/proc/self/task").iterdir()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--runtime-wheel-dir", type=Path, required=True)
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
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = repo_root / MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime_wheels = verify_manifest_inputs(
        manifest, args.source_artifact, args.model, args.runtime_wheel_dir,
    )
    labels, plan, fixture_manifest = load_inputs(
        args.fixture_dir, args.label_index, args.recording_plan,
    )
    expected_versions = {
        "onnxruntime": "1.29.0", "flatbuffers": "25.12.19", "numpy": "2.5.2",
        "packaging": "26.3", "protobuf": "7.36.0",
    }
    for package, expected in expected_versions.items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f"Silero runtime version mismatch: {package}")

    import numpy as np  # type: ignore[import-not-found]
    import onnxruntime as ort  # type: ignore[import-not-found]

    labels_by_id = {record["fixture_id"]: record for record in labels["records"]}
    plan_classes = {item["fixture_id"]: item["vad_class"] for item in plan["utterances"]}
    for vad_class in ("silence", "noise"):
        plan_classes.update({f"vad-{vad_class}-{index:03d}": vad_class for index in range(1, 26)})
    before = {
        "python_threads": threading.active_count(), "native_tasks": task_count(),
        "fds": len(list(Path("/proc/self/fd").iterdir())), "children": child_pids(),
    }
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(args.model), sess_options=options, providers=["CPUExecutionProvider"])
    input_names = [item.name for item in session.get_inputs()]
    output_names = [item.name for item in session.get_outputs()]
    if input_names != ["input", "state", "sr"] or output_names != ["output", "stateN"]:
        raise ValueError("Silero ONNX interface mismatch")

    wall_started = time.monotonic()
    cpu_started = time.process_time()
    records: list[dict[str, Any]] = []
    total_audio_seconds = 0.0
    positive_windows = total_windows = 0
    for fixture_id, fixture in sorted(fixture_manifest["records"].items()):
        wav_path = args.fixture_dir / fixture["file"]
        if sha256_file(wav_path) != fixture["derived_sha256"]:
            raise ValueError(f"fixture checksum mismatch: {fixture_id}")
        with wave.open(str(wav_path), "rb") as source_wav:
            if (source_wav.getframerate(), source_wav.getnchannels(), source_wav.getsampwidth()) != (16000, 1, 2):
                raise ValueError(f"fixture PCM mismatch: {fixture_id}")
            pcm = source_wav.readframes(source_wav.getnframes())
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        duration_ms = round(len(samples) / 16)
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)
        probabilities: list[float] = []
        for start in range(STARTUP_MASK_MS * 16, len(samples), WINDOW_SAMPLES):
            window = samples[start:start + WINDOW_SAMPLES]
            if len(window) < WINDOW_SAMPLES:
                window = np.pad(window, (0, WINDOW_SAMPLES - len(window)))
            model_input = np.concatenate((context, window.reshape(1, -1)), axis=1)
            output, state = session.run(None, {
                "input": model_input, "state": state,
                "sr": np.array(16000, dtype=np.int64),
            })
            context = model_input[:, -CONTEXT_SAMPLES:]
            probabilities.append(float(output.reshape(-1)[0]))
        events, positives = detect_probability_windows(probabilities, duration_ms)
        duration_seconds = len(samples) / 16000
        total_audio_seconds += duration_seconds
        positive_windows += positives
        total_windows += len(probabilities)
        label = labels_by_id.get(fixture_id)
        records.append({
            "fixture_id": fixture_id,
            "class": plan_classes[fixture_id],
            "duration_seconds": duration_seconds,
            "reference_intervals_ms": label["speech_intervals_ms"] if label else [],
            "candidate_events_ms": [list(event) for event in events],
            "capture_intervals_ms": padded_and_merged_events(events, duration_ms),
            "positive_windows": positives,
            "total_windows": len(probabilities),
        })
    wall_seconds = time.monotonic() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    scoring = score_records(records)
    del session
    gc.collect()
    time.sleep(0.1)
    after = {
        "python_threads": threading.active_count(), "native_tasks": task_count(),
        "fds": len(list(Path("/proc/self/fd").iterdir())), "children": child_pids(),
    }
    cleanup_pass = before == after and not after["children"]
    gates = dict(scoring["gates"])
    gates["cleanup_zero_delta"] = cleanup_pass
    passed = all(gates.values())
    report = {
        "schema_version": "1.0",
        "report_id": "M2-VAD-SILERO-BOUNDED-001",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_sha": args.source_sha,
        "candidate_id": CANDIDATE_ID,
        "candidate": {
            "commit": manifest["engine"]["commit"],
            "source_sha256": manifest["source"]["sha256"],
            "model_sha256": manifest["model"]["sha256"],
            "runtime_wheels": runtime_wheels,
        },
        "profile": manifest["profile"],
        "inputs": {
            "recording_plan_sha256": PLAN_SHA256,
            "label_index_sha256": LABEL_INDEX_SHA256,
            "delivered_manifest_sha256": sha256_file(args.fixture_dir / "delivered_fixture_manifest.json"),
            "fixture_count": len(records),
        },
        "runtime_interface": {
            "inputs": input_names,
            "outputs": output_names,
            "providers": ["CPUExecutionProvider"],
            "official_context_samples": CONTEXT_SAMPLES,
        },
        "score": {**scoring, "gates": gates, "quality_pass": passed},
        "observations": {
            "audio_seconds": round(total_audio_seconds, 6),
            "wall_seconds": round(wall_seconds, 6),
            "rtf": round(wall_seconds / total_audio_seconds, 9),
            "cpu_percent_one_core": round(cpu_seconds / wall_seconds * 100, 6),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 6),
            "positive_window_percent": round(positive_windows / total_windows * 100, 6),
        },
        "cleanup": {"before": before, "after": after, "pass": cleanup_pass},
        "records": records,
        "status": "DRAFT_SILERO_GATE_MET_USER_CONFIRMATION_PENDING" if passed else "DRAFT_SILERO_GATE_NOT_MET_USER_CONFIRMATION_PENDING",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "score": report["score"]["overall"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
