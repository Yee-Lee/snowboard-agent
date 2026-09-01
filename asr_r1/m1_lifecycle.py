"""Real-backend AR1M1 lifecycle verification with sanitized output only."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import wave
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import monotonic, process_time

from .fixture_preflight import verify_controlled_smoke_fixture
from .m1_baseline import (
    _output_digest,
    _repo_root,
    _resource_fields,
    _row,
    _verify_sherpa_runtime_artifacts,
    _verify_external,
    _verify_file,
    run_monitored,
)
from .nemo_adapter import NemoSpeechCBackend
from .protocol import ErrorCode, PCMChunk, ProtocolError
from .sherpa_adapter import (
    OnlineBackend,
    SherpaOnnxTransducerBackend,
    SherpaOnnxWenetCtcBackend,
    SherpaStreamingRuntime,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pcm_chunks(path: Path, chunk_duration_ms: int = 160) -> list[tuple[int, bytes]]:
    with wave.open(str(path), "rb") as source:
        frames_per_chunk = source.getframerate() * chunk_duration_ms // 1_000
        result = []
        frame_offset = 0
        while True:
            pcm = source.readframes(frames_per_chunk)
            if not pcm:
                break
            timestamp_ms = frame_offset * 1_000 // source.getframerate()
            result.append((timestamp_ms, pcm))
            frame_offset += len(pcm) // 2
        return result


def _feed(
    runtime: SherpaStreamingRuntime,
    session_id: str,
    chunks: list[tuple[int, bytes]],
    duration_ms: int,
) -> tuple[int, str, int, bool]:
    partials = 0
    for sequence, (timestamp_ms, pcm) in enumerate(chunks):
        event = runtime.accept_chunk(
            PCMChunk(session_id, sequence, timestamp_ms, pcm),
            decode_timeout_ms=30_000,
        )
        if event is not None:
            partials += 1
    final = runtime.finish_input(
        session_id,
        emitted_at_ms=duration_ms,
        decode_timeout_ms=60_000,
    )
    return (
        partials,
        _digest(final.text or ""),
        len(final.alternatives),
        final.alternatives[0].confidence is None,
    )


def run_lifecycle(
    candidate_id: str,
    backend: OnlineBackend,
    controlled_wav: Path,
) -> dict[str, object]:
    """Exercise one resident real backend without exposing transcript content."""

    identity = verify_controlled_smoke_fixture(_repo_root(), controlled_wav)
    chunks = _pcm_chunks(identity.path)
    if not chunks:
        raise ValueError("fixture produced no PCM chunks")
    duration_ms = round(identity.duration_seconds * 1_000)
    runtime = SherpaStreamingRuntime(backend)

    started = monotonic()
    cpu_started = process_time()
    load_started = monotonic()
    load_cpu_started = process_time()
    first_model_id = runtime.load_model()
    model_load_cpu_seconds = process_time() - load_cpu_started
    model_load_seconds = monotonic() - load_started
    second_model_id = runtime.load_model()
    resident_idempotent = first_model_id == second_model_id == candidate_id

    first = runtime.create_session()
    second = runtime.create_session()
    first_partials = 0
    second_partials = 0
    for sequence, (timestamp_ms, pcm) in enumerate(chunks):
        if runtime.accept_chunk(
            PCMChunk(first, sequence, timestamp_ms, pcm),
            decode_timeout_ms=30_000,
        ):
            first_partials += 1
        if runtime.accept_chunk(
            PCMChunk(second, sequence, timestamp_ms, pcm),
            decode_timeout_ms=30_000,
        ):
            second_partials += 1
    first_final = runtime.finish_input(first, duration_ms, decode_timeout_ms=60_000)
    second_final = runtime.finish_input(second, duration_ms, decode_timeout_ms=60_000)
    first_digest = _digest(first_final.text or "")
    second_digest = _digest(second_final.text or "")
    isolated_sessions_stable = first_digest == second_digest

    runtime.reset_session(first)
    reset_partials, reset_digest, reset_alternatives, reset_confidence_missing = _feed(
        runtime, first, chunks, duration_ms
    )
    reset_preserves_model = runtime.model_loaded and reset_digest == first_digest

    runtime.reset_session(second)
    runtime.accept_chunk(PCMChunk(second, 0, chunks[0][0], chunks[0][1]))
    cancel_event = runtime.cancel_session(second, emitted_at_ms=chunks[0][0] + 1)
    cancel_is_typed = cancel_event.error_code is ErrorCode.CANCELLED
    cancel_is_terminal = False
    try:
        runtime.accept_chunk(PCMChunk(second, 1, chunks[0][0] + 1, chunks[0][1]))
    except ProtocolError as exc:
        cancel_is_terminal = exc.code is ErrorCode.INVALID_STATE

    runtime.reset_session(second)
    recovered_partials, recovered_digest, _, _ = _feed(
        runtime, second, chunks, duration_ms
    )
    cancel_recovery = recovered_digest == first_digest

    error_session = runtime.create_session()
    out_of_order_is_typed = False
    try:
        runtime.accept_chunk(
            PCMChunk(error_session, 1, chunks[0][0], chunks[0][1])
        )
    except ProtocolError as exc:
        out_of_order_is_typed = exc.code is ErrorCode.OUT_OF_ORDER
    runtime.reset_session(error_session)
    error_recovery_partials, error_recovery_digest, _, _ = _feed(
        runtime, error_session, chunks, duration_ms
    )
    typed_error_recovery = error_recovery_digest == first_digest

    unknown_session_is_typed = False
    try:
        runtime.state("missing-session")
    except ProtocolError as exc:
        unknown_session_is_typed = exc.code is ErrorCode.SESSION_NOT_FOUND

    invalid_chunk_rejected = False
    try:
        PCMChunk("invalid", 0, 0, b"\x00")
    except ValueError:
        invalid_chunk_rejected = True

    shutdown_ms = runtime.shutdown(5_000)
    post_load_cpu_seconds = process_time() - load_cpu_started - model_load_cpu_seconds
    post_load_seconds = monotonic() - load_started - model_load_seconds
    bounded_shutdown = shutdown_ms <= 5_000 and runtime.session_count == 0
    shutdown_is_terminal = False
    try:
        runtime.create_session()
    except ProtocolError as exc:
        shutdown_is_terminal = exc.code is ErrorCode.SHUTDOWN

    partial_event_count = sum(
        (
            first_partials,
            second_partials,
            reset_partials,
            recovered_partials,
            error_recovery_partials,
        )
    )
    top_one_fallback = (
        len(first_final.alternatives) == 1
        and len(second_final.alternatives) == 1
        and reset_alternatives == 1
        and first_final.alternatives[0].confidence is None
        and second_final.alternatives[0].confidence is None
        and reset_confidence_missing
    )
    checks = {
        "resident_load_idempotent": resident_idempotent,
        "session_isolation_stable": isolated_sessions_stable,
        "reset_preserves_model": reset_preserves_model,
        "cancel_is_typed": cancel_is_typed,
        "cancel_is_terminal": cancel_is_terminal,
        "cancel_recovery": cancel_recovery,
        "out_of_order_is_typed": out_of_order_is_typed,
        "typed_error_recovery": typed_error_recovery,
        "unknown_session_is_typed": unknown_session_is_typed,
        "invalid_chunk_rejected": invalid_chunk_rejected,
        "top_one_fallback": top_one_fallback,
        "partial_events_observed": partial_event_count > 0,
        "bounded_shutdown": bounded_shutdown,
        "shutdown_is_terminal": shutdown_is_terminal,
    }
    completed = all(checks.values())
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "fixture_id": identity.fixture_id,
        "status": (
            "NON_FORMAL_LIFECYCLE_COMPLETED"
            if completed
            else "NON_FORMAL_LIFECYCLE_INCOMPLETE"
        ),
        "lifecycle_completed": completed,
        "model_load_seconds": model_load_seconds,
        "model_load_cpu_seconds": model_load_cpu_seconds,
        "model_load_effective_cpu_cores": (
            model_load_cpu_seconds / model_load_seconds if model_load_seconds else 0.0
        ),
        "post_load_wall_seconds": post_load_seconds,
        "post_load_cpu_seconds": post_load_cpu_seconds,
        "post_load_effective_cpu_cores": (
            post_load_cpu_seconds / post_load_seconds if post_load_seconds else 0.0
        ),
        "total_cpu_seconds": process_time() - cpu_started,
        "elapsed_seconds": monotonic() - started,
        "self_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * 1_024,
        "partial_event_count": partial_event_count,
        "stable_final_text_sha256": first_digest,
        "shutdown_ms": shutdown_ms,
        "checks": checks,
        "interpretation": "NON_FORMAL_WORKSTATION_LIFECYCLE",
    }


def _build_backend(args: argparse.Namespace) -> OnlineBackend:
    repo_root = _repo_root()
    _, selected = _row(args.candidate_id)
    command = selected["command"]
    identity = selected["identity"]
    model_path = _verify_external(args.model_path, repo_root, "model artifact")

    if command["model_kind"] == "zipformer_transducer":
        _verify_sherpa_runtime_artifacts(
            getattr(args, "runtime_artifact", []), repo_root
        )
        if args.artifact_archive is None:
            raise ValueError("Zipformer lifecycle requires the release archive")
        archive = _verify_external(args.artifact_archive, repo_root, "model archive")
        checkpoint = identity["checkpoint"]
        _verify_file(
            archive,
            checkpoint["artifact_size_bytes"],
            checkpoint["artifact_sha256"],
        )
        for component in checkpoint["extracted_files"]:
            _verify_file(
                model_path / component["filename"],
                component["size_bytes"],
                component["sha256"],
            )
        _verify_sherpa_version()
        return SherpaOnnxTransducerBackend(
            args.candidate_id, model_path, args.num_threads
        )

    if command["model_kind"] == "wenet_ctc":
        _verify_sherpa_runtime_artifacts(
            getattr(args, "runtime_artifact", []), repo_root
        )
        checkpoint = identity["checkpoint"]
        _verify_file(
            model_path / checkpoint["streaming_model"]["filename"],
            checkpoint["streaming_model"]["size_bytes"],
            checkpoint["streaming_model"]["sha256"],
        )
        _verify_file(
            model_path / checkpoint["tokens"]["filename"],
            checkpoint["tokens"]["size_bytes"],
            checkpoint["tokens"]["sha256"],
        )
        _verify_sherpa_version()
        return SherpaOnnxWenetCtcBackend(
            args.candidate_id, model_path, args.num_threads
        )

    if command["model_kind"] == "nemotron_3_5_q8_0":
        if args.runtime_archive is None or args.runtime_library is None:
            raise ValueError("Nemotron lifecycle requires runtime archive and C library")
        archive = _verify_external(args.runtime_archive, repo_root, "runtime archive")
        library = _verify_external(args.runtime_library, repo_root, "runtime library")
        checkpoint = identity["checkpoint"]
        runtime = identity["runtime"]["linux_x86_64_cpu_archive"]
        _verify_file(model_path, checkpoint["size_bytes"], checkpoint["sha256"])
        _verify_file(archive, runtime["size_bytes"], runtime["sha256"])
        library_identity = next(
            item
            for item in runtime["extracted_files"]
            if item["relative_path"] == "lib/libnemo_speech_asr_c.so.1"
        )
        _verify_file(
            library,
            library_identity["size_bytes"],
            library_identity["sha256"],
        )
        return NemoSpeechCBackend(args.candidate_id, model_path, library)

    raise ValueError("unsupported frozen model kind")


def _verify_sherpa_version() -> None:
    try:
        installed = version("sherpa-onnx")
    except PackageNotFoundError as exc:
        raise RuntimeError("sherpa-onnx 1.13.5 is not installed") from exc
    if installed != "1.13.5":
        raise RuntimeError("sherpa-onnx runtime identity mismatch")


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
    return run_lifecycle(args.candidate_id, _build_backend(args), fixture)


def _run_supervised(args: argparse.Namespace) -> dict[str, object]:
    method, selected = _row(args.candidate_id)
    run = run_monitored(
        [sys.executable, "-m", "asr_r1.m1_lifecycle", *sys.argv[1:], "--child"],
        selected["command"]["timeout_seconds"],
        _repo_root(),
    )
    if run.status != "COMPLETED":
        return {
            "schema_version": "1.0",
            "formal_result": False,
            "candidate_id": args.candidate_id,
            "lifecycle_completed": False,
            "status": run.status,
            "returncode": run.returncode,
            "stdout_sha256": _output_digest(run.stdout),
            "stderr_sha256": _output_digest(run.stderr),
            **_resource_fields(run, method["memory_reference_bytes"]),
            "interpretation": "NON_FORMAL_WORKSTATION_LIFECYCLE",
        }
    try:
        result = json.loads(run.stdout)
    except json.JSONDecodeError:
        result = {
            "schema_version": "1.0",
            "formal_result": False,
            "candidate_id": args.candidate_id,
            "lifecycle_completed": False,
            "status": "INVALID_OUTPUT",
            "interpretation": "NON_FORMAL_WORKSTATION_LIFECYCLE",
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
    return 0 if result.get("lifecycle_completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
