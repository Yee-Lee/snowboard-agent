"""Run review-only Q8 screening on VAD-label-bounded frozen fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_qualification import PLAN_SHA256, WARMUPS, numeric_summary, thermal_observation, verify_fixtures
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_preflight import (
    GIT_SHA_RE,
    PRIMARY_ID,
    create_preflight_report,
    repo_root,
    resolve_controlled_path,
    sha256_file,
)
from .m4a_whispercpp_qualification import NativeWhisperWorker, validate_build_report


REPORT_ID = "POC-AUDIO-PERF-2026-001-Q8-BOUNDED"
LABEL_INDEX_SHA256 = "85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74"
SAMPLE_RATE_HZ = 16000


def _read_task_ticks(pid: int) -> tuple[dict[int, int], set[int]]:
    ticks: dict[int, int] = {}
    cores: set[int] = set()
    for path in Path(f"/proc/{pid}/task").glob("*/stat"):
        try:
            text = path.read_text(encoding="ascii")
            fields = text[text.rfind(")") + 2 :].split()
            ticks[int(path.parent.name)] = int(fields[11]) + int(fields[12])
            cores.add(int(fields[36]))
        except (FileNotFoundError, IndexError, ValueError):
            continue
    return ticks, cores


def _read_core_ticks() -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for line in Path("/proc/stat").read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) < 5 or not fields[0].startswith("cpu") or fields[0] == "cpu":
            continue
        values = [int(value) for value in fields[1:]]
        total = sum(values)
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        result[fields[0]] = (total, idle)
    return result


def _read_frequencies() -> dict[str, int]:
    result: dict[str, int] = {}
    for path in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
        try:
            result[path.parents[1].name] = int(path.read_text(encoding="ascii").strip())
        except (FileNotFoundError, ValueError):
            continue
    return result


def cpu_environment() -> dict[str, Any]:
    policies: dict[str, Any] = {}
    for policy in Path("/sys/devices/system/cpu/cpufreq").glob("policy[0-9]*"):
        values: dict[str, Any] = {}
        for name in ("scaling_governor", "scaling_min_freq", "scaling_max_freq", "cpuinfo_max_freq"):
            path = policy / name
            try:
                text = path.read_text(encoding="ascii").strip()
                values[name] = int(text) if text.isdecimal() else text
            except FileNotFoundError:
                continue
        policies[policy.name] = values
    return {"logical_cpu_count": os.cpu_count(), "cpufreq_policies": policies}


class ProcessActivityMonitor:
    """Low-rate /proc sampler proving task/core use without external tools."""

    def __init__(self, pid: int, interval_seconds: float = 0.05) -> None:
        self.pid = pid
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.first_tasks: dict[int, int] = {}
        self.last_tasks: dict[int, int] = {}
        self.previous_tasks: dict[int, int] = {}
        self.max_task_count = 0
        self.max_active_tasks = 0
        self.cores_observed: set[int] = set()
        self.core_start: dict[str, tuple[int, int]] = {}
        self.core_end: dict[str, tuple[int, int]] = {}
        self.frequency_min: dict[str, int] = {}
        self.frequency_max: dict[str, int] = {}
        self.sample_count = 0

    def _sample(self) -> None:
        tasks, cores = _read_task_ticks(self.pid)
        if not self.first_tasks:
            self.first_tasks = dict(tasks)
        for task_id, value in tasks.items():
            self.first_tasks.setdefault(task_id, value)
            self.last_tasks[task_id] = value
        active = sum(value > self.previous_tasks.get(task_id, value)
                     for task_id, value in tasks.items())
        self.max_active_tasks = max(self.max_active_tasks, active)
        self.previous_tasks = tasks
        self.max_task_count = max(self.max_task_count, len(tasks))
        self.cores_observed.update(cores)
        core_ticks = _read_core_ticks()
        if not self.core_start:
            self.core_start = core_ticks
        self.core_end = core_ticks
        for core, frequency in _read_frequencies().items():
            self.frequency_min[core] = min(self.frequency_min.get(core, frequency), frequency)
            self.frequency_max[core] = max(self.frequency_max.get(core, frequency), frequency)
        self.sample_count += 1

    def start(self) -> None:
        self._sample()

        def run() -> None:
            while not self.stop_event.wait(self.interval_seconds):
                self._sample()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        self._sample()
        clock_ticks = os.sysconf("SC_CLK_TCK")
        per_thread_ms = sorted(
            (round(1000.0 * (self.last_tasks[task] - first) / clock_ticks, 3)
             for task, first in self.first_tasks.items() if task in self.last_tasks),
            reverse=True,
        )
        core_utilization: dict[str, float] = {}
        for core, (start_total, start_idle) in self.core_start.items():
            end_total, end_idle = self.core_end.get(core, (start_total, start_idle))
            total_delta = end_total - start_total
            idle_delta = end_idle - start_idle
            if total_delta > 0:
                core_utilization[core] = round(100.0 * (total_delta - idle_delta) / total_delta, 3)
        return {
            "sample_interval_ms": round(self.interval_seconds * 1000),
            "sample_count": self.sample_count,
            "maximum_worker_task_count": self.max_task_count,
            "maximum_simultaneously_active_tasks": self.max_active_tasks,
            "worker_thread_cpu_ms_descending": per_thread_ms,
            "cores_observed": sorted(self.cores_observed),
            "per_core_utilization_percent": core_utilization,
            "frequency_khz_min": self.frequency_min,
            "frequency_khz_max": self.frequency_max,
        }


def _validate_labels(document: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    accepted = document.get("accepted")
    expected = {str(item["fixture_id"]): item for item in plan["utterances"]}
    if not isinstance(accepted, dict) or set(accepted) != set(expected):
        raise ValueError("VAD label index does not contain the frozen 50 ASR fixtures")
    for fixture_id, label in accepted.items():
        intervals = label.get("speech_intervals_ms")
        required_count = 1 if expected[fixture_id]["vad_class"] == "clear_speech" else 2
        if not isinstance(intervals, list) or len(intervals) != required_count:
            raise ValueError(f"invalid speech interval count: {fixture_id}")
        previous_end = -1
        for interval in intervals:
            if not isinstance(interval, list) or len(interval) != 2 \
                    or not all(isinstance(value, int) for value in interval) \
                    or interval[0] < previous_end or interval[0] >= interval[1]:
                raise ValueError(f"invalid speech intervals: {fixture_id}")
            previous_end = interval[1]
        pause = label.get("internal_pause_interval_ms")
        if required_count == 2 and pause != [intervals[0][1], intervals[1][0]]:
            raise ValueError(f"internal pause is not preserved by the label index: {fixture_id}")
        if required_count == 1 and pause is not None:
            raise ValueError(f"clear-speech fixture has an internal pause: {fixture_id}")
    return accepted


def derive_bounded_fixtures(
    fixture_dir: Path, label_index: Path, plan: dict[str, Any], output_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(label_index) != LABEL_INDEX_SHA256:
        raise ValueError("frozen VAD label index checksum mismatch")
    if output_dir.exists():
        raise ValueError("bounded fixture directory must be new")
    accepted = _validate_labels(json.loads(label_index.read_text(encoding="utf-8")), plan)
    fixture_identities = verify_fixtures(fixture_dir, plan)
    identities = {str(item["fixture_id"]): item for item in fixture_identities}
    output_dir.mkdir(parents=True)
    records: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    for plan_item in plan["utterances"]:
        fixture_id = str(plan_item["fixture_id"])
        source = fixture_dir / f"{fixture_id}.wav"
        intervals = accepted[fixture_id]["speech_intervals_ms"]
        start_ms, end_ms = intervals[0][0], intervals[-1][1]
        with wave.open(str(source), "rb") as input_wav:
            if (input_wav.getframerate(), input_wav.getnchannels(), input_wav.getsampwidth(),
                    input_wav.getcomptype()) != (SAMPLE_RATE_HZ, 1, 2, "NONE"):
                raise ValueError(f"delivered fixture format changed: {fixture_id}")
            total_frames = input_wav.getnframes()
            start_frame = start_ms * SAMPLE_RATE_HZ // 1000
            end_frame = end_ms * SAMPLE_RATE_HZ // 1000
            if start_ms * SAMPLE_RATE_HZ % 1000 or end_ms * SAMPLE_RATE_HZ % 1000 \
                    or start_frame < 0 or end_frame > total_frames or start_frame >= end_frame:
                raise ValueError(f"VAD label is outside delivered audio: {fixture_id}")
            input_wav.setpos(start_frame)
            payload = input_wav.readframes(end_frame - start_frame)
        destination = output_dir / f"{fixture_id}.wav"
        with wave.open(str(destination), "wb") as output_wav:
            output_wav.setnchannels(1)
            output_wav.setsampwidth(2)
            output_wav.setframerate(SAMPLE_RATE_HZ)
            output_wav.writeframes(payload)
        input_duration = (end_frame - start_frame) / SAMPLE_RATE_HZ
        speech_duration = sum(end - start for start, end in intervals) / 1000.0
        records[fixture_id] = {
            "source_sha256": identities[fixture_id]["sha256"],
            "bounded_sha256": sha256_file(destination),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "audio_duration_seconds": round(input_duration, 6),
            "labelled_speech_duration_seconds": round(speech_duration, 6),
            "internal_pause_duration_seconds": round(input_duration - speech_duration, 6),
            "derivation": "single_contiguous_first_speech_start_to_last_speech_end_no_concatenation",
        }
        item = dict(plan_item)
        item.update(records[fixture_id])
        items.append(item)
    manifest = {
        "schema_version": "1.0",
        "manifest_id": "POC-AUDIO-PERF-2026-001-VAD-BOUNDED-INPUT",
        "vad_label_index_sha256": LABEL_INDEX_SHA256,
        "recording_plan_sha256": PLAN_SHA256,
        "fixture_count": len(records),
        "source_fixture_set_sha256": hashlib.sha256(
            json.dumps(fixture_identities, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "records": records,
    }
    manifest_path = output_dir / "bounded_fixture_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest, items


def _score(item: dict[str, Any], hypothesis: str, metrics: dict[str, Any]) -> dict[str, Any]:
    reference = normalize_asr(str(item["reference_text"]))
    normalized = normalize_asr(hypothesis)
    controller_ms = float(metrics["latency_ms"])
    audio_duration = float(item["audio_duration_seconds"])
    speech_duration = float(item["labelled_speech_duration_seconds"])
    return {
        "fixture_id": item["fixture_id"],
        "category": item["category"],
        "controller_latency_ms": controller_ms,
        "native_inference_ms": metrics["native_inference_ms"],
        "cpu_ms": metrics["cpu_ms"],
        "peak_rss_mib": metrics["peak_rss_mib"],
        "audio_duration_seconds": audio_duration,
        "labelled_speech_duration_seconds": speech_duration,
        "input_rtf": round(controller_ms / 1000.0 / audio_duration, 6),
        "speech_rtf": round(controller_ms / 1000.0 / speech_duration, 6),
        "effective_cpu_cores": round(float(metrics["cpu_ms"]) / float(metrics["native_inference_ms"]), 6),
        "reference_length": len(reference),
        "hypothesis_length": len(normalized),
        "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode("utf-8")).hexdigest(),
        "raw_transcript_emitted": False,
    }


def run_loaded_suite(
    command: list[str], stderr_path: Path, items: list[dict[str, Any]], fixture_dir: Path,
    cycles: int, warmups: int,
) -> dict[str, Any]:
    worker = NativeWhisperWorker(command, stderr_path)
    results: list[dict[str, Any]] = []
    monitor: ProcessActivityMonitor | None = None
    activity: dict[str, Any] = {}
    try:
        worker.start()
        monitor = ProcessActivityMonitor(int(worker.pid))
        monitor.start()
        for warmup in range(warmups):
            worker.transcribe(fixture_dir / f"{items[warmup % len(items)]['fixture_id']}.wav")
        for cycle in range(1, cycles + 1):
            for item in items:
                metrics = worker.transcribe(fixture_dir / f"{item['fixture_id']}.wav")
                result = _score(item, metrics.pop("hypothesis"), metrics)
                result["cycle"] = cycle
                results.append(result)
        terminal_status, error_code = "SUCCESS", None
    except Exception as error:  # retained in raw report without transcript or path disclosure
        terminal_status, error_code = "ERROR", type(error).__name__
    finally:
        if monitor is not None:
            activity = monitor.stop()
        cleanup = worker.stop()
    return {
        "terminal_status": terminal_status,
        "error_code": error_code,
        "load_ms": worker.load_ms,
        "warmups": warmups,
        "cycles": cycles,
        "results": results,
        "activity": activity,
        "peak_rss_mib": max((float(item["peak_rss_mib"]) for item in results), default=None),
        "cleanup": cleanup,
    }


def summarize(run: dict[str, Any], expected_results: int) -> dict[str, Any]:
    results = run["results"] if run["terminal_status"] == "SUCCESS" else []
    categories: dict[str, Any] = {}
    for category in sorted({str(item["category"]) for item in results}):
        selected = [item for item in results if item["category"] == category]
        reference_length = sum(int(item["reference_length"]) for item in selected)
        edits = sum(int(item["edit_distance"]) for item in selected)
        categories[category] = {
            "result_count": len(selected),
            "cer_percent": round(100.0 * edits / reference_length, 6) if reference_length else None,
            "sentence_correctness_percent": round(
                100.0 * sum(bool(item["sentence_correct"]) for item in selected) / len(selected), 6
            ) if selected else None,
        }
    core_cer = categories.get("taiwan_mandarin", {}).get("cer_percent")
    sentence_correctness = round(
        100.0 * sum(bool(item["sentence_correct"]) for item in results) / len(results), 6
    ) if results else None
    complete = len(results) == expected_results
    return {
        "execution_complete": complete,
        "gate_eligible": False,
        "quality": {
            "taiwan_mandarin_core_cer_percent": core_cer,
            "overall_sentence_correctness_percent": sentence_correctness,
            "thresholds_observed_met": bool(complete and core_cer is not None and core_cer <= 20.0
                                             and sentence_correctness is not None
                                             and sentence_correctness >= 70.0),
        },
        "performance": {
            "controller_latency_ms": numeric_summary([float(item["controller_latency_ms"]) for item in results]),
            "native_inference_ms": numeric_summary([float(item["native_inference_ms"]) for item in results]),
            "cpu_ms": numeric_summary([float(item["cpu_ms"]) for item in results]),
            "input_rtf": numeric_summary([float(item["input_rtf"]) for item in results]),
            "speech_rtf": numeric_summary([float(item["speech_rtf"]) for item in results]),
            "effective_cpu_cores": numeric_summary([float(item["effective_cpu_cores"]) for item in results]),
            "peak_rss_mib": run.get("peak_rss_mib"),
            "rtf_threshold_observed_met": bool(
                complete and results and numeric_summary([float(item["input_rtf"]) for item in results])["p95"] <= 2.0
            ),
            "final_transcript_absolute_latency": "OBSERVATION_ONLY_DEFERRED_FROM_M2_GATE",
        },
        "categories": categories,
        "activity": run.get("activity", {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--vad-label-index", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("screening", "diagnostic"), required=True)
    parser.add_argument("--threads", type=int, choices=(1, 2, 4), required=True)
    parser.add_argument("--hot-repetitions", type=int, choices=(1, 2), default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full lowercase Git SHA")
    root = repo_root().resolve()
    if args.work_dir.exists() or args.output.exists() \
            or args.work_dir.resolve().is_relative_to(root) or args.output.resolve().is_relative_to(root):
        raise ValueError("new work/output paths outside the repository are required")
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    manifest = json.loads((root / "poc_audio/manifests/m4a_asr_recovery_ack002.json").read_text(encoding="utf-8"))
    artifact_report = create_preflight_report(manifest, PRIMARY_ID, args.artifact_dir, args.source_sha, None)
    build_report = json.loads(args.build_report.read_text(encoding="utf-8"))
    validate_build_report(build_report, PRIMARY_ID, args.source_sha, args.binary)
    plan_path = root / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    if sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("frozen ASR recording plan checksum mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    args.work_dir.mkdir(parents=True)
    bounded_dir = args.work_dir / "bounded-fixtures"
    bounded_manifest, items = derive_bounded_fixtures(
        args.fixture_dir, args.vad_label_index, plan, bounded_dir,
    )
    if args.mode == "screening":
        items = [max(items, key=lambda item: (float(item["audio_duration_seconds"]), item["fixture_id"]))]
        repetitions, warmups = 1, 1
    else:
        repetitions, warmups = args.hot_repetitions, WARMUPS
    candidate = next(item for item in manifest["candidates"] if item["candidate_id"] == PRIMARY_ID)
    model = resolve_controlled_path(manifest, candidate["controlled_locator"], candidate["filename"], args.artifact_dir)
    command = [str(args.binary.resolve()), "--model", str(model), "--threads", str(args.threads)]
    owners_before = audio_device_owner_count()
    thermal_before = thermal_observation()
    run = run_loaded_suite(command, args.work_dir / "worker.stderr.log", items, bounded_dir, repetitions, warmups)
    assert_network_isolated()
    owners_after = audio_device_owner_count()
    summary = summarize(run, len(items) * repetitions)
    cleanup_clean = owners_before == owners_after == 0 and bool(run["cleanup"]["clean"])
    status = (
        "BOUNDED_SCREENING_COMPLETE_NOT_GATE_EVIDENCE" if args.mode == "screening"
        else "BOUNDED_DIAGNOSTIC_COMPLETE_NOT_FORMAL_GATE_EVIDENCE"
    ) if summary["execution_complete"] and cleanup_clean else "BOUNDED_INCONCLUSIVE_RETAINED"
    report = {
        "schema_version": "1.0",
        "report_id": REPORT_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "review_status": "UNREVIEWED",
        "poc_source_sha": args.source_sha,
        "candidate_id": PRIMARY_ID,
        "platform": target,
        "artifact_preflight": artifact_report,
        "build_identity": {
            "build_profile": build_report.get("build_profile", "generic"),
            "report_sha256": sha256_file(args.build_report),
            "binary_sha256": sha256_file(args.binary),
            "cmake_cache": build_report.get("cmake_cache", {}),
            "release_flags": build_report.get("toolchain", {}).get("release_flags", {}),
        },
        "method": {
            "mode": args.mode,
            "threads": args.threads,
            "workers": 1,
            "warmups": warmups,
            "hot_repetitions": repetitions,
            "input": "contiguous_window_from_first_labelled_speech_start_to_last_labelled_speech_end",
            "internal_pauses": "preserved_not_concatenated",
            "absolute_latency_gate": "DEFERRED_OBSERVATION_ONLY",
            "rtf_p95_gate_max": 2.0,
        },
        "cpu_environment": cpu_environment(),
        "input_identity": {
            "vad_label_index_sha256": LABEL_INDEX_SHA256,
            "bounded_fixture_manifest_sha256": bounded_manifest["manifest_sha256"],
            "source_fixture_set_sha256": bounded_manifest["source_fixture_set_sha256"],
            "fixture_count": bounded_manifest["fixture_count"],
            "total_audio_duration_seconds": round(sum(float(item["audio_duration_seconds"]) for item in items), 6),
            "total_labelled_speech_duration_seconds": round(
                sum(float(item["labelled_speech_duration_seconds"]) for item in items), 6
            ),
        },
        "raw_run": run,
        "summary": summary,
        "thermal": {"before": thermal_before, "after": thermal_observation()},
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_QUALIFICATION",
        "security": {
            "raw_transcript_emitted": False,
            "pcm_emitted_to_report": False,
            "audio_device_opened": False,
            "speaker_playback": False,
        },
        "execution_status": status,
        "cleanup": {
            "child_processes": run["cleanup"]["child_processes"],
            "threads": 0,
            "iterators": 0,
            "streams": 0,
            "device_owners": owners_after,
            "clean": cleanup_clean,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"bounded Q8 report: {args.output} ({status})")
    return 0 if summary["execution_complete"] and cleanup_clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
