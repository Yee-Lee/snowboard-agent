"""Authorized Pi-only M4 combined and P9 formal execution runner."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .m3_core_hal import make_alsa_config
from .m3_formal_hal import (
    _require_outside_repo,
    _validate_device,
    assert_network_isolated,
    assert_target,
    cleanup_delta,
    runtime_snapshot,
    sha256_file,
)
from .m4_authorization import (
    load_authorization,
    validate_formal_authorization,
    validate_formal_result,
)
from .m4_combined_coordinator import M4CombinedCoordinator
from .m4_combined_domains import (
    AsyncP9Overlap,
    PersistentAsrDomain,
    PersistentTtsDomain,
    PersistentVadDomain,
)
from .m4_fixture_lock import load_fixture_lock, verify_fixture_files
from .m4_failure import FAILURE_TEST_ID, validate_failure_bundle
from .m4_failure_fixture import build_sustained_probe
from .m4_failure_runner import M4FailureRunner
from .m4_finalist_failure import FinalistFailureAdapter
from .m4_p9 import P9Client, locked_p9_paths
from .m4_packet import P9_1_TEST_ID, PACKET_ID, PUBLICATION_STATUS, load_packet, validate_repo_inputs


class M4ExecutionError(RuntimeError):
    """Retain partial stage/resource evidence after a formal execution error."""

    def __init__(
        self, cause: BaseException, resource_samples: list[dict[str, Any]],
        session_trace: list[dict[str, Any]],
    ) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.resource_samples = resource_samples
        self.session_trace = session_trace


class ResourceSampler:
    """Controlled raw sampler for the P9 capacity/thermal gate."""

    def __init__(self, pid_supplier: Callable[[], set[int]], interval_s: float = 0.5) -> None:
        self.interval_s = interval_s
        self.pid_supplier = pid_supplier
        self.records: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("M4 resource sampler is already running")
        self._thread = threading.Thread(target=self._run, name="m4-resource-sampler", daemon=False)
        self._thread.start()

    def stop(self) -> list[dict[str, Any]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s * 4 + 2.0)
            if self._thread.is_alive():
                raise RuntimeError("M4 resource sampler did not stop")
        return list(self.records)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.records.append(_resource_sample(self.pid_supplier()))
            self._stop.wait(self.interval_s)


def _resource_sample(pids: set[int]) -> dict[str, Any]:
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal"}:
            meminfo[key] = int(value.split()[0])
    temperature: int | None = None
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal.is_file():
        try:
            temperature = int(thermal.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    throttled: str | None = None
    if shutil.which("vcgencmd") is not None:
        completed = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            throttled = completed.stdout.strip()
    processes: dict[str, dict[str, int]] = {}
    for pid in sorted(pids):
        sample = _process_sample(pid)
        if sample is not None:
            processes[str(pid)] = sample
    return {
        "monotonic_s": round(time.monotonic(), 6),
        "mem_total_kib": meminfo.get("MemTotal"),
        "mem_available_kib": meminfo.get("MemAvailable"),
        "swap_total_kib": meminfo.get("SwapTotal"),
        "used_mib": round((meminfo.get("MemTotal", 0) - meminfo.get("MemAvailable", 0)) / 1024, 3),
        "temperature_millic": temperature,
        "throttled": throttled,
        "processes": processes,
    }


def _process_sample(pid: int) -> dict[str, int] | None:
    status = Path(f"/proc/{pid}/status")
    if not status.is_file():
        return None
    values: dict[str, int] = {}
    try:
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith(("VmRSS:", "Threads:")):
                key, value = line.split(":", 1)
                values[key] = int(value.split()[0])
        rollup = Path(f"/proc/{pid}/smaps_rollup")
        if rollup.is_file():
            for line in rollup.read_text(encoding="utf-8").splitlines():
                if line.startswith("Pss:"):
                    values["Pss"] = int(line.split()[1])
                    break
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        values["cpu_ticks"] = int(stat[13]) + int(stat[14])
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        return None
    return {
        "rss_kib": values.get("VmRSS", 0), "pss_kib": values.get("Pss", 0),
        "threads": values.get("Threads", 0), "cpu_ticks": values.get("cpu_ticks", 0),
    }


async def execute(args: argparse.Namespace, fixture_lock: dict[str, Any]) -> dict[str, Any]:
    audio, config = make_alsa_config(
        args.core_root, args.input_device, args.output_device, args.input_channel,
    )
    records = []
    for record in fixture_lock["records"]:
        records.append({**record, "wav_path": args.fixture_dir / record["filename"]})
    pipeline_lock = {**fixture_lock, "records": records}
    vad = PersistentVadDomain(
        args.repo_root, args.vad_runtime_python, args.vad_model, args.work_dir / "vad-bounded",
        args.operation_timeout,
    )
    asr = PersistentAsrDomain(
        args.binary, args.model, args.work_dir / "asr", args.operation_timeout,
    )
    tts = PersistentTtsDomain(
        args.repo_root, args.artifact_dir, args.runtime_python, args.work_dir / "tts",
        audio, config, args.operation_timeout,
    )
    coordinator = M4CombinedCoordinator(vad, asr, tts)
    p9_client: P9Client | None = None
    sampler = ResourceSampler(lambda: _active_pids(vad, asr, tts, p9_client))
    try:
        if args.phase == "p9_1":
            paths = locked_p9_paths(args.repo_root)
            p9_client = P9Client(paths["runner"], paths["schema"], paths["lock"])
            await asyncio.to_thread(p9_client.start, args.p9_ready_timeout)
        sampler.start()
        if p9_client is not None:
            session_results = await coordinator.run(
                pipeline_lock, AsyncP9Overlap(p9_client, args.operation_timeout),
            )
        else:
            session_results = await coordinator.run(pipeline_lock)
        samples = sampler.stop()
        if p9_client is not None:
            await asyncio.to_thread(p9_client.shutdown, args.p9_shutdown_timeout)
        return {
            "sessions": session_results,
            "session_count": len(session_results),
            "p9": _p9_summary(samples) if args.phase == "p9_1" else None,
            "resources": _resource_summary(samples),
            "_resource_samples": samples,
            "stream_format": "16000_HZ_MONO_S16_LE",
            "core_native_output_format": "48000_HZ_STEREO_S32_LE",
            "controller_thread_policy": {"OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"]},
            "network": assert_network_isolated(),
        }
    except BaseException as error:
        samples = sampler.stop() if sampler._thread is not None and sampler._thread.is_alive() else list(sampler.records)
        raise M4ExecutionError(error, samples, coordinator.trace) from error
    finally:
        if sampler._thread is not None and sampler._thread.is_alive():
            sampler.stop()
        if p9_client is not None and p9_client.process is not None:
            await asyncio.to_thread(p9_client.shutdown, args.p9_shutdown_timeout)


async def execute_failure(args: argparse.Namespace, fixture_lock: dict[str, Any]) -> dict[str, Any]:
    """Run the exact 12-case catalog without mixing it into the 20-session run."""
    records = fixture_lock["records"]
    if not isinstance(records, list) or not records:
        raise ValueError("M4 failure run requires the controlled fixture lock")
    record = {**records[0], "wav_path": args.fixture_dir / records[0]["filename"]}
    sustained = build_sustained_probe(record["wav_path"], args.work_dir / "failure-fixture" / "sustained.wav")
    audio, config = make_alsa_config(
        args.core_root, args.input_device, args.output_device, args.input_channel,
    )
    indices = {"vad": 0, "asr": 0, "tts": 0}

    def vad_factory() -> PersistentVadDomain:
        indices["vad"] += 1
        return PersistentVadDomain(args.repo_root, args.vad_runtime_python, args.vad_model,
                                   args.work_dir / f"failure-vad-{indices['vad']}", args.operation_timeout)

    def asr_factory() -> PersistentAsrDomain:
        indices["asr"] += 1
        return PersistentAsrDomain(args.binary, args.model,
                                   args.work_dir / f"failure-asr-{indices['asr']}", args.operation_timeout)

    def tts_factory() -> PersistentTtsDomain:
        indices["tts"] += 1
        return PersistentTtsDomain(args.repo_root, args.artifact_dir, args.runtime_python,
                                   args.work_dir / f"failure-tts-{indices['tts']}", audio, config,
                                   args.operation_timeout)

    timeout_text = "M4 controlled lifecycle timeout workload. " * 96
    probes = {
        "vad": {**record, "_failure_probe": {**record, "wav_path": sustained}},
        "asr": {**record, "bounded_wav": record["wav_path"],
                "_failure_probe": {**record, "bounded_wav": sustained}},
        "tts": {**record, "_failure_probe": {**record, "failure_text": timeout_text}},
    }
    runner = M4FailureRunner({
        "vad": FinalistFailureAdapter("vad", vad_factory, 0.1, args.failure_terminal_timeout),
        "asr": FinalistFailureAdapter("asr", asr_factory, 0.1, args.failure_terminal_timeout),
        "tts": FinalistFailureAdapter("tts", tts_factory, 0.1, args.failure_terminal_timeout),
    })
    cases = await runner.run(probes)
    return {
        "failure_cases": cases,
        "controller_thread_policy": {"OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"]},
        "network": assert_network_isolated(),
    }


def _p9_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        raise RuntimeError("M4 P9 resource sampler did not capture evidence")
    if any(item["swap_total_kib"] != 0 for item in samples):
        raise RuntimeError("M4 P9 requires zero swap for every resource sample")
    used = [float(item["used_mib"]) for item in samples]
    if any(value > 3584 for value in used):
        raise RuntimeError("M4 P9 capacity gate exceeded 3584 MiB")
    if any(item["throttled"] != "throttled=0x0" for item in samples):
        raise RuntimeError("M4 P9 throttling proof is absent or indicates a throttle")
    return {
        "sample_count": len(samples),
        "sample_interval_max_s": 0.5,
        "peak_used_mib": max(used),
        "capacity_gate_mib": 3584,
        "all_samples_within_capacity_gate": True,
    }


def _resource_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        raise RuntimeError("M4 resource sampler did not capture evidence")
    temperatures = [item["temperature_millic"] for item in samples if item["temperature_millic"] is not None]
    return {
        "sample_count": len(samples),
        "sample_interval_max_s": 0.5,
        "peak_used_mib": max(float(item["used_mib"]) for item in samples),
        "peak_temperature_millic": max(temperatures) if temperatures else None,
        "throttle_observations": sorted({str(item["throttled"]) for item in samples}),
    }


def _active_pids(
    vad: PersistentVadDomain,
    asr: PersistentAsrDomain,
    tts: PersistentTtsDomain,
    p9: P9Client | None,
) -> set[int]:
    pids: set[int] = set()
    if vad.process is not None:
        pids.add(vad.process.pid)
    if asr.worker is not None and asr.worker.pid is not None:
        pids.add(asr.worker.pid)
    if tts.process is not None:
        pids.add(tts.process.pid)
    if p9 is not None:
        if p9.process is not None:
            pids.add(p9.process.pid)
        pids.update(p9.worker_pids)
    return pids


def _result(args: argparse.Namespace, authorization: dict[str, Any], result: str, cleanup: dict[str, int], evidence: Path, details: dict[str, Any]) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "packet_id": PACKET_ID,
        "test_id": (
            P9_1_TEST_ID if args.phase == "p9_1" else
            FAILURE_TEST_ID if args.phase == "failure" else "M4-COMBINED-20-SESSION-001"
        ),
        "publication_status": PUBLICATION_STATUS,
        "result": result,
        "audio_execution_sha": authorization["audio_execution_sha"],
        "core_execution_sha": authorization["core_execution_sha"],
        "command": list(sys.argv),
        "cleanup": cleanup,
        "controlled_evidence": {"locator": args.controlled_locator, "sha256": sha256_file(evidence)},
        "details": details,
    }
    validate_formal_result(document)
    return document


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("phase", choices=("p9_1", "combined", "failure"))
    root.add_argument("--packet", type=Path, required=True)
    root.add_argument("--authorization", type=Path, required=True)
    root.add_argument("--repo-root", type=Path, required=True)
    root.add_argument("--core-root", type=Path, required=True)
    root.add_argument("--fixture-dir", type=Path, required=True)
    root.add_argument("--fixture-lock", type=Path, required=True)
    root.add_argument("--artifact-dir", type=Path, required=True)
    root.add_argument("--runtime-python", type=Path, required=True)
    root.add_argument("--binary", type=Path, required=True)
    root.add_argument("--model", type=Path, required=True)
    root.add_argument("--vad-runtime-python", type=Path, required=True)
    root.add_argument("--vad-model", type=Path, required=True)
    root.add_argument("--work-dir", type=Path, required=True)
    root.add_argument("--input-device", required=True)
    root.add_argument("--output-device", required=True)
    root.add_argument("--input-channel", type=int, choices=(0, 1), required=True)
    root.add_argument("--controlled-locator", required=True)
    root.add_argument("--evidence-log", type=Path, required=True)
    root.add_argument("--output", type=Path, required=True)
    root.add_argument("--operation-timeout", type=float, default=10.0)
    root.add_argument("--p9-ready-timeout", type=float, default=10.0)
    root.add_argument("--p9-shutdown-timeout", type=float, default=5.0)
    root.add_argument("--failure-terminal-timeout", type=float, default=5.0)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.work_dir.exists() or args.output.exists() or args.evidence_log.exists():
        raise ValueError("M4 formal work, result and controlled evidence paths must be new")
    if min(args.operation_timeout, args.p9_ready_timeout, args.p9_shutdown_timeout, args.failure_terminal_timeout) <= 0:
        raise ValueError("M4 formal timeouts must be positive")
    _validate_device(args.input_device, "input device")
    _validate_device(args.output_device, "output device")
    for name, path in (
        ("fixture directory", args.fixture_dir), ("fixture lock", args.fixture_lock),
        ("artifact directory", args.artifact_dir), ("work directory", args.work_dir),
        ("controlled evidence log", args.evidence_log),
    ):
        _require_outside_repo(path, args.repo_root, name)
    authorization = load_authorization(args.authorization)
    validate_formal_authorization(authorization, args.packet, args.repo_root, args.core_root)
    packet = load_packet(args.packet)
    validate_repo_inputs(packet, args.repo_root)
    fixture_lock = load_fixture_lock(args.fixture_lock, authorization["audio_execution_sha"])
    verify_fixture_files(fixture_lock, args.fixture_dir)
    platform_identity = assert_target()
    if args.phase == "p9_1":
        _assert_p9_target()
    _assert_controller_thread_policy()
    assert_network_isolated()
    before = runtime_snapshot()
    result = "PASS"
    details: dict[str, Any]
    try:
        args.work_dir.mkdir(parents=True)
        details = asyncio.run(execute_failure(args, fixture_lock)) if args.phase == "failure" else asyncio.run(execute(args, fixture_lock))
    except Exception as error:
        result = "FAIL"
        if isinstance(error, M4ExecutionError):
            details = {
                "error_type": type(error.cause).__name__, "error": str(error.cause),
                "partial_session_trace": error.session_trace,
                "_resource_samples": error.resource_samples,
            }
        else:
            details = {"error_type": type(error).__name__, "error": str(error)}
    after = runtime_snapshot()
    cleanup = cleanup_delta(before, after)
    if any(cleanup.values()):
        result = "FAIL"
    details["platform"] = platform_identity
    details["input_device"] = args.input_device
    details["output_device"] = args.output_device
    details["input_channel"] = args.input_channel
    resource_samples = details.pop("_resource_samples", [])
    raw_evidence = {
        "schema_version": "1.0", "packet_id": PACKET_ID,
        "phase": args.phase, "generated_at_utc": datetime.now(UTC).isoformat(),
        "result": result, "before": {**before, "children": sorted(before["children"])},
        "after": {**after, "children": sorted(after["children"])},
        "cleanup": cleanup, "resource_samples": resource_samples, "details": details,
    }
    args.evidence_log.parent.mkdir(parents=True, exist_ok=True)
    with args.evidence_log.open("x", encoding="utf-8") as destination:
        json.dump(raw_evidence, destination, indent=2, sort_keys=True)
        destination.write("\n")
    if args.phase == "failure" and result == "PASS":
        failure_bundle = {
            "schema_version": "1.0", "packet_id": PACKET_ID, "test_id": FAILURE_TEST_ID,
            "publication_status": PUBLICATION_STATUS,
            "audio_execution_sha": authorization["audio_execution_sha"],
            "core_execution_sha": authorization["core_execution_sha"],
            "controlled_evidence": {"locator": args.controlled_locator, "sha256": sha256_file(args.evidence_log)},
            "cases": details.get("failure_cases", []), "cleanup": cleanup,
            "proposed_disposition": result,
            "decision_boundary": "DRAFT: User confirmation is required before publication.",
        }
        validate_failure_bundle(failure_bundle)
        details["failure_bundle"] = failure_bundle
    elif args.phase == "failure":
        # The raw controlled evidence retains the partial/failed case.  Do not
        # fabricate a complete twelve-case bundle for an unsuccessful run.
        details["failure_bundle_status"] = "INCOMPLETE_FAILURE_EVIDENCE_RETAINED"
    document = _result(args, authorization, result, cleanup, args.evidence_log, details)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(document, destination, indent=2, sort_keys=True)
        destination.write("\n")
    print(json.dumps({"phase": args.phase, "result": result, "output": str(args.output)}, sort_keys=True))
    return 0 if result == "PASS" else 1


def _assert_p9_target() -> None:
    os_release = Path("/etc/os-release")
    values: dict[str, str] = {}
    if os_release.is_file():
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    if values.get("ID") != "debian" or values.get("VERSION_ID") != "13":
        raise ValueError("M4 P9 requires Debian 13")
    mem_total_kib = next(
        (int(line.split()[1]) for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
         if line.startswith("MemTotal:")),
        0,
    )
    if not 3_500_000 <= mem_total_kib <= 4_500_000:
        raise ValueError("M4 P9 requires the Pi 5 4GB memory envelope")
    swap_total_kib = next(
        (int(line.split()[1]) for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
         if line.startswith("SwapTotal:")),
        -1,
    )
    if swap_total_kib != 0:
        raise ValueError("M4 P9 requires SwapTotal: 0 before execution")


def _assert_controller_thread_policy() -> None:
    if os.environ.get("OPENBLAS_NUM_THREADS") != "1":
        raise ValueError("M4 formal controller requires OPENBLAS_NUM_THREADS=1")


if __name__ == "__main__":
    raise SystemExit(main())
