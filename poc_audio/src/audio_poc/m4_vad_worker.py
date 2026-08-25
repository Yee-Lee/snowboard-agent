"""Persistent, framed protocol adapter for the frozen M4 Silero VAD finalist.

The worker writes bounded controlled WAVs only to its caller-owned work directory.
It never emits PCM or transcript data on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import struct
import sys
from pathlib import Path
from typing import Any

from .m2_vad_silero import CONTEXT_SAMPLES, WINDOW_SAMPLES, detect_probability_windows
from .m2_vad_webrtc import padded_and_merged_events
from .m3_vad_worker import MODEL_SHA256, bounded_payload, read_wav, write_wav


def _emit(document: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_command(command: object) -> tuple[str, str, Path] | None:
    if command == {"op": "SHUTDOWN"}:
        return None
    if not isinstance(command, dict) or set(command) != {"op", "session_id", "wav_path"}:
        raise ValueError("INVALID_COMMAND")
    if command.get("op") != "RUN" or not isinstance(command["session_id"], str):
        raise ValueError("INVALID_COMMAND")
    path_text = command.get("wav_path")
    if not isinstance(path_text, str) or not path_text or any(char in path_text for char in "\r\n"):
        raise ValueError("INVALID_WAV_PATH")
    return "RUN", command["session_id"], Path(path_text)


def _run_one(session: Any, wav_path: Path, output_dir: Path, np: Any) -> dict[str, Any]:
    payload, samples = read_wav(wav_path)
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
    intervals = [list(item) for item in padded_and_merged_events(events, duration_ms)]
    if len(intervals) != 1:
        raise ValueError("NO_SINGLE_BOUNDED_UTTERANCE")
    bounded_path = output_dir / f"{session}.wav"
    if bounded_path.exists():
        raise ValueError("SESSION_OUTPUT_EXISTS")
    write_wav(bounded_path, bounded_payload(payload, intervals))
    return {
        "event": "RESULT",
        "session_id": session,
        "source_sha256": _sha256_file(wav_path),
        "bounded_sha256": _sha256_file(bounded_path),
        "bounded_filename": bounded_path.name,
        "bounded_size_bytes": bounded_path.stat().st_size,
        "capture_intervals_ms": intervals,
        "positive_windows": positive_windows,
        "total_windows": len(probabilities),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("M4 VAD output directory must be new")
    if not args.model.is_file() or _sha256_file(args.model) != MODEL_SHA256:
        raise ValueError("M4 Silero model checksum mismatch")
    import numpy as np
    import onnxruntime as ort

    versions = {
        "onnxruntime": importlib.metadata.version("onnxruntime"),
        "numpy": importlib.metadata.version("numpy"),
    }
    if versions != {"onnxruntime": "1.29.0", "numpy": "2.5.2"}:
        raise ValueError(f"M4 Silero runtime identity mismatch: {versions}")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(
        str(args.model), sess_options=options, providers=["CPUExecutionProvider"]
    )
    if [item.name for item in session.get_inputs()] != ["input", "state", "sr"]:
        raise ValueError("M4 Silero input interface mismatch")
    args.output_dir.mkdir(parents=True)
    _emit({
        "event": "READY", "candidate_id": "vad-silero-onnx-6.2.1",
        "model_sha256": MODEL_SHA256, "runtime": {**versions, "threads": 1},
    })
    for raw in sys.stdin:
        try:
            command = _validate_command(json.loads(raw))
            if command is None:
                _emit({"event": "SHUTDOWN_ACK"})
                return 0
            _op, session_id, wav_path = command
            _emit(_run_one(session_id, wav_path, args.output_dir, np))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            _emit({"event": "ERROR", "code": str(error)})
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
