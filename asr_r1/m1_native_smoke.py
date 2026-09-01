"""Direct-backend, sanitized AR1M1 native API smoke probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path
from time import monotonic, process_time

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
from .sherpa_adapter import OnlineBackend


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _float_samples(pcm: bytes) -> tuple[float, ...]:
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    return tuple(sample / 32768.0 for sample in samples)


def _drain(backend: OnlineBackend, stream: object) -> str:
    text = ""
    while backend.is_ready(stream):
        backend.decode_stream(stream)
        text = backend.get_text(stream).strip()
    return text or backend.get_text(stream).strip()


def run_native_smoke(
    candidate_id: str,
    backend: OnlineBackend,
    controlled_wav: Path,
    chunk_duration_ms: int = 160,
) -> dict[str, object]:
    """Use the backend API directly, without the AR1 session adapter."""

    identity = verify_controlled_smoke_fixture(_repo_root(), controlled_wav)
    chunks = _pcm_chunks(identity.path, chunk_duration_ms)
    if not chunks:
        raise ValueError("fixture produced no PCM chunks")

    load_wall_started = monotonic()
    load_cpu_started = process_time()
    backend.load_model()
    load_cpu_seconds = process_time() - load_cpu_started
    load_wall_seconds = monotonic() - load_wall_started
    if backend.model_id != candidate_id:
        raise ValueError("backend model identity mismatch")

    decode_wall_started = monotonic()
    decode_cpu_started = process_time()
    partial_hashes: list[str] = []
    try:
        stream = backend.create_stream()
        try:
            for _, pcm in chunks:
                backend.accept_waveform(stream, _float_samples(pcm))
                text = _drain(backend, stream)
                digest = _digest(text) if text else ""
                if digest and (
                    not partial_hashes or digest != partial_hashes[-1]
                ):
                    partial_hashes.append(digest)
            backend.input_finished(stream)
            final_text = _drain(backend, stream)
        finally:
            backend.close_stream(stream)
    finally:
        backend.close()
    decode_cpu_seconds = process_time() - decode_cpu_started
    decode_wall_seconds = monotonic() - decode_wall_started

    completed = bool(final_text) and bool(partial_hashes)
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "fixture_id": identity.fixture_id,
        "native_smoke_completed": completed,
        "status": (
            "NON_FORMAL_NATIVE_SMOKE_COMPLETED"
            if completed
            else "NON_FORMAL_NATIVE_SMOKE_INCOMPLETE"
        ),
        "model_load_wall_seconds": load_wall_seconds,
        "model_load_cpu_seconds": load_cpu_seconds,
        "model_load_effective_cpu_cores": load_cpu_seconds / load_wall_seconds,
        "full_utterance_decode_wall_seconds": decode_wall_seconds,
        "decode_cpu_seconds": decode_cpu_seconds,
        "decode_effective_cpu_cores": decode_cpu_seconds / decode_wall_seconds,
        "full_utterance_rtf": decode_wall_seconds / identity.duration_seconds,
        "partial_event_count": len(partial_hashes),
        "partial_digest_chain_sha256": _digest("\n".join(partial_hashes)),
        "final_text_sha256": _digest(final_text),
        "interpretation": "NON_FORMAL_WORKSTATION_NATIVE_API_SMOKE",
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
    return run_native_smoke(args.candidate_id, _build_backend(args), fixture)


def _run_supervised(args: argparse.Namespace) -> dict[str, object]:
    method, selected = _row(args.candidate_id)
    run = run_monitored(
        [sys.executable, "-m", "asr_r1.m1_native_smoke", *sys.argv[1:], "--child"],
        selected["command"]["timeout_seconds"],
        _repo_root(),
    )
    if run.status != "COMPLETED":
        result: dict[str, object] = {
            "schema_version": "1.0",
            "formal_result": False,
            "candidate_id": args.candidate_id,
            "native_smoke_completed": False,
            "status": run.status,
            "returncode": run.returncode,
            "interpretation": "NON_FORMAL_WORKSTATION_NATIVE_API_SMOKE",
        }
    else:
        try:
            result = json.loads(run.stdout)
        except json.JSONDecodeError:
            result = {
                "schema_version": "1.0",
                "formal_result": False,
                "candidate_id": args.candidate_id,
                "native_smoke_completed": False,
                "status": "INVALID_OUTPUT",
                "interpretation": "NON_FORMAL_WORKSTATION_NATIVE_API_SMOKE",
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
    return 0 if result.get("native_smoke_completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
