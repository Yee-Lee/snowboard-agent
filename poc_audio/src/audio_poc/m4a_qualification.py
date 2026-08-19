"""Run frozen full-fixture M2 quality/resource qualification without playback."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_authorized_preflight import AUTHORIZED_CANDIDATES, repo_root, verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .validation import GIT_SHA_RE, validate_m4a_qualification


ASR_ID = "asr-sherpa-sensevoice-int8-2025-09-09"
TTS_ID = "tts-sherpa-matcha-zh-en-1.13.5"
FIXTURE_MANIFEST_SHA256 = "1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2"
PLAN_SHA256 = "d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920"
PROMPTS_SHA256 = "1f9699344394e718fa0d30fb24df3219407680268340418e564c70cc13007739"
COLD_REPETITIONS = 3
WARMUPS = 3
HOT_REPETITIONS = 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], quantile: float) -> float | None:
    """Nearest-rank percentile, fixed before the full candidate run."""

    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return round(ordered[index], 6)


def numeric_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "minimum": round(min(values), 6) if values else None,
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "maximum": round(max(values), 6) if values else None,
    }


def verify_fixtures(fixture_dir: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_path = fixture_dir / "delivered_fixture_manifest.json"
    if sha256_file(manifest_path) != FIXTURE_MANIFEST_SHA256:
        raise ValueError("delivered fixture manifest checksum mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("delivered_pcm") != {
        "sample_rate_hz": 16000,
        "channels": 1,
        "sample_format": "S16_LE",
    }:
        raise ValueError("delivered ASR fixture PCM identity mismatch")
    items = list(plan.get("utterances", []))
    if len(items) != 50:
        raise ValueError("frozen ASR plan must contain exactly 50 utterances")
    identities = []
    for item in items:
        fixture_id = str(item["fixture_id"])
        record = manifest["records"].get(fixture_id)
        if not isinstance(record, dict):
            raise ValueError(f"delivered fixture is missing: {fixture_id}")
        path = fixture_dir / str(record["file"])
        actual = sha256_file(path)
        if actual != record.get("derived_sha256"):
            raise ValueError(f"delivered fixture checksum mismatch: {fixture_id}")
        identities.append({"fixture_id": fixture_id, "sha256": actual})
    return identities


def run_worker(command: list[str], environment: dict[str, str], timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "terminal_status": "TIMEOUT",
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    line = next(
        (value for value in completed.stdout.splitlines() if value.startswith("M4A_QUALIFICATION_RESULT=")),
        None,
    )
    if completed.returncode != 0 or line is None:
        return {
            "terminal_status": "ERROR",
            "worker_exit_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "error_tail": completed.stderr[-2000:],
        }
    report = json.loads(line.removeprefix("M4A_QUALIFICATION_RESULT="))
    report.update(terminal_status="SUCCESS", worker_exit_code=completed.returncode)
    return report


def _candidate_command(
    runtime_python: Path,
    domain: str,
    model_dir: Path,
    fixture_dir: Path,
    plan: Path,
    prompts: Path,
    vocos: Path,
    cycles: int,
    warmups: int,
) -> list[str]:
    command = [
        str(runtime_python), "-m", "audio_poc.m4a_qualification_worker",
        "--domain", domain,
        "--model-dir", str(model_dir),
        "--plan", str(plan if domain == "asr" else prompts),
        "--cycles", str(cycles),
        "--warmups", str(warmups),
    ]
    if domain == "asr":
        command.extend(("--fixture-dir", str(fixture_dir)))
    else:
        command.extend(("--vocos", str(vocos)))
    return command


def run_candidate(
    runtime_python: Path,
    domain: str,
    model_dir: Path,
    fixture_dir: Path,
    plan: Path,
    prompts: Path,
    vocos: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    cold = []
    for repetition in range(1, COLD_REPETITIONS + 1):
        result = run_worker(
            _candidate_command(runtime_python, domain, model_dir, fixture_dir, plan, prompts, vocos, 1, 0),
            environment,
            3600,
        )
        result["repetition"] = repetition
        cold.append(result)
    hot = run_worker(
        _candidate_command(
            runtime_python, domain, model_dir, fixture_dir, plan, prompts, vocos,
            HOT_REPETITIONS, WARMUPS,
        ),
        environment,
        7200,
    )
    return {"domain": domain, "cold": cold, "hot": hot}


def _successful_results(run: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    workers = run[phase] if phase == "cold" else [run[phase]]
    return [
        item
        for worker in workers
        if worker.get("terminal_status") == "SUCCESS"
        for item in worker["results"]
    ]


def summarize_asr(run: dict[str, Any]) -> dict[str, Any]:
    cold = _successful_results(run, "cold")
    hot = _successful_results(run, "hot")
    categories: dict[str, dict[str, Any]] = {}
    for category in sorted({str(item["category"]) for item in hot}):
        selected = [item for item in hot if item["category"] == category]
        reference_length = sum(int(item["reference_length"]) for item in selected)
        edits = sum(int(item["edit_distance"]) for item in selected)
        categories[category] = {
            "result_count": len(selected),
            "reference_codepoints": reference_length,
            "edit_distance": edits,
            "cer": round(edits / reference_length, 6) if reference_length else None,
            "sentence_correct_rate": round(
                sum(bool(item["sentence_correct"]) for item in selected) / len(selected), 6
            ) if selected else None,
        }
    core_cer = categories.get("taiwan_mandarin", {}).get("cer")
    sentence_rate = round(
        sum(bool(item["sentence_correct"]) for item in hot) / len(hot), 6
    ) if hot else None
    execution_complete = len(cold) == 3 * 50 and len(hot) == 20 * 50
    quality_pass = execution_complete and core_cer is not None and core_cer <= 0.20 and sentence_rate >= 0.70
    return {
        "execution_complete": execution_complete,
        "cold_latency_ms": numeric_summary([float(item["latency_ms"]) for item in cold]),
        "hot_latency_ms": numeric_summary([float(item["latency_ms"]) for item in hot]),
        "hot_rtf": numeric_summary([float(item["rtf"]) for item in hot]),
        "categories": categories,
        "overall_sentence_correct_rate": sentence_rate,
        "frozen_gate": {"core_cer_lte": 0.20, "sentence_correct_rate_gte": 0.70},
        "quality_gate_pass": quality_pass,
    }


def summarize_tts(run: dict[str, Any]) -> dict[str, Any]:
    cold = _successful_results(run, "cold")
    hot = _successful_results(run, "hot")
    first_chunk = [float(item["first_chunk_ms"]) for item in hot]
    rtf = [float(item["rtf"]) for item in hot]
    execution_complete = len(cold) == 3 * 20 and len(hot) == 20 * 20
    first_summary = numeric_summary(first_chunk)
    rtf_summary = numeric_summary(rtf)
    performance_pass = (
        execution_complete
        and first_summary["p95"] is not None and float(first_summary["p95"]) <= 1500
        and rtf_summary["p95"] is not None and float(rtf_summary["p95"]) <= 1.0
    )
    return {
        "execution_complete": execution_complete,
        "cold_latency_ms": numeric_summary([float(item["latency_ms"]) for item in cold]),
        "hot_latency_ms": numeric_summary([float(item["latency_ms"]) for item in hot]),
        "hot_first_chunk_ms": first_summary,
        "hot_rtf": rtf_summary,
        "native_pcm": {
            "sample_rate_hz": 16000,
            "channels": 1,
            "sample_representation": "float32_api_buffer",
            "first_chunk_boundary": "synchronous_generate_returned_first_nonempty_buffer",
        },
        "frozen_gate": {"first_chunk_p95_ms_lte": 1500, "rtf_p95_lte": 1.0},
        "performance_gate_pass": performance_pass,
        "user_quality_gate": "PENDING_NO_PLAYBACK_OR_REVIEW_IN_THIS_PACKET",
    }


def tree_size_mib(path: Path) -> float:
    if path.is_file():
        return round(path.stat().st_size / 1024 / 1024, 3)
    return round(sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) / 1024 / 1024, 3)


def _resource_summary(run: dict[str, Any], limit_mib: int, disk_mib: float) -> dict[str, Any]:
    workers = [*run["cold"], run["hot"]]
    successful = [worker for worker in workers if worker.get("terminal_status") == "SUCCESS"]
    peak = max((float(worker["peak_rss_mib"]) for worker in successful), default=None)
    cpu_percent = [
        100 * float(worker["cpu_ms"]) / float(worker["duration_ms"])
        for worker in successful if float(worker.get("duration_ms", 0)) > 0
    ]
    hot_series = run["hot"].get("rss_after_cycle_mib", [])
    return {
        "peak_rss_mib": peak,
        "advisory_limit_mib": limit_mib,
        "within_advisory_limit": peak is not None and peak <= limit_mib,
        "worker_cpu_percent": numeric_summary(cpu_percent),
        "model_disk_mib": disk_mib,
        "model_load_ms": numeric_summary([float(worker["load_ms"]) for worker in successful]),
        "hot_rss_after_cycle_mib": hot_series,
        "growth_disposition": "PENDING_TECHNICAL_REVIEW_NO_NUMERIC_TOLERANCE_FROZEN",
    }


def thermal_observation() -> dict[str, Any]:
    temperature = None
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.is_file():
        temperature = round(int(thermal_path.read_text().strip()) / 1000, 3)
    throttled = None
    if shutil.which("vcgencmd"):
        command = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False)
        if command.returncode == 0 and "=" in command.stdout:
            throttled = command.stdout.strip().split("=", 1)[1]
    return {"temperature_c": temperature, "throttled_hex": throttled}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full Git SHA")
    if args.output.exists() or args.work_dir.exists():
        raise ValueError("output and work directory must be new paths")
    target = target_platform()
    assert_target(target)
    manifest = json.loads((repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text())
    for candidate_id in sorted(AUTHORIZED_CANDIDATES):
        verify_candidate_inputs(manifest, candidate_id, args.artifact_dir)

    plan_path = repo_root() / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    prompts_path = repo_root() / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(plan_path) != PLAN_SHA256 or sha256_file(prompts_path) != PROMPTS_SHA256:
        raise ValueError("tracked frozen plan or prompt checksum mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    fixture_identities = verify_fixtures(args.fixture_dir, plan)
    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
    if len(prompts) != 20:
        raise ValueError("frozen TTS prompt set must contain exactly 20 prompts")

    args.work_dir.mkdir(parents=True)
    asr_model = safe_extract(
        args.artifact_dir / "models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09.tar.bz2",
        args.work_dir, "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09",
    )
    tts_model = safe_extract(
        args.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        args.work_dir, "matcha-icefall-zh-en",
    )
    runtime_python = args.runtime_dir / "bin/python"
    if not runtime_python.is_file():
        raise ValueError("authorized runtime Python is unavailable")
    environment = os.environ.copy()
    environment.update({
        "PYTHONPATH": str(repo_root() / "poc_audio/src"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1", "NO_PROXY": "*",
    })
    owners_before = audio_device_owner_count()
    thermal_before = thermal_observation()
    asr_run = run_candidate(
        runtime_python, "asr", asr_model, args.fixture_dir, plan_path, prompts_path,
        args.artifact_dir / "models/vocos-16khz-univ.onnx", environment,
    )
    tts_run = run_candidate(
        runtime_python, "tts", tts_model, args.fixture_dir, plan_path, prompts_path,
        args.artifact_dir / "models/vocos-16khz-univ.onnx", environment,
    )
    thermal_after = thermal_observation()
    owners_after = audio_device_owner_count()
    summaries = {"asr": summarize_asr(asr_run), "tts": summarize_tts(tts_run)}
    executions_complete = summaries["asr"]["execution_complete"] and summaries["tts"]["execution_complete"]
    metrics_pass = summaries["asr"]["quality_gate_pass"] and summaries["tts"]["performance_gate_pass"]
    cleanup_clean = owners_before == owners_after == 0
    if not executions_complete:
        status = "QUALIFICATION_INCONCLUSIVE_RETAINED"
    elif not metrics_pass:
        status = "QUALIFICATION_QUALITY_LATENCY_FAIL_RETAINED"
    else:
        status = "QUALIFICATION_QUALITY_LATENCY_PASS_PENDING_RESOURCE_LIFECYCLE_USER_OFFLINE"
    report = {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-WP3-FULL-QUALIFICATION",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "platform": target,
        "scope": "AUTHORIZED_ASR_TTS_FULL_FIXTURE_QUALITY_RESOURCE_NO_PLAYBACK",
        "method": {
            "threads": 2,
            "warmups": WARMUPS,
            "cold_repetitions": COLD_REPETITIONS,
            "cold_definition": "new_worker_and_model_load_then_one_complete_suite",
            "hot_repetitions": HOT_REPETITIONS,
            "hot_definition": "one_loaded_model_runs_complete_suite_twenty_times",
            "percentile": "nearest_rank",
        },
        "input_identity": {
            "delivered_fixture_manifest_sha256": FIXTURE_MANIFEST_SHA256,
            "asr_fixture_count": len(fixture_identities),
            "asr_fixture_set_sha256": hashlib.sha256(
                json.dumps(fixture_identities, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "recording_plan_sha256": PLAN_SHA256,
            "tts_prompts_sha256": PROMPTS_SHA256,
            "tts_prompt_count": len(prompts),
        },
        "network_evidence": "OFFLINE_ENVIRONMENT_ONLY_NOT_NETWORK_DISABLED_P12_PENDING",
        "raw_runs": {"asr": asr_run, "tts": tts_run},
        "summaries": summaries,
        "resources": {
            "asr": _resource_summary(asr_run, 1250, tree_size_mib(asr_model)),
            "tts": _resource_summary(tts_run, 1000, tree_size_mib(tts_model) + tree_size_mib(args.artifact_dir / "models/vocos-16khz-univ.onnx")),
            "thermal_before": thermal_before,
            "thermal_after": thermal_after,
        },
        "security": {
            "raw_transcript_emitted": False,
            "pcm_emitted": False,
            "audio_device_opened": False,
            "speaker_playback": False,
        },
        "pending": [
            "candidate lifecycle timeout/cancel/force-abort/reopen",
            "network-disabled P12 run and attempted-network trace",
            "User TTS quality review and critical-misread record",
            "RSS growth technical review",
        ],
        "execution_status": status,
        "cleanup": {
            "child_processes": 0, "threads": 0, "iterators": 0, "streams": 0,
            "device_owners": owners_after, "clean": cleanup_clean,
        },
    }
    validate_m4a_qualification(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"qualification report: {args.output} ({status})")
    return 0 if executions_complete and cleanup_clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
