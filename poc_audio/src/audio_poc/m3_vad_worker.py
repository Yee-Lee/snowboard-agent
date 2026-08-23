"""Pi worker for frozen Silero VAD over Core-captured M3 WAV fixtures."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import struct
import wave
from pathlib import Path
from typing import Any

from .m2_vad_silero import (
    CONTEXT_SAMPLES,
    CANDIDATE_ID,
    WINDOW_SAMPLES,
    detect_probability_windows,
)
from .m2_vad_webrtc import padded_and_merged_events


MODEL_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
CASE_FILES = (
    ("M3-VAD-01", "asr-clear-002.wav", True),
    ("M3-VAD-02", "asr-clear-003.wav", True),
    ("M3-VAD-03", "asr-pause-031.wav", True),
    ("M3-VAD-04", "m3-steady-silence-60s.wav", False),
    ("M3-VAD-05", "m3-device-start-10s.wav", False),
    ("M3-VAD-06", "m3-impact-10s.wav", False),
    ("M3-VAD-07", "m3-cough-10s.wav", False),
    ("M3-VAD-08", "m3-playback-speech-10s.wav", False),
    ("M3-ASR-04", "asr-clear-012.wav", True),
    ("M3-ASR-05", "asr-clear-023.wav", True),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_wav(path: Path) -> tuple[bytes, list[float]]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (16_000, 1, 2, "NONE"):
            raise ValueError(f"M3 VAD fixture format mismatch: {path.name}")
        payload = source.readframes(source.getnframes())
    if not payload:
        raise ValueError(f"M3 VAD fixture is empty: {path.name}")
    samples = [value[0] / 32768.0 for value in struct.iter_unpack("<h", payload)]
    return payload, samples


def bounded_payload(payload: bytes, intervals_ms: list[list[int]]) -> bytes:
    if len(intervals_ms) != 1:
        raise ValueError("M3 bounded ASR fixture requires one merged capture interval")
    start_ms, end_ms = intervals_ms[0]
    start_byte = start_ms * 16 * 2
    end_byte = end_ms * 16 * 2
    if start_byte < 0 or start_byte >= end_byte or end_byte > len(payload):
        raise ValueError("M3 VAD capture interval is outside source PCM")
    return payload[start_byte:end_byte]


def write_wav(path: Path, payload: bytes) -> None:
    with path.open("xb") as raw:
        with wave.open(raw, "wb") as destination:
            destination.setnchannels(1)
            destination.setsampwidth(2)
            destination.setframerate(16_000)
            destination.writeframes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.work_dir.exists():
        raise ValueError("M3 VAD work directory must be new")
    if sha256_file(args.model) != MODEL_SHA256:
        raise ValueError("M3 Silero model checksum mismatch")
    import numpy as np
    import onnxruntime as ort

    versions = {
        "onnxruntime": importlib.metadata.version("onnxruntime"),
        "numpy": importlib.metadata.version("numpy"),
    }
    if versions != {"onnxruntime": "1.29.0", "numpy": "2.5.2"}:
        raise ValueError(f"M3 Silero runtime identity mismatch: {versions}")

    args.work_dir.mkdir(parents=True)
    bounded_dir = args.work_dir / "bounded-asr"
    bounded_dir.mkdir()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(
        str(args.model), sess_options=options, providers=["CPUExecutionProvider"]
    )
    if [item.name for item in session.get_inputs()] != ["input", "state", "sr"]:
        raise ValueError("M3 Silero input interface mismatch")
    diagnostics: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for test_id, filename, create_bounded in CASE_FILES:
        path = args.fixture_dir / filename
        payload, samples = read_wav(path)
        duration_ms = len(samples) // 16
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)
        probabilities: list[float] = []
        for start in range(160 * 16, len(samples), WINDOW_SAMPLES):
            window = np.asarray(samples[start:start + WINDOW_SAMPLES], dtype=np.float32)
            if len(window) < WINDOW_SAMPLES:
                window = np.pad(window, (0, WINDOW_SAMPLES - len(window)))
            model_input = np.concatenate((context, window.reshape(1, -1)), axis=1)
            output, state = session.run(None, {
                "input": model_input,
                "state": state,
                "sr": np.array(16_000, dtype=np.int64),
            })
            context = model_input[:, -CONTEXT_SAMPLES:]
            probabilities.append(float(output.reshape(-1)[0]))
        events, positive_windows = detect_probability_windows(probabilities, duration_ms)
        capture_intervals = [list(item) for item in padded_and_merged_events(events, duration_ms)]
        bounded = None
        if create_bounded and len(capture_intervals) == 1:
            bounded_path = bounded_dir / filename
            write_wav(bounded_path, bounded_payload(payload, capture_intervals))
            bounded = {
                "file": filename,
                "sha256": sha256_file(bounded_path),
                "size_bytes": bounded_path.stat().st_size,
            }
        records.append({
            "test_id": test_id,
            "file": filename,
            "source_sha256": sha256_file(path),
            "duration_ms": duration_ms,
            "event_count": len(events),
            "events_ms": [list(item) for item in events],
            "capture_intervals_ms": capture_intervals,
            "positive_windows": positive_windows,
            "total_windows": len(probabilities),
            "bounded_asr": bounded,
        })
        diagnostics.append({
            "test_id": test_id,
            "source_sha256": sha256_file(path),
            "probabilities": probabilities,
        })
    diagnostic_path = args.work_dir / "vad-probabilities.controlled.json"
    diagnostic_path.write_text(
        json.dumps({"records": diagnostics}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    result = {
        "candidate_id": CANDIDATE_ID,
        "model_sha256": MODEL_SHA256,
        "runtime": {
            **versions,
            "provider": "CPUExecutionProvider",
            "threads": 1,
        },
        "profile": {
            "sample_rate_hz": 16_000,
            "context_samples": 64,
            "threshold": 0.5,
            "negative_threshold": 0.35,
            "minimum_speech_ms": 250,
            "startup_mask_ms": 160,
            "end_silence_ms": 500,
            "capture_pre_padding_ms": 500,
            "capture_post_padding_ms": 600,
        },
        "records": records,
        "controlled_probability_sha256": sha256_file(diagnostic_path),
        "bounded_fixture_count": sum(item["bounded_asr"] is not None for item in records),
        "review_disposition": "PENDING_USER_LOW_VOLUME_AND_CLASSIFICATION_REVIEW",
    }
    print("M3_VAD_RESULT=" + json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
