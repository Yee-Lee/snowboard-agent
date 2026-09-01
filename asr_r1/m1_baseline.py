"""Fail-closed supervisor for non-formal AR1M1 workstation baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .fixture_preflight import verify_controlled_smoke_fixture
from .paths import resolve_repo_resource


METHOD_MANIFEST = "asr_r1/manifests/m1_baseline_method.json"
IDENTITY_MANIFEST = "asr_r1/manifests/m1_identity_screening.json"


@dataclass(frozen=True)
class CapturedRun:
    status: str
    returncode: int
    elapsed_seconds: float
    peak_process_tree_rss_bytes: int
    stdout: str
    stderr: str
    peak_process_tree_pss_bytes: int = 0
    peak_process_tree_threads: int = 0
    process_tree_cpu_seconds: float = 0.0
    effective_cpu_cores: float = 0.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_external(path: Path, repo_root: Path, kind: str) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{kind} must remain outside the repository")


def _verify_file(path: Path, size_bytes: int, sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != size_bytes:
        raise ValueError("artifact size mismatch")
    if _sha256(path) != sha256:
        raise ValueError("artifact SHA-256 mismatch")


def _verify_sherpa_runtime_artifacts(
    paths: Sequence[Path], repo_root: Path
) -> None:
    identity = _load_json(IDENTITY_MANIFEST)
    expected = {
        item["filename"]: item
        for item in identity["shared_sherpa_runtime"][
            "workstation_cp312_x86_64_wheels"
        ]
    }
    supplied: dict[str, Path] = {}
    for path in paths:
        external = _verify_external(path, repo_root, "runtime artifact")
        if external.name in supplied:
            raise ValueError("duplicate runtime artifact")
        supplied[external.name] = external
    if set(supplied) != set(expected):
        raise ValueError("exact sherpa runtime artifact closure is required")
    for filename, item in expected.items():
        _verify_file(supplied[filename], item["size_bytes"], item["sha256"])


def _children(pid: int) -> set[int]:
    descendants: set[int] = set()
    pending = [pid]
    while pending:
        parent = pending.pop()
        children_path = Path("/proc") / str(parent) / "task" / str(parent) / "children"
        try:
            values = children_path.read_text(encoding="ascii").split()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        for value in values:
            child = int(value)
            if child not in descendants:
                descendants.add(child)
                pending.append(child)
    return descendants


def _rss_bytes(pid: int) -> int:
    status_path = Path("/proc") / str(pid) / "status"
    try:
        lines = status_path.read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return 0
    for line in lines:
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1_024
    return 0


def _pss_bytes(pid: int) -> int:
    rollup = Path("/proc") / str(pid) / "smaps_rollup"
    try:
        lines = rollup.read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return 0
    for line in lines:
        if line.startswith("Pss:"):
            return int(line.split()[1]) * 1_024
    return 0


def _thread_count(pid: int) -> int:
    status_path = Path("/proc") / str(pid) / "status"
    try:
        lines = status_path.read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return 0
    for line in lines:
        if line.startswith("Threads:"):
            return int(line.split()[1])
    return 0


def _cpu_ticks(pid: int) -> int:
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        value = stat_path.read_text(encoding="ascii")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return 0
    closing = value.rfind(")")
    if closing < 0:
        return 0
    fields = value[closing + 2 :].split()
    try:
        return int(fields[11]) + int(fields[12])
    except (IndexError, ValueError):
        return 0


def _process_tree_metrics(pid: int) -> tuple[int, int, int, int]:
    processes = {pid, *_children(pid)}
    return (
        sum(_rss_bytes(item) for item in processes),
        sum(_pss_bytes(item) for item in processes),
        sum(_thread_count(item) for item in processes),
        sum(_cpu_ticks(item) for item in processes),
    )


def _stop_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def run_monitored(
    argv: Sequence[str],
    timeout_seconds: float,
    cwd: Path | None = None,
) -> CapturedRun:
    """Run without a shell, observing process-tree RSS without a memory kill."""

    if not argv:
        raise ValueError("argv must not be empty")
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")
    environment = os.environ.copy()
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "localhost,127.0.0.1,::1",
            "no_proxy": "localhost,127.0.0.1,::1",
        }
    )
    started = time.monotonic()
    process = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        start_new_session=True,
    )
    peak_rss = 0
    peak_pss = 0
    peak_threads = 0
    peak_cpu_ticks = 0
    status = "COMPLETED"
    while process.poll() is None:
        rss, pss, threads, cpu_ticks = _process_tree_metrics(process.pid)
        peak_rss = max(peak_rss, rss)
        peak_pss = max(peak_pss, pss)
        peak_threads = max(peak_threads, threads)
        peak_cpu_ticks = max(peak_cpu_ticks, cpu_ticks)
        if time.monotonic() - started > timeout_seconds:
            status = "TIMEOUT"
            _stop_process_group(process)
            break
        time.sleep(0.02)
    rss, pss, threads, cpu_ticks = _process_tree_metrics(process.pid)
    peak_rss = max(peak_rss, rss)
    peak_pss = max(peak_pss, pss)
    peak_threads = max(peak_threads, threads)
    peak_cpu_ticks = max(peak_cpu_ticks, cpu_ticks)
    stdout, stderr = process.communicate()
    if status == "COMPLETED" and process.returncode != 0:
        status = "PROCESS_ERROR"
    elapsed_seconds = time.monotonic() - started
    cpu_seconds = peak_cpu_ticks / os.sysconf("SC_CLK_TCK")
    return CapturedRun(
        status=status,
        returncode=process.returncode,
        elapsed_seconds=elapsed_seconds,
        peak_process_tree_rss_bytes=peak_rss,
        stdout=stdout,
        stderr=stderr,
        peak_process_tree_pss_bytes=peak_pss,
        peak_process_tree_threads=peak_threads,
        process_tree_cpu_seconds=cpu_seconds,
        effective_cpu_cores=cpu_seconds / elapsed_seconds,
    )


def _output_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_json(relative: str) -> dict:
    path = resolve_repo_resource(_repo_root(), relative)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _row(candidate_id: str) -> tuple[dict, dict]:
    method = _load_json(METHOD_MANIFEST)
    identity = _load_json(IDENTITY_MANIFEST)
    command = next(
        (item for item in method["candidate_commands"] if item["candidate_id"] == candidate_id),
        None,
    )
    row = next(
        (item for item in identity["rows"] if item["candidate_id"] == candidate_id),
        None,
    )
    if command is None or row is None:
        raise ValueError("candidate is not in the frozen M1 packet")
    return method, {"command": command, "identity": row}


def _resource_fields(run: CapturedRun, reference_bytes: int) -> dict[str, object]:
    return {
        "peak_process_tree_rss_bytes": run.peak_process_tree_rss_bytes,
        "peak_process_tree_pss_bytes": run.peak_process_tree_pss_bytes,
        "peak_process_tree_threads": run.peak_process_tree_threads,
        "process_tree_cpu_seconds": run.process_tree_cpu_seconds,
        "effective_cpu_cores": run.effective_cpu_cores,
        "memory_reference_bytes": reference_bytes,
        "rss_above_reference": run.peak_process_tree_rss_bytes > reference_bytes,
        **_environment_fields(),
    }


def _environment_fields() -> dict[str, object]:
    release = platform.freedesktop_os_release()
    affinity = (
        len(os.sched_getaffinity(0))
        if hasattr(os, "sched_getaffinity")
        else os.cpu_count()
    )
    return {
        "execution_environment": "WORKSTATION_FEASIBILITY_NOT_PI5",
        "host_architecture": platform.machine(),
        "os_id": release.get("ID", "unknown"),
        "os_version_id": release.get("VERSION_ID", "unknown"),
        "affinity_vcpu_count": affinity,
        "gpu_acceleration": False,
        "pi5_hardware_result": False,
    }


def _failed_result(
    candidate_id: str, run: CapturedRun, reference_bytes: int
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "smoke_completed": False,
        "status": run.status,
        "returncode": run.returncode,
        "elapsed_seconds": run.elapsed_seconds,
        **_resource_fields(run, reference_bytes),
        "stdout_sha256": _output_digest(run.stdout),
        "stderr_sha256": _output_digest(run.stderr),
        "interpretation": "NON_FORMAL_WORKSTATION_SMOKE",
    }


def _run_sherpa(
    candidate_id: str,
    model_dir: Path,
    fixture: Path,
    timeout_seconds: int,
    memory_reference_bytes: int,
    num_threads: int,
) -> dict[str, object]:
    argv = [
        sys.executable,
        "-m",
        "asr_r1.m1_sherpa_smoke",
        "--candidate-id",
        candidate_id,
        "--model-dir",
        str(model_dir),
        "--fixture",
        str(fixture),
        "--num-threads",
        str(num_threads),
    ]
    run = run_monitored(argv, timeout_seconds, _repo_root())
    if run.status != "COMPLETED":
        return _failed_result(candidate_id, run, memory_reference_bytes)
    try:
        result = json.loads(run.stdout)
    except json.JSONDecodeError:
        return {
            **_failed_result(candidate_id, run, memory_reference_bytes),
            "status": "INVALID_OUTPUT",
        }
    result.update(
        {
            "smoke_completed": bool(result.get("final_non_empty")),
            "status": (
                "NON_FORMAL_SMOKE_COMPLETED"
                if result.get("final_non_empty")
                else "EMPTY_FINAL"
            ),
            **_resource_fields(run, memory_reference_bytes),
            "stdout_sha256": _output_digest(run.stdout),
            "stderr_sha256": _output_digest(run.stderr),
        }
    )
    return result


def _run_nemotron(
    candidate_id: str,
    binary: Path,
    model: Path,
    fixture: Path,
    timeout_seconds: int,
    memory_reference_bytes: int,
) -> dict[str, object]:
    common = ["--model", str(model), "--device", "cpu", "--language", "zh-CN"]
    smoke_argv = [
        str(binary),
        "transcribe",
        str(fixture),
        *common,
        "--stream",
        "--no-warmup",
        "--json",
    ]
    smoke = run_monitored(smoke_argv, timeout_seconds)
    if smoke.status != "COMPLETED":
        return _failed_result(candidate_id, smoke, memory_reference_bytes)
    try:
        transcript = json.loads(smoke.stdout)
        final_text = transcript["text"].strip()
    except (json.JSONDecodeError, KeyError, AttributeError):
        return {
            **_failed_result(candidate_id, smoke, memory_reference_bytes),
            "status": "INVALID_OUTPUT",
        }
    if not final_text:
        return {
            **_failed_result(candidate_id, smoke, memory_reference_bytes),
            "status": "EMPTY_FINAL",
        }

    bench_argv = [
        str(binary),
        "bench",
        "asr",
        str(fixture),
        *common,
        "--mode",
        "stream",
        "--concurrency",
        "1",
        "--repetitions",
        "1",
        "--warmup",
        "0",
        "--json",
    ]
    bench = run_monitored(bench_argv, timeout_seconds)
    if bench.status != "COMPLETED":
        return _failed_result(candidate_id, bench, memory_reference_bytes)
    try:
        payload = json.loads(bench.stdout)
        native = payload["runs"][0]
        load_seconds = float(payload["load_ms"]) / 1_000
        benchmark_warmup_seconds = float(payload["warmup_ms"]) / 1_000
        decode_seconds = float(native["wall_seconds"])
        rtfx = float(native["rtfx"])
        if min(load_seconds, benchmark_warmup_seconds, decode_seconds) < 0 or rtfx <= 0:
            raise ValueError("invalid rtfx")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return {
            **_failed_result(candidate_id, bench, memory_reference_bytes),
            "status": "INVALID_OUTPUT",
        }

    peak_rss = max(
        smoke.peak_process_tree_rss_bytes,
        bench.peak_process_tree_rss_bytes,
    )
    peak_pss = max(
        smoke.peak_process_tree_pss_bytes,
        bench.peak_process_tree_pss_bytes,
    )
    peak_threads = max(
        smoke.peak_process_tree_threads,
        bench.peak_process_tree_threads,
    )

    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": candidate_id,
        "smoke_completed": True,
        "status": "NON_FORMAL_SMOKE_COMPLETED",
        "fixture_id": "asr-clear-002-p0",
        "audio_seconds": float(native["audio_seconds"]),
        "model_load_seconds": load_seconds,
        "benchmark_warmup_seconds": benchmark_warmup_seconds,
        "full_utterance_decode_wall_seconds": decode_seconds,
        "full_utterance_rtf": 1 / rtfx,
        "peak_process_tree_rss_bytes": peak_rss,
        "peak_process_tree_pss_bytes": peak_pss,
        "peak_process_tree_threads": peak_threads,
        "benchmark_process_cpu_seconds": bench.process_tree_cpu_seconds,
        "benchmark_effective_cpu_cores": bench.effective_cpu_cores,
        "memory_reference_bytes": memory_reference_bytes,
        "rss_above_reference": peak_rss > memory_reference_bytes,
        **_environment_fields(),
        "final_non_empty": True,
        "final_text_sha256": _output_digest(final_text),
        "smoke_stdout_sha256": _output_digest(smoke.stdout),
        "smoke_stderr_sha256": _output_digest(smoke.stderr),
        "bench_stdout_sha256": _output_digest(bench.stdout),
        "bench_stderr_sha256": _output_digest(bench.stderr),
        "interpretation": "NON_FORMAL_WORKSTATION_SMOKE",
    }


def run_candidate(
    candidate_id: str,
    controlled_wav: Path,
    model_path: Path,
    artifact_archive: Path | None = None,
    runtime_binary: Path | None = None,
    runtime_archive: Path | None = None,
    runtime_artifacts: Sequence[Path] = (),
    num_threads: int = 2,
) -> dict[str, object]:
    """Verify identities, then run exactly one frozen candidate row."""

    repo_root = _repo_root()
    method, selected = _row(candidate_id)
    command = selected["command"]
    identity = selected["identity"]
    fixture = _verify_external(controlled_wav, repo_root, "controlled audio")
    verify_controlled_smoke_fixture(repo_root, fixture)
    model_path = _verify_external(model_path, repo_root, "model artifact")
    memory_reference = method["memory_reference_bytes"]
    timeout = command["timeout_seconds"]

    if command["model_kind"] == "zipformer_transducer":
        _verify_sherpa_runtime_artifacts(runtime_artifacts, repo_root)
        if artifact_archive is None:
            raise ValueError("Zipformer requires its verified external release archive")
        archive = _verify_external(artifact_archive, repo_root, "model archive")
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
        return _run_sherpa(
            candidate_id, model_path, fixture, timeout, memory_reference, num_threads
        )

    if command["model_kind"] == "wenet_ctc":
        _verify_sherpa_runtime_artifacts(runtime_artifacts, repo_root)
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
        return _run_sherpa(
            candidate_id, model_path, fixture, timeout, memory_reference, num_threads
        )

    if command["model_kind"] == "nemotron_3_5_q8_0":
        if runtime_binary is None or runtime_archive is None:
            raise ValueError("Nemotron requires external runtime binary and archive")
        binary = _verify_external(runtime_binary, repo_root, "runtime binary")
        archive = _verify_external(runtime_archive, repo_root, "runtime archive")
        checkpoint = identity["checkpoint"]
        runtime = identity["runtime"]["linux_x86_64_cpu_archive"]
        _verify_file(model_path, checkpoint["size_bytes"], checkpoint["sha256"])
        _verify_file(archive, runtime["size_bytes"], runtime["sha256"])
        executable = next(
            item
            for item in runtime["extracted_files"]
            if item["relative_path"] == "bin/nemo-speech"
        )
        _verify_file(binary, executable["size_bytes"], executable["sha256"])
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError("runtime binary is not executable")
        return _run_nemotron(
            candidate_id, binary, model_path, fixture, timeout, memory_reference
        )
    raise ValueError("unsupported frozen model kind")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--artifact-archive", type=Path)
    parser.add_argument("--runtime-binary", type=Path)
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--runtime-artifact", action="append", type=Path, default=[])
    parser.add_argument("--num-threads", type=int, default=2)
    args = parser.parse_args()
    result = run_candidate(
        candidate_id=args.candidate_id,
        controlled_wav=args.fixture,
        model_path=args.model_path,
        artifact_archive=args.artifact_archive,
        runtime_binary=args.runtime_binary,
        runtime_archive=args.runtime_archive,
        runtime_artifacts=args.runtime_artifact,
        num_threads=args.num_threads,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["smoke_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
