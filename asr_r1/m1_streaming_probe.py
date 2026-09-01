"""Paced, sanitized AR1M1 streaming-latency development probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import monotonic, process_time, sleep

from .fixture_preflight import verify_controlled_smoke_fixture
from .m1_baseline import (
    _output_digest,
    _repo_root,
    _resource_fields,
    _row,
    _verify_external,
    run_monitored,
)
from .m1_lifecycle import _build_backend, _pcm_chunks
from .protocol import PCMChunk
from .sherpa_adapter import OnlineBackend, SherpaStreamingRuntime


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def _ttft_ms(
    stream_started: float,
    speech_start_offset_ms: int,
    first_partial_observed: float,
) -> float:
    speech_started = stream_started + speech_start_offset_ms / 1_000
    if first_partial_observed < speech_started:
        raise ValueError("first partial precedes frozen speech start")
    return (first_partial_observed - speech_started) * 1_000


def run_paced_probe(
    candidate_id: str,
    backend: OnlineBackend,
    controlled_wav: Path,
    chunk_duration_ms: int = 160,
) -> dict[str, object]:
    """Drive one resident stream on its deterministic real-time schedule."""

    if chunk_duration_ms <= 0:
        raise ValueError("chunk_duration_ms must be positive")
    identity = verify_controlled_smoke_fixture(_repo_root(), controlled_wav)
    chunks = _pcm_chunks(identity.path, chunk_duration_ms)
    if not chunks:
        raise ValueError("fixture produced no PCM chunks")

    runtime = SherpaStreamingRuntime(backend)
    load_wall_started = monotonic()
    load_cpu_started = process_time()
    loaded_model_id = runtime.load_model()
    if loaded_model_id != candidate_id:
        raise ValueError("backend model identity mismatch")
    load_cpu_seconds = process_time() - load_cpu_started
    load_wall_seconds = monotonic() - load_wall_started

    session_id = runtime.create_session()
    stream_started = monotonic()
    stream_cpu_started = process_time()
    first_partial_observed: float | None = None
    first_partial_audio_timestamp_ms: int | None = None
    partial_hashes: list[str] = []
    chunk_call_seconds: list[float] = []
    chunk_delivery_lateness_ms: list[float] = []

    for sequence, (timestamp_ms, pcm) in enumerate(chunks):
        due = stream_started + timestamp_ms / 1_000
        remaining = due - monotonic()
        if remaining > 0:
            sleep(remaining)
        delivered = monotonic()
        chunk_delivery_lateness_ms.append(max(0.0, (delivered - due) * 1_000))
        call_started = monotonic()
        event = runtime.accept_chunk(
            PCMChunk(session_id, sequence, timestamp_ms, pcm),
            decode_timeout_ms=60_000,
        )
        chunk_call_seconds.append(monotonic() - call_started)
        if event is not None:
            partial_observed = monotonic()
            partial_hashes.append(_digest(event.text or ""))
            if first_partial_observed is None:
                first_partial_observed = partial_observed
                first_partial_audio_timestamp_ms = timestamp_ms

    scheduled_speech_end = (
        stream_started + identity.speech_end_offset_ms / 1_000
    )
    remaining = scheduled_speech_end - monotonic()
    if remaining > 0:
        sleep(remaining)
    finish_started = monotonic()
    final = runtime.finish_input(
        session_id,
        emitted_at_ms=round(identity.duration_seconds * 1_000),
        decode_timeout_ms=120_000,
    )
    final_at = monotonic()
    stream_cpu_seconds = process_time() - stream_cpu_started
    shutdown_ms = runtime.shutdown(5_000)

    deadline_tolerance_ms = 5.0
    deadline_misses = sum(
        lateness > deadline_tolerance_ms for lateness in chunk_delivery_lateness_ms
    )
    partial_chain = _digest("\n".join(partial_hashes))
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "fixture_id": identity.fixture_id,
        "interpretation": "NON_FORMAL_WORKSTATION_PACED_STREAMING",
        "probe_completed": bool(final.text) and first_partial_observed is not None,
        "status": (
            "NON_FORMAL_PACED_STREAMING_COMPLETED"
            if final.text and first_partial_observed is not None
            else "NON_FORMAL_PACED_STREAMING_INCOMPLETE"
        ),
        "audio_seconds": identity.duration_seconds,
        "chunk_duration_ms": chunk_duration_ms,
        "chunk_count": len(chunks),
        "speech_start_offset_ms": identity.speech_start_offset_ms,
        "speech_end_offset_ms": identity.speech_end_offset_ms,
        "model_load_wall_seconds": load_wall_seconds,
        "model_load_cpu_seconds": load_cpu_seconds,
        "model_load_effective_cpu_cores": (
            load_cpu_seconds / load_wall_seconds if load_wall_seconds else 0.0
        ),
        "ttft_ms": (
            _ttft_ms(
                stream_started,
                identity.speech_start_offset_ms,
                first_partial_observed,
            )
            if first_partial_observed is not None
            else None
        ),
        "ttft_scope": "ADAPTER_OBSERVED_FIRST_NONEMPTY_CHANGED_PARTIAL",
        "first_partial_audio_timestamp_ms": first_partial_audio_timestamp_ms,
        "speech_end_to_final_ms": max(
            0.0, (final_at - scheduled_speech_end) * 1_000
        ),
        "input_finished_to_final_ms": (final_at - finish_started) * 1_000,
        "end_to_end_final_ms": (final_at - stream_started) * 1_000,
        "stream_cpu_seconds": stream_cpu_seconds,
        "stream_effective_cpu_cores": stream_cpu_seconds
        / (final_at - stream_started),
        "chunk_call_p50_ms": _percentile(chunk_call_seconds, 0.50) * 1_000,
        "chunk_call_p95_ms": _percentile(chunk_call_seconds, 0.95) * 1_000,
        "chunk_call_max_ms": max(chunk_call_seconds) * 1_000,
        "deadline_tolerance_ms": deadline_tolerance_ms,
        "chunk_deadline_miss_count": deadline_misses,
        "max_chunk_delivery_lateness_ms": max(chunk_delivery_lateness_ms),
        "partial_event_count": len(partial_hashes),
        "partial_revision_count": max(0, len(partial_hashes) - 1),
        "partial_digest_chain_sha256": partial_chain,
        "final_text_sha256": _digest(final.text or ""),
        "top_one_fallback": len(final.alternatives) == 1,
        "shutdown_ms": shutdown_ms,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--artifact-archive", type=Path)
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--runtime-library", type=Path)
    parser.add_argument("--runtime-artifact", action="append", type=Path, default=[])
    parser.add_argument("--num-threads", type=int, default=2)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    return parser


def _run_child(args: argparse.Namespace) -> dict[str, object]:
    fixture = _verify_external(args.fixture, _repo_root(), "controlled audio")
    return run_paced_probe(args.candidate_id, _build_backend(args), fixture)


def _run_supervised(args: argparse.Namespace) -> dict[str, object]:
    method, selected = _row(args.candidate_id)
    argv = [
        sys.executable,
        "-m",
        "asr_r1.m1_streaming_probe",
        *sys.argv[1:],
        "--child",
    ]
    run = run_monitored(
        argv,
        selected["command"]["timeout_seconds"],
        _repo_root(),
    )
    if run.status != "COMPLETED":
        return {
            "schema_version": "1.0",
            "formal_result": False,
            "candidate_id": args.candidate_id,
            "probe_completed": False,
            "status": run.status,
            "returncode": run.returncode,
            "stdout_sha256": _output_digest(run.stdout),
            "stderr_sha256": _output_digest(run.stderr),
            **_resource_fields(run, method["memory_reference_bytes"]),
            "interpretation": "NON_FORMAL_WORKSTATION_PACED_STREAMING",
        }
    try:
        result = json.loads(run.stdout)
    except json.JSONDecodeError:
        result = {
            "schema_version": "1.0",
            "formal_result": False,
            "candidate_id": args.candidate_id,
            "probe_completed": False,
            "status": "INVALID_OUTPUT",
            "interpretation": "NON_FORMAL_WORKSTATION_PACED_STREAMING",
        }
    result.update(
        {
            **_resource_fields(run, method["memory_reference_bytes"]),
            "stdout_sha256": _output_digest(run.stdout),
            "stderr_sha256": _output_digest(run.stderr),
        }
    )
    return result


def main() -> int:
    args = _parser().parse_args()
    result = _run_child(args) if args.child else _run_supervised(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("probe_completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
