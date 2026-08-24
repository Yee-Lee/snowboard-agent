"""Five-item M3 direct-PCM baseline using the frozen base-Q8 worker."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import wave
from pathlib import Path
from typing import Any

from .m2b_c_task_scoring import normalize_task
from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_whispercpp_qualification import NativeWhisperWorker


MODEL_SHA256 = "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"
BINARY_SHA256 = "64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b"
PROMPT = "繁體中文。常用技術詞彙：Wi-Fi、audio frame、音訊基線、候選語音模型、離線執行。"
PROMPT_SHA256 = "e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef"
FIXTURE_IDS = (
    "asr-clear-002",
    "asr-clear-003",
    "asr-pause-031",
    "asr-clear-012",
    "asr-clear-023",
)
TASK_SCORING_FILENAME = "m2b_c_task_adjusted_scoring.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_wav(path: Path) -> tuple[bytes, float]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (16_000, 1, 2, "NONE"):
            raise ValueError(f"M3 ASR fixture format mismatch: {path.name}")
        frames = source.readframes(source.getnframes())
    if not frames:
        raise ValueError(f"M3 ASR fixture is empty: {path.name}")
    return frames, len(frames) / 2 / 16_000


def _level(payload: bytes) -> dict[str, float | int]:
    samples = [item[0] for item in struct.iter_unpack("<h", payload)]
    peak = max(abs(item) for item in samples)
    rms = math.sqrt(sum(item * item for item in samples) / len(samples))
    return {
        "peak_abs_s16": peak,
        "rms_s16": round(rms, 3),
        "clipped_samples": sum(abs(item) >= 32_767 for item in samples),
    }


def load_task_script_map(repo_root: Path) -> dict[str, str]:
    scoring_path = repo_root / "poc_audio/manifests" / TASK_SCORING_FILENAME
    scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
    return scoring["normalization"]["traditional_to_simplified"]


def run_direct_asr(
    repo_root: Path,
    fixture_dir: Path,
    binary: Path,
    model: Path,
    work_dir: Path,
    poc_execution_sha: str,
    timeout: float,
    run_id: str = "M3-ASR-DIRECT-PCM-BASELINE-001",
    source_fixture_lock: Path | None = None,
) -> dict[str, Any]:
    if run_id not in {"M3-ASR-DIRECT-PCM-BASELINE-001", "M3-ASR-HAL-PATH-001"}:
        raise ValueError("unsupported M3 ASR run identity")
    if work_dir.exists():
        raise ValueError("M3 ASR work directory must be new")
    if sha256_file(binary) != BINARY_SHA256:
        raise ValueError("M3 ASR worker binary checksum mismatch")
    if sha256_file(model) != MODEL_SHA256:
        raise ValueError("M3 ASR model checksum mismatch")
    plan_path = repo_root / "poc_audio/fixtures/authorized/recording_plan_v1.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    planned = {item["fixture_id"]: item for item in plan["utterances"]}
    script_map = load_task_script_map(repo_root)
    work_dir.mkdir(parents=True)
    fixture_records: list[dict[str, Any]] = []
    for fixture_id in FIXTURE_IDS:
        item = planned[fixture_id]
        path = fixture_dir / f"{fixture_id}.wav"
        payload, duration = _read_wav(path)
        fixture_records.append({
            "fixture_id": fixture_id,
            "category": item["category"],
            "file": path.name,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "duration_seconds": round(duration, 6),
            "reference_sha256": hashlib.sha256(item["reference_text"].encode()).hexdigest(),
            "level": _level(payload),
        })
    lock = {
        "schema_version": "1.0",
        "lock_id": "M3-ASR-FIVE-FIXTURE-LOCK-001",
        "poc_execution_sha": poc_execution_sha,
        "fixture_count": len(fixture_records),
        "records": fixture_records,
    }
    lock_path = work_dir / "m3_asr_fixture_lock.json"
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    inference_lock_sha = sha256_file(lock_path)
    source_lock_sha = inference_lock_sha
    if run_id == "M3-ASR-HAL-PATH-001":
        if source_fixture_lock is None or not source_fixture_lock.is_file():
            raise ValueError("M3 ASR HAL path requires the direct-PCM source fixture lock")
        source_lock = json.loads(source_fixture_lock.read_text(encoding="utf-8"))
        if (
            source_lock.get("lock_id") != "M3-ASR-FIVE-FIXTURE-LOCK-001"
            or source_lock.get("poc_execution_sha") != poc_execution_sha
            or [item.get("fixture_id") for item in source_lock.get("records", [])]
            != list(FIXTURE_IDS)
            or [item.get("reference_sha256") for item in source_lock.get("records", [])]
            != [item["reference_sha256"] for item in fixture_records]
        ):
            raise ValueError("M3 ASR HAL source fixture lock identity mismatch")
        source_lock_sha = sha256_file(source_fixture_lock)
    command = [
        str(binary.resolve()),
        "--model", str(model.resolve()),
        "--threads", "4",
        "--initial-prompt", PROMPT,
    ]
    worker = NativeWhisperWorker(command, work_dir / "base-q8.stderr.log")
    results: list[dict[str, Any]] = []
    cleanup: dict[str, Any]
    try:
        worker.start()
        worker.transcribe(fixture_dir / f"{FIXTURE_IDS[0]}.wav", timeout)
        for fixture_id in FIXTURE_IDS:
            item = planned[fixture_id]
            metrics = worker.transcribe(fixture_dir / f"{fixture_id}.wav", timeout)
            hypothesis = str(metrics.pop("hypothesis"))
            raw_reference = normalize_asr(item["reference_text"])
            raw_hypothesis = normalize_asr(hypothesis)
            task_reference = normalize_task(item["reference_text"], script_map)
            task_hypothesis = normalize_task(hypothesis, script_map)
            results.append({
                "fixture_id": fixture_id,
                "category": item["category"],
                **metrics,
                "raw_reference_length": len(raw_reference),
                "raw_hypothesis_length": len(raw_hypothesis),
                "raw_edit_distance": edit_distance(raw_reference, raw_hypothesis),
                "raw_sentence_correct": raw_reference == raw_hypothesis,
                "task_reference_length": len(task_reference),
                "task_hypothesis_length": len(task_hypothesis),
                "task_edit_distance": edit_distance(task_reference, task_hypothesis),
                "task_sentence_correct": task_reference == task_hypothesis,
                "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
                "raw_transcript_emitted": False,
            })
    finally:
        cleanup = worker.stop()
    if not cleanup["clean"]:
        raise RuntimeError("M3 ASR worker cleanup failed")
    stderr_path = work_dir / "base-q8.stderr.log"
    return {
        "_result_disposition": "INCONCLUSIVE",
        "review_disposition": "PENDING_PAIRED_PATH_AND_USER_SEMANTIC_REVIEW",
        "run_id": run_id,
        "candidate_id": "asr-whispercpp-base-q8_0-1.9.2-m2b",
        "fixture_lock_sha256": source_lock_sha,
        "inference_fixture_lock_sha256": inference_lock_sha,
        "model_sha256": MODEL_SHA256,
        "worker_binary_sha256": BINARY_SHA256,
        "prompt_sha256": PROMPT_SHA256,
        "threads": 4,
        "decoder": "greedy",
        "language": "zh",
        "warmups": 1,
        "formal_inferences": len(results),
        "results": results,
        "worker_cleanup": cleanup,
        "worker_stderr_sha256": sha256_file(stderr_path),
    }
