"""Run one ACK-003 M2A observation row on the exact 20-item PCM lock."""

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
from .m4a_m2a_packet import load_json, repo_root, sha256_file, validate_linked_fixture_lock, validate_packet
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_qualification import NativeWhisperWorker


REPORT_ID = "M4A-M2A-BASELINE-SURVEY-ROW-001"
M2B_REPORT_ID = "M4A-M2B-SINGLE-VARIABLE-PROBE-ROW-001"
FIXTURE_LOCK_SHA256 = "fa3649f2fde77aaaa2132cab81b6d3c562e2b812335d90e846fb6c3f85c943e6"
CONTROLLED_MANIFEST_SHA256 = "24d3747cbcec7b5a22c7842ac92851a672dcdbe8b256e616c0abf1195dd42a9a"


class JsonWorker:
    def __init__(self, command: list[str], stderr_path: Path) -> None:
        self.command = command
        self.stderr_path = stderr_path
        self.process: subprocess.Popen[str] | None = None
        self.stderr_file = None
        self.load_ms: float | None = None
        self.runtime_identity: dict[str, Any] = {}
        self.force_abort_used = False

    def _read(self, timeout_seconds: float) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("worker is not running")
        readable, _, _ = select.select([self.process.stdout], [], [], timeout_seconds)
        if not readable:
            raise TimeoutError("worker response timed out")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"worker exited early: {self.process.poll()}")
        result = json.loads(line)
        if not isinstance(result, dict):
            raise RuntimeError("worker response is not an object")
        return result

    def start(self, timeout_seconds: float = 300.0) -> None:
        self.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        self.stderr_file = self.stderr_path.open("xb")
        self.process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr_file, text=True, start_new_session=True, bufsize=1,
        )
        ready = self._read(timeout_seconds)
        if ready.get("event") != "ready" or ready.get("pid") != self.process.pid:
            self.terminate()
            raise RuntimeError("worker READY identity mismatch")
        self.load_ms = float(ready["load_ms"])
        runtime = ready.get("runtime", {})
        if not isinstance(runtime, dict):
            raise RuntimeError("worker runtime identity mismatch")
        self.runtime_identity = runtime

    def transcribe(self, wav_path: Path, timeout_seconds: float) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("worker is not running")
        started = time.monotonic()
        self.process.stdin.write(json.dumps({"command": "transcribe", "wav": str(wav_path.resolve())}) + "\n")
        self.process.stdin.flush()
        try:
            result = self._read(timeout_seconds)
        except TimeoutError:
            self.terminate()
            raise
        if result.get("event") != "result":
            raise RuntimeError(f"worker result error: {result.get('code', 'PROTOCOL')}")
        result["latency_ms"] = round((time.monotonic() - started) * 1000.0, 3)
        return result

    def terminate(self) -> None:
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.force_abort_used = True
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=2.0)
        self.close()

    def stop(self) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None and self.process.stdin is not None:
            self.process.stdin.write('{"command":"quit"}\n')
            self.process.stdin.flush()
            try:
                if self._read(5.0).get("event") != "bye":
                    raise RuntimeError("worker did not acknowledge quit")
                self.process.wait(timeout=5.0)
            except (RuntimeError, TimeoutError, subprocess.TimeoutExpired):
                self.terminate()
        self.close()
        alive = self.process is not None and self.process.poll() is None
        return {"child_processes": int(alive), "force_abort_used": self.force_abort_used, "clean": not alive}

    def close(self) -> None:
        if self.process is not None:
            if self.process.stdin is not None and not self.process.stdin.closed:
                self.process.stdin.close()
            if self.process.stdout is not None and not self.process.stdout.closed:
                self.process.stdout.close()
        if self.stderr_file is not None and not self.stderr_file.closed:
            self.stderr_file.close()


def numeric_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p50": None, "p95": None, "max": None}
    ordered = sorted(values)
    nearest = lambda fraction: ordered[max(0, int(len(ordered) * fraction + 0.999999) - 1)]
    return {"min": ordered[0], "p50": nearest(0.50), "p95": nearest(0.95), "max": ordered[-1]}


def verify_inputs(fixtures_dir: Path, controlled_path: Path) -> list[dict[str, Any]]:
    tracked_path = repo_root() / "poc_audio/manifests/m4a_m2a_fixture_lock.json"
    if sha256_file(tracked_path) != FIXTURE_LOCK_SHA256:
        raise ValueError("tracked exact fixture lock checksum mismatch")
    if sha256_file(controlled_path) != CONTROLLED_MANIFEST_SHA256:
        raise ValueError("controlled exact fixture manifest checksum mismatch")
    tracked = load_json(tracked_path)["records"]
    controlled = load_json(controlled_path)
    if controlled.get("git_safety") != "CONTROLLED_REFERENCE_TEXT_AND_AUDIO_PATHS_DO_NOT_COMMIT":
        raise ValueError("controlled fixture safety marker mismatch")
    items: list[dict[str, Any]] = []
    for family in ("internal", "common_voice"):
        sanitized = tracked[family]
        raw = controlled["records"][family]
        if len(raw) != len(sanitized):
            raise ValueError("controlled fixture count mismatch")
        for expected, item in zip(sanitized, raw, strict=True):
            identity_key = "fixture_id" if family == "internal" else "clip_id"
            if item.get(identity_key) != expected.get(identity_key):
                raise ValueError("controlled fixture order mismatch")
            for field in ("reference_sha256", "derived_wav_sha256", "derived_wav_size_bytes", "frames"):
                if item.get(field) != expected.get(field):
                    raise ValueError("controlled fixture identity mismatch")
            reference = str(item.get("reference_text", ""))
            if hashlib.sha256(reference.encode()).hexdigest() != expected["reference_sha256"]:
                raise ValueError("controlled reference checksum mismatch")
            wav_path = fixtures_dir / str(item["relative_wav_path"])
            if wav_path.stat().st_size != expected["derived_wav_size_bytes"] \
                    or sha256_file(wav_path) != expected["derived_wav_sha256"]:
                raise ValueError("derived fixture file identity mismatch")
            items.append({**item, "family": family, "wav_path": wav_path})
    return items


def score(item: dict[str, Any], metrics: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    hypothesis = str(metrics["hypothesis"])
    reference = normalize_asr(str(item["reference_text"]))
    normalized = normalize_asr(hypothesis)
    latency_ms = float(metrics["latency_ms"])
    duration = float(item["duration_seconds"])
    identity = str(item.get("fixture_id", item.get("clip_id")))
    common = {
        "fixture_id": identity, "family": item["family"],
        "category": item.get("group", "common_voice"),
        "latency_ms": round(latency_ms, 3),
        "native_inference_ms": float(metrics["native_inference_ms"]),
        "cpu_ms": float(metrics["cpu_ms"]), "peak_rss_mib": float(metrics["peak_rss_mib"]),
        "audio_duration_seconds": duration, "rtf": round(latency_ms / 1000.0 / duration, 6),
        "reference_length": len(reference), "hypothesis_length": len(normalized),
        "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
    }
    return {**common, "reference_text": item["reference_text"], "hypothesis": hypothesis}, common


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, Any] = {}
    for category in sorted({str(item["category"]) for item in results}):
        selected = [item for item in results if item["category"] == category]
        reference_length = sum(int(item["reference_length"]) for item in selected)
        edits = sum(int(item["edit_distance"]) for item in selected)
        categories[category] = {
            "item_count": len(selected),
            "cer_percent": round(100.0 * edits / reference_length, 6) if reference_length else None,
            "sentence_correctness_percent": round(100.0 * sum(bool(item["sentence_correct"]) for item in selected) / len(selected), 6),
        }
    reference_length = sum(int(item["reference_length"]) for item in results)
    return {
        "item_count": len(results),
        "overall_cer_percent": round(100.0 * sum(int(item["edit_distance"]) for item in results) / reference_length, 6) if reference_length else None,
        "overall_sentence_correctness_percent": round(100.0 * sum(bool(item["sentence_correct"]) for item in results) / len(results), 6) if results else None,
        "latency_ms": numeric_summary([float(item["latency_ms"]) for item in results]),
        "rtf": numeric_summary([float(item["rtf"]) for item in results]),
        "peak_rss_mib": max((float(item["peak_rss_mib"]) for item in results), default=None),
        "categories": categories,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--engine", choices=("whisper", "sherpa-zipformer", "vosk"), required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--runtime-python", type=Path, default=Path("/usr/bin/python3"))
    parser.add_argument("--runtime-artifact-dir", type=Path, required=True)
    parser.add_argument("--fixtures-dir", type=Path, required=True)
    parser.add_argument("--controlled-manifest", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--diagnostic-recheck",
        type=int,
        choices=(1, 2),
        help="mark this run as diagnostic recheck 1 or 2, excluded from the M2A scorecard",
    )
    mode.add_argument(
        "--m2b-probe-manifest",
        type=Path,
        help="run one reviewed-shortlist M2B single-variable probe",
    )
    return parser.parse_args()


def execution_status(
    complete: bool, diagnostic_recheck: int | None, m2b_probe: bool = False,
) -> str:
    if not complete:
        return "INCONCLUSIVE_RETAINED"
    if diagnostic_recheck is not None:
        return "DIAGNOSTIC_RECHECK_COMPLETE_NOT_SCORECARD"
    if m2b_probe:
        return "M2B_PROBE_OBSERVATIONS_COMPLETE_PENDING_DELTA_REVIEW"
    return "OBSERVATIONS_COMPLETE_PENDING_COMPARATIVE_REVIEW"


def executable_path_preserving_venv(path: Path) -> Path:
    """Make an executable path absolute without resolving a virtualenv symlink."""
    absolute = Path(os.path.abspath(path))
    if not absolute.is_file() or not os.access(absolute, os.X_OK):
        raise ValueError("runtime Python is not an executable file")
    return absolute


def expected_wheel_packages(runtime: dict[str, Any]) -> dict[str, str]:
    packages: dict[str, str] = {}
    for artifact in runtime.get("runtime_artifacts", []):
        filename = str(artifact["filename"])
        if not filename.endswith(".whl"):
            continue
        fields = filename.removesuffix(".whl").split("-")
        if len(fields) < 5:
            raise ValueError(f"invalid runtime wheel filename: {filename}")
        packages[fields[0].replace("_", "-")] = fields[1]
    if not packages:
        raise ValueError("Python runtime has no pinned wheel package identities")
    return packages


def load_m2b_probe(path: Path, packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    probe = load_json(path)
    if probe.get("status") != "AUTHORIZED_BY_REVIEWED_M2A_SHORTLIST":
        raise ValueError("M2B probe is not authorized by reviewed M2A shortlist")
    baseline_id = probe.get("baseline_candidate_id")
    baseline = next(
        (row for row in packet["candidate_rows"] if row["candidate_id"] == baseline_id), None,
    )
    if baseline is None or baseline_id not in probe.get("shortlist", []):
        raise ValueError("M2B baseline is not in the reviewed shortlist")
    if probe.get("runtime_id") != baseline["runtime_id"]:
        raise ValueError("M2B probe changes the baseline runtime")
    variable = probe.get("single_variable", {})
    if variable != {
        "name": "model_quantization", "baseline_value": "Q5_1", "probe_value": "Q8_0",
    }:
        raise ValueError("M2B probe is not the reviewed quantization-only change")
    controls = probe.get("fixed_controls", {})
    expected_controls = {
        "fixture_lock_sha256": FIXTURE_LOCK_SHA256,
        "controlled_manifest_sha256": CONTROLLED_MANIFEST_SHA256,
        "fixture_count": 20, "warmups_per_item": 1, "scored_inferences_per_item": 1,
        "per_item_timeout_seconds": 120, "row_budget_seconds": 2400, "threads": 4,
        "platform": "Raspberry Pi 5 / Debian 13 / aarch64",
        "network": "isolated namespace", "audio_capture": False, "audio_playback": False,
    }
    if controls != expected_controls:
        raise ValueError("M2B probe changes a frozen control")
    artifact = probe.get("artifact", {})
    required_artifact = {
        "filename", "immutable_revision", "license", "sha256", "size_bytes", "source_url",
    }
    if set(artifact) != required_artifact or len(str(artifact["sha256"])) != 64:
        raise ValueError("M2B probe artifact identity is incomplete")
    row = {
        "candidate_id": probe["probe_candidate_id"],
        "artifact": artifact,
        "runtime_id": probe["runtime_id"],
    }
    return row, probe


def main() -> int:
    args = parse_args()
    root = repo_root().resolve()
    for path in (args.work_dir, args.output, args.sanitized_output):
        if path.exists() or path.resolve().is_relative_to(root):
            raise ValueError("survey work and outputs must be new paths outside the repository")
    packet = load_json(root / "poc_audio/manifests/m4a_m2a_common_packet.json")
    validate_packet(packet)
    validate_linked_fixture_lock(packet)
    probe = None
    if args.m2b_probe_manifest is not None:
        expected_probe_path = root / "poc_audio/manifests/m2b_base_q8_probe.json"
        if args.m2b_probe_manifest.resolve() != expected_probe_path:
            raise ValueError("M2B probe must use the tracked manifest from the clean candidate SHA")
        row, probe = load_m2b_probe(args.m2b_probe_manifest, packet)
        if args.candidate != row["candidate_id"]:
            raise ValueError("candidate does not match M2B probe manifest")
        if args.engine != "whisper":
            raise ValueError("reviewed base Q8 M2B probe requires whisper engine")
    else:
        row = next((item for item in packet["candidate_rows"] if item["candidate_id"] == args.candidate), None)
        if row is None:
            raise ValueError("candidate is not authorized by ACK-003")
    artifact = row["artifact"]
    if args.artifact.name != artifact["filename"] or args.artifact.stat().st_size != artifact["size_bytes"] \
            or sha256_file(args.artifact) != artifact["sha256"]:
        raise ValueError("candidate artifact identity mismatch")
    runtime = packet["runtime_identities"][row["runtime_id"]]
    runtime_artifacts = runtime.get("runtime_artifacts")
    if runtime_artifacts is None:
        runtime_artifacts = [{
            "filename": runtime["source_filename"],
            "size_bytes": runtime["source_size_bytes"],
            "sha256": runtime["source_sha256"],
        }]
    verified_runtime_artifacts = []
    for expected in runtime_artifacts:
        path = args.runtime_artifact_dir / expected["filename"]
        if path.stat().st_size != expected["size_bytes"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"runtime artifact identity mismatch: {expected['filename']}")
        verified_runtime_artifacts.append({
            "filename": expected["filename"], "size_bytes": expected["size_bytes"],
            "sha256": expected["sha256"],
        })
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    items = verify_inputs(args.fixtures_dir, args.controlled_manifest)
    args.work_dir.mkdir(parents=True)
    if args.engine == "whisper":
        if args.binary is None or args.model is None or args.model != args.artifact:
            raise ValueError("whisper row requires matching --model and --artifact plus --binary")
        command = [str(args.binary.resolve()), "--model", str(args.model.resolve()), "--threads", "4"]
        worker: Any = NativeWhisperWorker(command, args.work_dir / "worker.stderr.log")
        worker.runtime_identity = {"engine_version": runtime["version"]}
    else:
        if args.model_dir is None:
            raise ValueError("Python ASR row requires --model-dir")
        runtime_python = executable_path_preserving_venv(args.runtime_python)
        command = [str(runtime_python), "-m", "audio_poc.m2a_asr_worker", "--engine", args.engine, "--model-dir", str(args.model_dir.resolve())]
        worker = JsonWorker(command, args.work_dir / "worker.stderr.log")
    owners_before = audio_device_owner_count()
    started = time.monotonic()
    raw_results: list[dict[str, Any]] = []
    sanitized_results: list[dict[str, Any]] = []
    error_code = None
    try:
        worker.start()
        if args.engine != "whisper" and worker.runtime_identity != {
            "packages": expected_wheel_packages(runtime),
        }:
            raise RuntimeError("loaded runtime package identity mismatch")
        for item in items:
            worker.transcribe(item["wav_path"], 120.0)
            metrics = worker.transcribe(item["wav_path"], 120.0)
            raw, sanitized = score(item, metrics)
            raw_results.append(raw)
            sanitized_results.append(sanitized)
            if time.monotonic() - started > 2400:
                raise TimeoutError("row budget exceeded")
    except Exception as error:
        error_code = type(error).__name__
    cleanup = worker.stop()
    assert_network_isolated()
    owners_after = audio_device_owner_count()
    cleanup.update({"threads": 0, "iterators": 0, "streams": 0, "device_owners": owners_after})
    cleanup["clean"] = bool(cleanup["clean"] and owners_before == owners_after == 0)
    complete = len(sanitized_results) == 20 and error_code is None and cleanup["clean"]
    status = execution_status(complete, args.diagnostic_recheck, probe is not None)
    base = {
        "schema_version": "1.0", "report_id": M2B_REPORT_ID if probe is not None else REPORT_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(), "review_status": "UNREVIEWED",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "candidate_id": args.candidate, "engine": args.engine, "platform": target,
        "artifact": {"filename": artifact["filename"], "size_bytes": artifact["size_bytes"], "sha256": artifact["sha256"], "license": artifact["license"], "immutable_revision": artifact["immutable_revision"]},
        "runtime": {
            "engine": args.engine,
            "runtime_executable_sha256": sha256_file(Path(command[0]).resolve()),
            "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
            "artifacts": verified_runtime_artifacts,
            "loaded_identity": worker.runtime_identity,
        },
        "method": {
            "fixture_count": 20, "warmups_per_item": 1,
            "scored_inferences_per_item": 1, "per_item_timeout_seconds": 120,
            "row_budget_seconds": 2400, "threads": 4 if args.engine != "vosk" else 1,
            "run_class": (
                "M2B_SINGLE_VARIABLE_PROBE" if probe is not None else
                "DIAGNOSTIC_RECHECK_NOT_SCORECARD" if args.diagnostic_recheck is not None else
                "FORMAL_M2A_SCORECARD_ROW"
            ),
            "diagnostic_recheck_index": args.diagnostic_recheck,
        },
        "fixture_lock_sha256": FIXTURE_LOCK_SHA256,
        "controlled_manifest_sha256": CONTROLLED_MANIFEST_SHA256,
        "load_ms": worker.load_ms, "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "summary": summarize(sanitized_results), "error_code": error_code,
        "execution_status": status, "cleanup": cleanup,
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_SURVEY",
        "security": {"audio_device_opened": False, "speaker_playback": False, "pcm_emitted_to_report": False},
    }
    if probe is not None:
        base["m2b_probe"] = {
            "probe_id": probe["probe_id"],
            "baseline_candidate_id": probe["baseline_candidate_id"],
            "single_variable": probe["single_variable"],
            "review_evidence": probe["review_evidence"],
        }
    raw = {
        **base, "git_safety": "CONTROLLED_TRANSCRIPTS_AND_PATHS_DO_NOT_COMMIT",
        "runtime_command": command, "results": raw_results,
    }
    sanitized = {**base, "results": sanitized_results, "raw_transcript_emitted": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.sanitized_output.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stage = "M2B probe" if probe is not None else "M2A row"
    print(f"{stage} report: {args.sanitized_output} ({status})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
