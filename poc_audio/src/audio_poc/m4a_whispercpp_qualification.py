"""Run ACK-002 whisper.cpp ASR qualification with one persistent native worker.

The runner never opens an audio device or emits transcript text into evidence.
It preserves the historical SenseVoice qualification and applies only to the
Q8 primary or a Q5 row unlocked by a separately reviewed Q8 result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import select
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_qualification import (
    COLD_REPETITIONS,
    FIXTURE_MANIFEST_SHA256,
    HOT_REPETITIONS,
    PLAN_SHA256,
    WARMUPS,
    numeric_summary,
    thermal_observation,
    verify_fixtures,
)
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_preflight import (
    FALLBACK_ID,
    PRIMARY_ID,
    GIT_SHA_RE,
    create_preflight_report,
    repo_root,
    resolve_controlled_path,
    sha256_file,
)


REPORT_ID = "M4A-G1B-ASR-RECOVERY-QUALIFICATION"
INFERENCE_TIMEOUT_SECONDS = 15.0
READY_TIMEOUT_SECONDS = 300.0


class WorkerProtocolError(RuntimeError):
    pass


class WorkerTimeout(RuntimeError):
    pass


class NativeWhisperWorker:
    """Bounded line-protocol owner for one loaded whisper.cpp process."""

    def __init__(self, command: list[str], stderr_path: Path,
                 ready_timeout: float = READY_TIMEOUT_SECONDS) -> None:
        self.command = command
        self.stderr_path = stderr_path
        self.ready_timeout = ready_timeout
        self.process: subprocess.Popen[bytes] | None = None
        self._stderr = None
        self._buffer = b""
        self.load_ms: float | None = None
        self.pid: int | None = None
        self.force_abort_used = False

    def start(self) -> None:
        if self.process is not None:
            raise RuntimeError("worker is already started")
        self.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        self._stderr = self.stderr_path.open("xb")
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            start_new_session=True,
            bufsize=0,
        )
        try:
            fields = self._read_line(self.ready_timeout).split("\t")
            if len(fields) != 4 or fields[:2] != ["READY", "1.9.2"]:
                raise WorkerProtocolError("worker READY identity is invalid")
            self.load_ms = round(int(fields[2]) / 1000.0, 3)
            self.pid = int(fields[3])
            if self.pid != self.process.pid:
                raise WorkerProtocolError("worker READY PID does not match child PID")
        except Exception:
            self.terminate()
            raise

    def _read_line(self, timeout_seconds: float) -> str:
        if self.process is None or self.process.stdout is None:
            raise WorkerProtocolError("worker is not running")
        deadline = time.monotonic() + timeout_seconds
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkerTimeout("worker response timed out")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                raise WorkerTimeout("worker response timed out")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                raise WorkerProtocolError(
                    f"worker exited before a complete response: {self.process.poll()}"
                )
            self._buffer += chunk
            if len(self._buffer) > 1024 * 1024:
                raise WorkerProtocolError("worker response exceeds protocol limit")
        line, self._buffer = self._buffer.split(b"\n", 1)
        try:
            return line.decode("ascii")
        except UnicodeDecodeError as error:
            raise WorkerProtocolError("worker protocol is not ASCII") from error

    def transcribe(self, wav_path: Path, timeout_seconds: float = INFERENCE_TIMEOUT_SECONDS) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None:
            raise WorkerProtocolError("worker is not running")
        resolved = str(wav_path.resolve())
        if any(character in resolved for character in ("\n", "\r", "\t")):
            raise ValueError("fixture path is not protocol-safe")
        started = time.monotonic()
        self.process.stdin.write(f"TRANSCRIBE\t{resolved}\n".encode("utf-8"))
        self.process.stdin.flush()
        try:
            fields = self._read_line(timeout_seconds).split("\t")
        except WorkerTimeout:
            self.terminate()
            raise
        latency_ms = round((time.monotonic() - started) * 1000.0, 3)
        if len(fields) == 2 and fields[0] == "ERROR":
            raise WorkerProtocolError(f"native worker rejected fixture: {fields[1]}")
        if len(fields) != 5 or fields[0] != "RESULT":
            raise WorkerProtocolError("native worker RESULT is invalid")
        try:
            hypothesis = bytes.fromhex(fields[1]).decode("utf-8")
            native_ms = round(int(fields[2]) / 1000.0, 3)
            cpu_ms = round(int(fields[3]) / 1000.0, 3)
            peak_rss_mib = round(int(fields[4]) / 1024.0, 3)
        except (ValueError, UnicodeDecodeError) as error:
            raise WorkerProtocolError("native worker RESULT fields are invalid") from error
        return {
            "hypothesis": hypothesis,
            "latency_ms": latency_ms,
            "native_inference_ms": native_ms,
            "cpu_ms": cpu_ms,
            "peak_rss_mib": peak_rss_mib,
        }

    def stop(self) -> dict[str, Any]:
        if self.process is None:
            return self.cleanup_report()
        if self.process.poll() is None and self.process.stdin is not None:
            try:
                self.process.stdin.write(b"QUIT\n")
                self.process.stdin.flush()
                if self._read_line(5.0) != "BYE":
                    raise WorkerProtocolError("worker did not acknowledge QUIT")
                self.process.wait(timeout=5.0)
            except (BrokenPipeError, subprocess.TimeoutExpired, WorkerProtocolError, WorkerTimeout):
                self.terminate()
        self._close_streams()
        return self.cleanup_report()

    def terminate(self) -> None:
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.force_abort_used = True
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=2.0)
            except ProcessLookupError:
                pass
        self._close_streams()

    def _close_streams(self) -> None:
        if self.process is not None:
            if self.process.stdin is not None and not self.process.stdin.closed:
                self.process.stdin.close()
            if self.process.stdout is not None and not self.process.stdout.closed:
                self.process.stdout.close()
        if self._stderr is not None and not self._stderr.closed:
            self._stderr.close()

    def cleanup_report(self) -> dict[str, Any]:
        alive = self.process is not None and self.process.poll() is None
        return {
            "child_processes": int(alive),
            "threads": 0,
            "iterators": 0,
            "streams": 0,
            "device_owners": 0,
            "force_abort_used": self.force_abort_used,
            "clean": not alive,
        }


def _score(item: dict[str, Any], hypothesis: str, metrics: dict[str, Any]) -> dict[str, Any]:
    reference = normalize_asr(str(item["reference_text"]))
    normalized = normalize_asr(hypothesis)
    duration = float(item["audio_duration_seconds"])
    latency_ms = float(metrics["latency_ms"])
    return {
        "fixture_id": item["fixture_id"],
        "category": item["category"],
        "latency_ms": latency_ms,
        "native_inference_ms": metrics["native_inference_ms"],
        "cpu_ms": metrics["cpu_ms"],
        "peak_rss_mib": metrics["peak_rss_mib"],
        "audio_duration_seconds": duration,
        "rtf": round(latency_ms / 1000.0 / duration, 6),
        "reference_length": len(reference),
        "hypothesis_length": len(normalized),
        "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode("utf-8")).hexdigest(),
        "raw_transcript_emitted": False,
    }


def run_loaded_suite(command: list[str], stderr_path: Path, items: list[dict[str, Any]],
                     fixture_dir: Path, cycles: int, warmups: int) -> dict[str, Any]:
    worker = NativeWhisperWorker(command, stderr_path)
    results: list[dict[str, Any]] = []
    rss_after_cycle: list[float] = []
    started = time.monotonic()
    try:
        worker.start()
        for warmup in range(warmups):
            worker.transcribe(fixture_dir / f"{items[warmup % len(items)]['fixture_id']}.wav")
        for cycle in range(1, cycles + 1):
            for item in items:
                metrics = worker.transcribe(fixture_dir / f"{item['fixture_id']}.wav")
                result = _score(item, metrics.pop("hypothesis"), metrics)
                result["cycle"] = cycle
                results.append(result)
            rss_after_cycle.append(max(float(item["peak_rss_mib"]) for item in results[-len(items):]))
        terminal_status = "SUCCESS"
        error_code = None
    except WorkerTimeout:
        terminal_status = "TIMEOUT"
        error_code = "INFERENCE_TIMEOUT"
    except (WorkerProtocolError, OSError, ValueError) as error:
        terminal_status = "ERROR"
        error_code = type(error).__name__
    cleanup = worker.stop()
    cleanup["clean"] = cleanup["clean"] and cleanup["child_processes"] == 0
    return {
        "terminal_status": terminal_status,
        "error_code": error_code,
        "load_ms": worker.load_ms,
        "warmups": warmups,
        "cycles": cycles,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "peak_rss_mib": max((float(item["peak_rss_mib"]) for item in results), default=None),
        "rss_after_cycle_mib": rss_after_cycle,
        "results": results,
        "cleanup": cleanup,
        "raw_transcript_emitted": False,
        "audio_device_opened": False,
    }


def summarize(
    run: dict[str, Any],
    expected_cold_repetitions: int = COLD_REPETITIONS,
    expected_hot_repetitions: int = HOT_REPETITIONS,
    gate_eligible: bool = True,
) -> dict[str, Any]:
    cold = [item for worker in run["cold"] if worker["terminal_status"] == "SUCCESS"
            for item in worker["results"]]
    hot = run["hot"]["results"] if run["hot"]["terminal_status"] == "SUCCESS" else []
    categories: dict[str, dict[str, Any]] = {}
    for category in sorted({str(item["category"]) for item in hot}):
        selected = [item for item in hot if item["category"] == category]
        reference_length = sum(int(item["reference_length"]) for item in selected)
        edits = sum(int(item["edit_distance"]) for item in selected)
        categories[category] = {
            "result_count": len(selected),
            "reference_codepoints": reference_length,
            "edit_distance": edits,
            "cer_percent": round(100.0 * edits / reference_length, 6) if reference_length else None,
            "sentence_correctness_percent": round(
                100.0 * sum(bool(item["sentence_correct"]) for item in selected) / len(selected), 6
            ) if selected else None,
        }
    execution_complete = (
        len(cold) == expected_cold_repetitions * 50
        and len(hot) == expected_hot_repetitions * 50
    )
    core_cer = categories.get("taiwan_mandarin", {}).get("cer_percent")
    overall_sentence = round(
        100.0 * sum(bool(item["sentence_correct"]) for item in hot) / len(hot), 6
    ) if hot else None
    hot_latency = numeric_summary([float(item["latency_ms"]) for item in hot])
    hot_rtf = numeric_summary([float(item["rtf"]) for item in hot])
    peak_rss = max(
        (float(worker["peak_rss_mib"]) for worker in [*run["cold"], run["hot"]]
         if worker["peak_rss_mib"] is not None),
        default=None,
    )
    quality_thresholds_observed_met = bool(
        execution_complete and core_cer is not None and core_cer <= 20.0
        and overall_sentence is not None and overall_sentence >= 70.0
    )
    latency_threshold_observed_met = bool(
        execution_complete and hot_latency["p95"] is not None
        and float(hot_latency["p95"]) <= 1500.0
    )
    rtf_threshold_observed_met = bool(
        execution_complete and hot_rtf["p95"] is not None
        and float(hot_rtf["p95"]) <= 2.0
    )
    fallback_trigger = bool(
        gate_eligible and quality_thresholds_observed_met
        and ((hot_latency["p95"] is not None and float(hot_latency["p95"]) > 1500.0)
             or (peak_rss is not None and peak_rss > 1250.0))
    )
    hashes_by_fixture: dict[str, set[str]] = {}
    for item in hot:
        hashes_by_fixture.setdefault(str(item["fixture_id"]), set()).add(
            str(item["hypothesis_sha256"])
        )
    determinism_threshold_observed_met = bool(
        execution_complete and len(hashes_by_fixture) == 50
        and all(len(hashes) == 1 for hashes in hashes_by_fixture.values())
    )
    return {
        "execution_complete": execution_complete,
        "gate_eligible": gate_eligible,
        "quality": {
            "taiwan_mandarin_core_cer_percent": core_cer,
            "overall_sentence_correctness_percent": overall_sentence,
            "thresholds_observed_met": quality_thresholds_observed_met,
            "gate_pass": gate_eligible and quality_thresholds_observed_met,
        },
        "performance": {
            "hot_final_transcript_ms": hot_latency,
            "hot_rtf": hot_rtf,
            "peak_rss_mib": peak_rss,
            "latency_threshold_observed_met": latency_threshold_observed_met,
            "rtf_threshold_observed_met": rtf_threshold_observed_met,
            "latency_gate_pass": gate_eligible and latency_threshold_observed_met,
            "rtf_gate_pass": gate_eligible and rtf_threshold_observed_met,
        },
        "categories": categories,
        "determinism": {
            "fixture_count": len(hashes_by_fixture),
            "maximum_unique_hypotheses_per_fixture": max(
                (len(hashes) for hashes in hashes_by_fixture.values()), default=0
            ),
            "threshold_observed_met": determinism_threshold_observed_met,
            "gate_pass": gate_eligible and determinism_threshold_observed_met,
        },
        "q5_fallback_triggered": fallback_trigger,
    }


def validate_build_report(report: dict[str, Any], candidate_id: str, source_sha: str,
                          binary: Path) -> None:
    if (
        report.get("report_id") != "M4A-G1B-ASR-RECOVERY-OFFLINE-BUILD"
        or report.get("execution_status") != "BUILD_PASS_MODEL_NOT_LOADED_INFERENCE_NOT_RUN"
        or report.get("candidate_id") != candidate_id
        or report.get("poc_source_sha") != source_sha
    ):
        raise ValueError("offline build report does not bind this candidate SHA and row")
    identity = report.get("binary", {})
    if not binary.is_file() or identity.get("size_bytes") != binary.stat().st_size \
            or identity.get("sha256") != sha256_file(binary):
        raise ValueError("persistent worker binary does not match the build report")


def validate_qualification_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != "1.0" or report.get("report_id") != REPORT_ID:
        raise ValueError("qualification report identity is invalid")
    if report.get("review_status") != "UNREVIEWED":
        raise ValueError("runner output must remain unreviewed")
    if report.get("candidate_id") not in {PRIMARY_ID, FALLBACK_ID}:
        raise ValueError("qualification candidate is unauthorized")
    formal_method = {
        "threads": 4,
        "workers": 1,
        "warmups": WARMUPS,
        "cold_repetitions": COLD_REPETITIONS,
        "hot_repetitions": HOT_REPETITIONS,
        "hot_definition": "one_loaded_model_runs_fifty_fixtures_twenty_times",
        "percentile": "nearest_rank",
        "inference_timeout_seconds": INFERENCE_TIMEOUT_SECONDS,
    }
    diagnostic_method = {
        "mode": "PARTIAL_DIAGNOSTIC_NOT_GATE_EVIDENCE",
        "threads": 4,
        "workers": 1,
        "warmups": WARMUPS,
        "cold_repetitions": 0,
        "hot_repetitions": 2,
        "hot_definition": "one_loaded_model_runs_fifty_fixtures_two_times",
        "percentile": "nearest_rank",
        "inference_timeout_seconds": INFERENCE_TIMEOUT_SECONDS,
    }
    method = report.get("method")
    if method not in (formal_method, diagnostic_method):
        raise ValueError("qualification method is not frozen")
    security = report.get("security", {})
    if security != {
        "raw_transcript_emitted": False,
        "pcm_emitted": False,
        "audio_device_opened": False,
        "speaker_playback": False,
    }:
        raise ValueError("qualification security boundary is invalid")
    summary = report.get("summary", {})
    diagnostic = method == diagnostic_method
    if diagnostic and (
        summary.get("gate_eligible") is not False
        or summary.get("quality", {}).get("gate_pass") is not False
        or summary.get("performance", {}).get("latency_gate_pass") is not False
        or summary.get("performance", {}).get("rtf_gate_pass") is not False
        or summary.get("determinism", {}).get("gate_pass") is not False
        or summary.get("q5_fallback_triggered") is not False
        or report.get("execution_status") not in {
            "PARTIAL_DIAGNOSTIC_NOT_GATE_EVIDENCE",
            "PARTIAL_DIAGNOSTIC_INCONCLUSIVE_RETAINED",
        }
    ):
        raise ValueError("partial diagnostic must remain ineligible for gate or Q5 claims")
    quality_pass = bool(summary.get("quality", {}).get("gate_pass"))
    status = report.get("execution_status")
    if not diagnostic and report["candidate_id"] == PRIMARY_ID and not quality_pass \
            and summary.get("execution_complete") \
            and status != "Q8_QUALITY_FAIL_STOP_NO_Q5":
        raise ValueError("Q8 quality failure must stop without Q5")
    cleanup = report.get("cleanup", {})
    if cleanup.get("clean") != (
        cleanup.get("child_processes") == 0
        and cleanup.get("threads") == 0
        and cleanup.get("iterators") == 0
        and cleanup.get("streams") == 0
        and cleanup.get("device_owners") == 0
    ):
        raise ValueError("qualification cleanup proof is inconsistent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", choices=(PRIMARY_ID, FALLBACK_ID), default=PRIMARY_ID)
    parser.add_argument("--q8-result", type=Path)
    parser.add_argument("--diagnostic-hot-repetitions", type=int, choices=(2,))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full lowercase Git SHA")
    if args.output.exists() or args.work_dir.exists():
        raise ValueError("output and work directory must be new paths")
    root = repo_root().resolve()
    if args.work_dir.resolve().is_relative_to(root) or args.output.resolve().is_relative_to(root):
        raise ValueError("qualification work and raw output must remain outside the POC repository")
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    manifest = json.loads(
        (repo_root() / "poc_audio/manifests/m4a_asr_recovery_ack002.json").read_text(encoding="utf-8")
    )
    q8_result = json.loads(args.q8_result.read_text(encoding="utf-8")) \
        if args.q8_result is not None else None
    artifact_report = create_preflight_report(
        manifest, args.candidate, args.artifact_dir, args.source_sha, q8_result
    )
    build_report = json.loads(args.build_report.read_text(encoding="utf-8"))
    validate_build_report(build_report, args.candidate, args.source_sha, args.binary)

    plan_path = repo_root() / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    if sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("frozen ASR recording plan checksum mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    fixture_identities = verify_fixtures(args.fixture_dir, plan)
    records = json.loads((args.fixture_dir / "delivered_fixture_manifest.json").read_text(encoding="utf-8"))["records"]
    items = []
    for item in plan["utterances"]:
        copied = dict(item)
        copied["audio_duration_seconds"] = (
            float(records[item["fixture_id"]]["metadata"]["frames"]) / 16000.0
        )
        items.append(copied)

    candidate = next(item for item in manifest["candidates"] if item["candidate_id"] == args.candidate)
    model = resolve_controlled_path(
        manifest, candidate["controlled_locator"], candidate["filename"], args.artifact_dir
    )
    args.work_dir.mkdir(parents=True)
    command = [str(args.binary.resolve()), "--model", str(model)]
    diagnostic = args.diagnostic_hot_repetitions is not None
    cold_repetitions = 0 if diagnostic else COLD_REPETITIONS
    hot_repetitions = args.diagnostic_hot_repetitions or HOT_REPETITIONS
    owners_before = audio_device_owner_count()
    thermal_before = thermal_observation()
    cold = []
    for repetition in range(1, cold_repetitions + 1):
        result = run_loaded_suite(
            command, args.work_dir / f"cold-{repetition}.stderr.log", items,
            args.fixture_dir, 1, 0,
        )
        result["repetition"] = repetition
        cold.append(result)
    hot = run_loaded_suite(
        command, args.work_dir / "hot.stderr.log", items, args.fixture_dir,
        hot_repetitions, WARMUPS,
    )
    assert_network_isolated()
    owners_after = audio_device_owner_count()
    summary = summarize(
        {"cold": cold, "hot": hot},
        expected_cold_repetitions=cold_repetitions,
        expected_hot_repetitions=hot_repetitions,
        gate_eligible=not diagnostic,
    )
    cleanup_clean = owners_before == owners_after == 0 and all(
        worker["cleanup"]["clean"] for worker in [*cold, hot]
    )
    if diagnostic:
        status = (
            "PARTIAL_DIAGNOSTIC_NOT_GATE_EVIDENCE"
            if summary["execution_complete"] and cleanup_clean
            else "PARTIAL_DIAGNOSTIC_INCONCLUSIVE_RETAINED"
        )
    elif not summary["execution_complete"] or not cleanup_clean:
        status = "INCONCLUSIVE_RETAINED"
    elif not summary["quality"]["gate_pass"]:
        status = "Q8_QUALITY_FAIL_STOP_NO_Q5" if args.candidate == PRIMARY_ID else "Q5_QUALITY_FAIL_RETAINED"
    elif not summary["determinism"]["gate_pass"]:
        status = "DETERMINISM_FAIL_RETAINED"
    elif not summary["performance"]["latency_gate_pass"] or not summary["performance"]["rtf_gate_pass"]:
        status = "QUALITY_PASS_PERFORMANCE_FAIL_RETAINED"
    else:
        status = "QUALITY_PERFORMANCE_PASS_PENDING_REVIEW_AND_LIFECYCLE"
    report = {
        "schema_version": "1.0",
        "report_id": REPORT_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "review_status": "UNREVIEWED",
        "poc_source_sha": args.source_sha,
        "candidate_id": args.candidate,
        "platform": target,
        "artifact_preflight": artifact_report,
        "build_identity": {
            "report_sha256": sha256_file(args.build_report),
            "binary_sha256": sha256_file(args.binary),
        },
        "method": ({
            "threads": 4,
            "workers": 1,
            "warmups": WARMUPS,
            "cold_repetitions": cold_repetitions,
            "hot_repetitions": hot_repetitions,
            "hot_definition": "one_loaded_model_runs_fifty_fixtures_twenty_times",
            "percentile": "nearest_rank",
            "inference_timeout_seconds": INFERENCE_TIMEOUT_SECONDS,
        } if not diagnostic else {
            "mode": "PARTIAL_DIAGNOSTIC_NOT_GATE_EVIDENCE",
            "threads": 4,
            "workers": 1,
            "warmups": WARMUPS,
            "cold_repetitions": 0,
            "hot_repetitions": 2,
            "hot_definition": "one_loaded_model_runs_fifty_fixtures_two_times",
            "percentile": "nearest_rank",
            "inference_timeout_seconds": INFERENCE_TIMEOUT_SECONDS,
        }),
        "input_identity": {
            "delivered_fixture_manifest_sha256": FIXTURE_MANIFEST_SHA256,
            "recording_plan_sha256": PLAN_SHA256,
            "fixture_count": len(fixture_identities),
            "fixture_set_sha256": hashlib.sha256(
                json.dumps(fixture_identities, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        },
        "raw_runs": {"cold": cold, "hot": hot},
        "summary": summary,
        "quality": {
            "taiwan_mandarin_core_cer_percent": summary["quality"]["taiwan_mandarin_core_cer_percent"],
            "overall_sentence_correctness_percent": summary["quality"]["overall_sentence_correctness_percent"],
        },
        "performance": {
            "hot_final_transcript_p95_seconds": (
                round(float(summary["performance"]["hot_final_transcript_ms"]["p95"]) / 1000.0, 6)
                if summary["performance"]["hot_final_transcript_ms"]["p95"] is not None else None
            ),
            "hot_rtf_p95": summary["performance"]["hot_rtf"]["p95"],
            "peak_rss_mib": summary["performance"]["peak_rss_mib"],
        },
        "thermal": {"before": thermal_before, "after": thermal_observation()},
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_QUALIFICATION",
        "security": {
            "raw_transcript_emitted": False,
            "pcm_emitted": False,
            "audio_device_opened": False,
            "speaker_playback": False,
        },
        "execution_status": status,
        "cleanup": {
            "child_processes": sum(worker["cleanup"]["child_processes"] for worker in [*cold, hot]),
            "threads": 0,
            "iterators": 0,
            "streams": 0,
            "device_owners": owners_after,
            "clean": cleanup_clean,
        },
    }
    validate_qualification_report(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"whisper.cpp qualification report: {args.output} ({status})")
    return 0 if summary["execution_complete"] and cleanup_clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
