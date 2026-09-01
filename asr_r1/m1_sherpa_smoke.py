"""Run one sanitized, warm-model sherpa-onnx M1 streaming smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import wave
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import monotonic, process_time

from .fixture_preflight import verify_controlled_smoke_fixture
from .protocol import PCMChunk
from .sherpa_adapter import (
    SherpaOnnxTransducerBackend,
    SherpaOnnxWenetCtcBackend,
    SherpaStreamingRuntime,
)


ZIPFORMER_IDS = {
    "asr-sherpa-streaming-zipformer-zh-xlarge-int8-2025-06-30",
    "asr-sherpa-streaming-zipformer-zh-large-int8-2025-06-30",
}
WENET_IDS = {
    "asr-sherpa-wenet-wenetspeech-streaming-ctc-int8",
    "asr-sherpa-wenet-aishell-streaming-ctc-int8",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _backend(candidate_id: str, model_dir: Path, num_threads: int):
    if candidate_id in ZIPFORMER_IDS:
        return SherpaOnnxTransducerBackend(candidate_id, model_dir, num_threads)
    if candidate_id in WENET_IDS:
        return SherpaOnnxWenetCtcBackend(candidate_id, model_dir, num_threads)
    raise ValueError("candidate is not an M1 sherpa-onnx row")


def run_smoke(
    candidate_id: str,
    model_dir: Path,
    controlled_wav: Path,
    num_threads: int = 2,
    chunk_duration_ms: int = 160,
) -> dict[str, object]:
    """Return metrics only; never return or persist transcript content."""

    if chunk_duration_ms <= 0:
        raise ValueError("chunk_duration_ms must be positive")
    try:
        runtime_version = version("sherpa-onnx")
    except PackageNotFoundError as exc:
        raise RuntimeError("sherpa-onnx 1.13.5 is not installed") from exc
    if runtime_version != "1.13.5":
        raise RuntimeError("sherpa-onnx runtime identity mismatch")
    identity = verify_controlled_smoke_fixture(_repo_root(), controlled_wav)
    runtime = SherpaStreamingRuntime(_backend(candidate_id, model_dir, num_threads))

    load_started = monotonic()
    load_cpu_started = process_time()
    runtime.load_model()
    load_cpu_seconds = process_time() - load_cpu_started
    load_seconds = monotonic() - load_started

    session_id = runtime.create_session()
    decode_started = monotonic()
    decode_cpu_started = process_time()
    partial_count = 0
    with wave.open(str(identity.path), "rb") as source:
        frames_per_chunk = source.getframerate() * chunk_duration_ms // 1_000
        sequence = 0
        frame_offset = 0
        while True:
            pcm = source.readframes(frames_per_chunk)
            if not pcm:
                break
            timestamp_ms = frame_offset * 1_000 // source.getframerate()
            event = runtime.accept_chunk(
                PCMChunk(session_id, sequence, timestamp_ms, pcm)
            )
            if event is not None:
                partial_count += 1
            frame_offset += len(pcm) // 2
            sequence += 1
    final = runtime.finish_input(
        session_id,
        emitted_at_ms=round(identity.duration_seconds * 1_000),
    )
    decode_cpu_seconds = process_time() - decode_cpu_started
    decode_seconds = monotonic() - decode_started
    shutdown_ms = runtime.shutdown(5_000)

    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "fixture_id": identity.fixture_id,
        "audio_seconds": identity.duration_seconds,
        "chunk_duration_ms": chunk_duration_ms,
        "num_threads": num_threads,
        "runtime_version": runtime_version,
        "model_load_seconds": load_seconds,
        "model_load_cpu_seconds": load_cpu_seconds,
        "model_load_effective_cpu_cores": load_cpu_seconds / load_seconds,
        "full_utterance_decode_wall_seconds": decode_seconds,
        "decode_cpu_seconds": decode_cpu_seconds,
        "decode_effective_cpu_cores": decode_cpu_seconds / decode_seconds,
        "full_utterance_rtf": decode_seconds / identity.duration_seconds,
        "self_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * 1_024,
        "partial_event_count": partial_count,
        "final_non_empty": bool(final.text),
        "final_text_sha256": hashlib.sha256(final.text.encode("utf-8")).hexdigest(),
        "shutdown_ms": shutdown_ms,
        "interpretation": "NON_FORMAL_WORKSTATION_SMOKE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--num-threads", type=int, default=2)
    args = parser.parse_args()
    print(
        json.dumps(
            run_smoke(
                candidate_id=args.candidate_id,
                model_dir=args.model_dir,
                controlled_wav=args.fixture,
                num_threads=args.num_threads,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
