"""Run the frozen Common Voice dev baseline for base Q8 and small Q8."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from .m2b_c_fixture_lock import load_json, sha256_file
from .m2b_c_padding_probe import _summary
from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_qualification import NativeWhisperWorker


PACKET_ID = "M2B-C-COMMON-VOICE-DEV-BASELINE-001"
BASE_ID = "asr-whispercpp-base-q8_0-1.9.2-m2b"
SMALL_ID = "asr-whispercpp-small-q8_0-1.9.2"
WORKER_SHA256 = "ad71dd80efbac7d346a99b776ade2e0e2b849d9dc389e690120b7b592ba31210"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("packet_id") != PACKET_ID \
            or packet.get("status") != "FROZEN_BEFORE_COMMON_VOICE_DEV_INFERENCE":
        raise ValueError("Common Voice dev packet identity mismatch")
    scope = packet.get("scope", {})
    if scope != {
        "family": "common_voice", "split": "dev",
        "review_ids": ["D02", "D05", "N03", "L03"],
        "holdout_execution": "SEALED",
        "internal_execution": "NOT_PART_OF_EXTERNAL_BASELINE",
    }:
        raise ValueError("Common Voice dev scope mismatch")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or [item.get("candidate_id") for item in candidates] != [BASE_ID, SMALL_ID]:
        raise ValueError("Common Voice dev candidate order mismatch")
    expected_artifacts = [
        {"filename": "ggml-base-q8_0.bin", "size_bytes": 81768585, "sha256": "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"},
        {"filename": "ggml-small-q8_0.bin", "size_bytes": 264464607, "sha256": "49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f"},
    ]
    if [item.get("artifact") for item in candidates] != expected_artifacts:
        raise ValueError("Common Voice dev artifact mismatch")
    runtime = packet.get("runtime", {})
    if (
        runtime.get("native_worker_sha256") != WORKER_SHA256
        or runtime.get("threads") != 4
        or runtime.get("decoder") != "greedy"
        or any(runtime.get(key) is not False for key in ("context", "timestamps", "internal_vad"))
    ):
        raise ValueError("Common Voice dev runtime mismatch")
    execution = packet.get("execution", {})
    expected = {
        "candidate_order": [BASE_ID, SMALL_ID], "warmups_per_item": 1,
        "scored_inferences_per_item": 1, "scored_observations": 8,
        "per_item_timeout_seconds": 120, "candidate_budget_seconds": 600,
        "network": "isolated_namespace", "audio_capture": False, "audio_playback": False,
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        raise ValueError("Common Voice dev execution controls mismatch")


def verify_inputs(
    packet: dict[str, Any], tracked_path: Path, controlled_path: Path,
    fixtures_root: Path,
) -> list[dict[str, Any]]:
    identity = packet["fixture_lock"]
    if sha256_file(tracked_path) != identity["tracked_manifest_sha256"] \
            or sha256_file(controlled_path) != identity["controlled_manifest_sha256"]:
        raise ValueError("C PCM lock checksum mismatch")
    tracked, controlled = load_json(tracked_path), load_json(controlled_path)
    sanitized = {item["review_id"]: item for item in tracked["records"]["common_voice"]}
    private = {item["review_id"]: item for item in controlled["records"]["common_voice"]}
    items = []
    for review_id in packet["scope"]["review_ids"]:
        expected, raw = sanitized.get(review_id), private.get(review_id)
        if expected is None or raw is None or raw.get("split") != "dev":
            raise ValueError(f"missing Common Voice dev item: {review_id}")
        for field in (
            "review_id", "split", "fixture_id", "category", "reference_sha256",
            "client_sha256", "source_sha256", "frames", "duration_seconds",
            "derived_wav_size_bytes", "derived_wav_sha256",
        ):
            if raw.get(field) != expected.get(field):
                raise ValueError(f"Common Voice controlled identity mismatch: {review_id}")
        reference = str(raw.get("reference_text", ""))
        if hashlib.sha256(reference.encode()).hexdigest() != expected["reference_sha256"]:
            raise ValueError(f"Common Voice reference mismatch: {review_id}")
        wav = fixtures_root / str(raw["relative_wav_path"])
        if wav.stat().st_size != expected["derived_wav_size_bytes"] \
                or sha256_file(wav) != expected["derived_wav_sha256"]:
            raise ValueError(f"Common Voice WAV mismatch: {review_id}")
        items.append({**raw, "wav_path": wav})
    return items


def score(
    candidate_id: str, item: dict[str, Any], metrics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    hypothesis = str(metrics["hypothesis"])
    reference, normalized = normalize_asr(str(item["reference_text"])), normalize_asr(hypothesis)
    latency, duration = float(metrics["latency_ms"]), float(item["duration_seconds"])
    common = {
        "candidate_id": candidate_id, "review_id": item["review_id"],
        "fixture_id": item["fixture_id"], "family": "common_voice", "split": "dev",
        "category": item["category"], "audio_duration_seconds": duration,
        "latency_ms": round(latency, 3), "native_inference_ms": float(metrics["native_inference_ms"]),
        "cpu_ms": float(metrics["cpu_ms"]), "peak_rss_mib": float(metrics["peak_rss_mib"]),
        "rtf": round(latency / 1000.0 / duration, 6), "reference_length": len(reference),
        "hypothesis_length": len(normalized), "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
    }
    return {**common, "reference_text": item["reference_text"], "hypothesis": hypothesis}, common


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = {}
    categories = {}
    for candidate_id in (BASE_ID, SMALL_ID):
        selected = [item for item in results if item["candidate_id"] == candidate_id]
        candidates[candidate_id] = _summary(selected)
        categories[candidate_id] = {
            category: _summary([item for item in selected if item["category"] == category])
            for category in sorted({str(item["category"]) for item in selected})
        }
    by_pair = {(item["review_id"], item["candidate_id"]): item for item in results}
    paired = []
    for review_id in sorted({str(item["review_id"]) for item in results}):
        base, small = by_pair[(review_id, BASE_ID)], by_pair[(review_id, SMALL_ID)]
        paired.append({
            "review_id": review_id,
            "edit_distance_delta_small_minus_base": int(small["edit_distance"]) - int(base["edit_distance"]),
            "sentence_correctness_delta_small_minus_base": int(bool(small["sentence_correct"])) - int(bool(base["sentence_correct"])),
            "latency_ms_delta_small_minus_base": round(float(small["latency_ms"]) - float(base["latency_ms"]), 3),
            "rss_mib_delta_small_minus_base": round(float(small["peak_rss_mib"]) - float(base["peak_rss_mib"]), 3),
        })
    return {"family": "common_voice", "split": "dev", "candidates": candidates, "candidate_categories": categories, "paired_candidate_delta": paired}


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=root / "poc_audio/manifests/m2b_c_common_voice_dev_baseline.json")
    parser.add_argument("--tracked-lock", type=Path, default=root / "poc_audio/manifests/m2b_c_pcm_lock.json")
    parser.add_argument("--controlled-lock", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--small-model", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root().resolve()
    for path in (args.work_dir, args.output, args.sanitized_output):
        if path.exists() or path.resolve().is_relative_to(root):
            raise ValueError("Common Voice baseline outputs must be new and outside Git")
    if args.packet.resolve() != root / "poc_audio/manifests/m2b_c_common_voice_dev_baseline.json":
        raise ValueError("Common Voice baseline must use the tracked packet")
    packet = load_json(args.packet)
    validate_packet(packet)
    models = {BASE_ID: args.base_model, SMALL_ID: args.small_model}
    for candidate in packet["candidates"]:
        model, artifact = models[candidate["candidate_id"]], candidate["artifact"]
        if model.name != artifact["filename"] or model.stat().st_size != artifact["size_bytes"] \
                or sha256_file(model) != artifact["sha256"]:
            raise ValueError(f"candidate model mismatch: {candidate['candidate_id']}")
    if sha256_file(args.binary) != packet["runtime"]["native_worker_sha256"]:
        raise ValueError("native worker mismatch")
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    items = verify_inputs(packet, args.tracked_lock, args.controlled_lock, args.fixtures_root)
    args.work_dir.mkdir(parents=True)
    raw_results, sanitized_results, runtimes, cleanups = [], [], {}, {}
    error_code = None
    started = time.monotonic()
    try:
        for candidate_id in packet["execution"]["candidate_order"]:
            model = models[candidate_id]
            command = [str(args.binary.resolve()), "--model", str(model.resolve()), "--threads", "4"]
            worker = NativeWhisperWorker(command, args.work_dir / f"{candidate_id}.stderr.log")
            owners_before = audio_device_owner_count()
            candidate_started = time.monotonic()
            try:
                worker.start()
                for item in items:
                    worker.transcribe(item["wav_path"], 120.0)
                    metrics = worker.transcribe(item["wav_path"], 120.0)
                    raw, sanitized = score(candidate_id, item, metrics)
                    raw_results.append(raw)
                    sanitized_results.append(sanitized)
                    if time.monotonic() - candidate_started > 600:
                        raise TimeoutError("Common Voice candidate budget exceeded")
            finally:
                cleanup = worker.stop()
            owners_after = audio_device_owner_count()
            cleanup.update({"threads": 0, "iterators": 0, "streams": 0, "device_owners": owners_after})
            cleanup["clean"] = bool(cleanup["clean"] and owners_before == owners_after == 0)
            cleanups[candidate_id] = cleanup
            runtimes[candidate_id] = {
                "load_ms": worker.load_ms, "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
                "runtime_executable_sha256": sha256_file(args.binary),
            }
    except Exception as error:
        error_code = type(error).__name__
    assert_network_isolated()
    complete = len(sanitized_results) == 8 and error_code is None \
        and len(cleanups) == 2 and all(item["clean"] for item in cleanups.values())
    base = {
        "schema_version": "1.0", "report_id": PACKET_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(), "review_status": "UNREVIEWED",
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_REVIEW" if complete else "INCONCLUSIVE_RETAINED",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "fixture_lock": packet["fixture_lock"], "scope": packet["scope"],
        "method": packet["execution"], "runtime": runtimes,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "summary": summarize(sanitized_results) if complete else None,
        "error_code": error_code, "cleanup": cleanups,
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_BASELINE",
        "security": {"audio_device_opened": False, "speaker_playback": False, "pcm_emitted_to_report": False},
    }
    raw = {**base, "git_safety": "CONTROLLED_TRANSCRIPTS_AND_PATHS_DO_NOT_COMMIT", "results": raw_results}
    sanitized = {**base, "results": sanitized_results, "raw_transcript_emitted": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.sanitized_output.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Common Voice dev baseline: {args.sanitized_output} ({base['execution_status']})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
