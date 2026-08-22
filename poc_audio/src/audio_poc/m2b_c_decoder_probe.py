"""Run the frozen base Q8 greedy-versus-beam decoder probe."""

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


PROBE_ID = "M2B-C-BASE-Q8-DECODER-PROBE-001"
MODEL_SHA256 = "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"
WORKER_SHA256 = "8c0b67f4ca54576691c25ee3d20427e7f62f951c9499df8c50c90dacc4dcf93b"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def validate_probe(probe: dict[str, Any]) -> None:
    if probe.get("probe_id") != PROBE_ID or probe.get("status") != "FROZEN_BEFORE_DECODER_INFERENCE":
        raise ValueError("decoder probe identity mismatch")
    if probe.get("candidate_id") != "asr-whispercpp-base-q8_0-1.9.2-m2b" \
            or probe.get("artifact") != {
                "filename": "ggml-base-q8_0.bin", "size_bytes": 81768585,
                "sha256": MODEL_SHA256,
            }:
        raise ValueError("decoder probe candidate mismatch")
    runtime = probe.get("runtime", {})
    if (
        runtime.get("native_worker_sha256") != WORKER_SHA256
        or runtime.get("source_sha") != "3403b4b1bd970d81754ae4aed34dd12f7ebdb4fd"
        or runtime.get("threads") != 4
        or any(runtime.get(key) is not False for key in ("context", "timestamps", "internal_vad"))
    ):
        raise ValueError("decoder probe runtime mismatch")
    if probe.get("single_variable") != {
        "name": "decoder",
        "baseline": {"strategy": "greedy", "best_of": 1},
        "probe": {"strategy": "beam", "beam_size": 5, "patience": 1.0},
    }:
        raise ValueError("decoder probe changes more than decoder strategy")
    scope = probe.get("scope", {})
    fixtures = scope.get("fixture_ids")
    if (
        scope.get("family") != "internal" or scope.get("split") != "dev"
        or scope.get("pcm_profile") != "p0" or not isinstance(fixtures, list)
        or len(fixtures) != 8 or len(set(fixtures)) != 8
        or scope.get("holdout_execution") != "SEALED"
        or scope.get("common_voice_execution") != "NOT_PART_OF_DECODER_PROBE"
    ):
        raise ValueError("decoder probe scope mismatch")
    execution = probe.get("execution", {})
    expected = {
        "decoder_order": ["greedy", "beam"], "warmups_per_item": 1,
        "scored_inferences_per_item": 1, "scored_observations": 16,
        "per_item_timeout_seconds": 120, "decoder_budget_seconds": 900,
        "network": "isolated_namespace", "audio_capture": False, "audio_playback": False,
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        raise ValueError("decoder probe execution controls mismatch")


def verify_inputs(
    probe: dict[str, Any], tracked_path: Path, controlled_path: Path,
    fixtures_root: Path,
) -> list[dict[str, Any]]:
    identity = probe["fixture_lock"]
    if sha256_file(tracked_path) != identity["tracked_manifest_sha256"] \
            or sha256_file(controlled_path) != identity["controlled_manifest_sha256"]:
        raise ValueError("decoder probe C lock checksum mismatch")
    tracked, controlled = load_json(tracked_path), load_json(controlled_path)
    sanitized = {item["fixture_id"]: item for item in tracked["records"]["internal"]}
    private = {item["fixture_id"]: item for item in controlled["records"]["internal"]}
    items = []
    for fixture_id in probe["scope"]["fixture_ids"]:
        expected, raw = sanitized.get(fixture_id), private.get(fixture_id)
        if expected is None or raw is None or raw.get("split") != "dev":
            raise ValueError(f"missing decoder dev fixture: {fixture_id}")
        reference = str(raw.get("reference_text", ""))
        if hashlib.sha256(reference.encode()).hexdigest() != expected["reference_sha256"]:
            raise ValueError(f"decoder reference mismatch: {fixture_id}")
        expected_variant = next(item for item in expected["variants"] if item["profile"] == "p0")
        raw_variant = next(item for item in raw["variants"] if item["profile"] == "p0")
        for field in (
            "profile", "frames", "duration_seconds", "derived_wav_size_bytes", "derived_wav_sha256",
        ):
            if raw_variant.get(field) != expected_variant.get(field):
                raise ValueError(f"decoder P0 identity mismatch: {fixture_id}")
        wav = fixtures_root / str(raw_variant["relative_wav_path"])
        if wav.stat().st_size != expected_variant["derived_wav_size_bytes"] \
                or sha256_file(wav) != expected_variant["derived_wav_sha256"]:
            raise ValueError(f"decoder P0 WAV mismatch: {fixture_id}")
        items.append({**raw, "p0": raw_variant, "wav_path": wav})
    return items


def score(
    decoder: str, item: dict[str, Any], metrics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    hypothesis = str(metrics["hypothesis"])
    reference, normalized = normalize_asr(str(item["reference_text"])), normalize_asr(hypothesis)
    latency, duration = float(metrics["latency_ms"]), float(item["p0"]["duration_seconds"])
    common = {
        "decoder": decoder, "fixture_id": item["fixture_id"], "review_id": item["review_id"],
        "family": "internal", "split": "dev", "category": item["category"],
        "latency_ms": round(latency, 3), "native_inference_ms": float(metrics["native_inference_ms"]),
        "cpu_ms": float(metrics["cpu_ms"]), "peak_rss_mib": float(metrics["peak_rss_mib"]),
        "audio_duration_seconds": duration, "rtf": round(latency / 1000.0 / duration, 6),
        "reference_length": len(reference), "hypothesis_length": len(normalized),
        "edit_distance": edit_distance(reference, normalized), "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
    }
    return {**common, "reference_text": item["reference_text"], "hypothesis": hypothesis}, common


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    decoders, categories = {}, {}
    for decoder in ("greedy", "beam"):
        selected = [item for item in results if item["decoder"] == decoder]
        decoders[decoder] = _summary(selected)
        categories[decoder] = {
            category: _summary([item for item in selected if item["category"] == category])
            for category in sorted({str(item["category"]) for item in selected})
        }
    by_pair = {(item["fixture_id"], item["decoder"]): item for item in results}
    paired = []
    for fixture_id in sorted({str(item["fixture_id"]) for item in results}):
        greedy, beam = by_pair[(fixture_id, "greedy")], by_pair[(fixture_id, "beam")]
        paired.append({
            "fixture_id": fixture_id,
            "edit_distance_delta_beam_minus_greedy": int(beam["edit_distance"]) - int(greedy["edit_distance"]),
            "sentence_correctness_delta_beam_minus_greedy": int(bool(beam["sentence_correct"])) - int(bool(greedy["sentence_correct"])),
            "latency_ms_delta_beam_minus_greedy": round(float(beam["latency_ms"]) - float(greedy["latency_ms"]), 3),
            "rss_mib_delta_beam_minus_greedy": round(float(beam["peak_rss_mib"]) - float(greedy["peak_rss_mib"]), 3),
        })
    return {"family": "internal", "split": "dev", "decoders": decoders, "decoder_categories": categories, "paired_decoder_delta": paired}


def predecessor_match(probe: dict[str, Any], results: list[dict[str, Any]], root: Path) -> bool:
    predecessor = probe["greedy_predecessor"]
    path = root / predecessor["path"]
    if sha256_file(path) != predecessor["sha256"]:
        raise ValueError("greedy predecessor checksum mismatch")
    previous = load_json(path)
    expected = {
        item["fixture_id"]: item["hypothesis_sha256"]
        for item in previous["results"] if item.get("profile") == predecessor["profile"]
    }
    observed = {
        item["fixture_id"]: item["hypothesis_sha256"]
        for item in results if item["decoder"] == "greedy"
    }
    return observed == expected


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, default=root / "poc_audio/manifests/m2b_c_base_q8_decoder_probe.json")
    parser.add_argument("--tracked-lock", type=Path, default=root / "poc_audio/manifests/m2b_c_pcm_lock.json")
    parser.add_argument("--controlled-lock", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root().resolve()
    for path in (args.work_dir, args.output, args.sanitized_output):
        if path.exists() or path.resolve().is_relative_to(root):
            raise ValueError("decoder probe outputs must be new and outside Git")
    if args.probe.resolve() != root / "poc_audio/manifests/m2b_c_base_q8_decoder_probe.json":
        raise ValueError("decoder probe must use the tracked packet")
    probe = load_json(args.probe)
    validate_probe(probe)
    artifact = probe["artifact"]
    if args.model.name != artifact["filename"] or args.model.stat().st_size != artifact["size_bytes"] \
            or sha256_file(args.model) != artifact["sha256"]:
        raise ValueError("decoder probe model mismatch")
    if sha256_file(args.binary) != probe["runtime"]["native_worker_sha256"] \
            or sha256_file(args.build_report) != probe["runtime"]["build_report_sha256"]:
        raise ValueError("decoder probe runtime closure mismatch")
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    items = verify_inputs(probe, args.tracked_lock, args.controlled_lock, args.fixtures_root)
    args.work_dir.mkdir(parents=True)
    raw_results, sanitized_results, runtimes, cleanups = [], [], {}, {}
    error_code = None
    started = time.monotonic()
    try:
        for decoder in probe["execution"]["decoder_order"]:
            command = [str(args.binary.resolve()), "--model", str(args.model.resolve()), "--threads", "4", "--decoder", decoder]
            if decoder == "beam":
                command += ["--beam-size", "5"]
            worker = NativeWhisperWorker(command, args.work_dir / f"{decoder}.stderr.log")
            owners_before = audio_device_owner_count()
            decoder_started = time.monotonic()
            try:
                worker.start()
                for item in items:
                    worker.transcribe(item["wav_path"], 120.0)
                    metrics = worker.transcribe(item["wav_path"], 120.0)
                    raw, sanitized = score(decoder, item, metrics)
                    raw_results.append(raw)
                    sanitized_results.append(sanitized)
                    if time.monotonic() - decoder_started > 900:
                        raise TimeoutError("decoder budget exceeded")
            finally:
                cleanup = worker.stop()
            owners_after = audio_device_owner_count()
            cleanup.update({"threads": 0, "iterators": 0, "streams": 0, "device_owners": owners_after})
            cleanup["clean"] = bool(cleanup["clean"] and owners_before == owners_after == 0)
            cleanups[decoder] = cleanup
            runtimes[decoder] = {
                "load_ms": worker.load_ms, "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
                "runtime_executable_sha256": sha256_file(args.binary),
            }
    except Exception as error:
        error_code = type(error).__name__
    assert_network_isolated()
    greedy_matches = predecessor_match(probe, sanitized_results, root) if len(sanitized_results) >= 8 else False
    if error_code is None and not greedy_matches:
        error_code = "GREEDY_PREDECESSOR_MISMATCH"
    complete = len(sanitized_results) == 16 and error_code is None \
        and len(cleanups) == 2 and all(item["clean"] for item in cleanups.values())
    base = {
        "schema_version": "1.0", "report_id": PROBE_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(), "review_status": "UNREVIEWED",
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_REVIEW" if complete else "INCONCLUSIVE_RETAINED",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "candidate_id": probe["candidate_id"], "artifact": artifact,
        "runtime": runtimes, "fixture_lock": probe["fixture_lock"], "scope": probe["scope"],
        "single_variable": probe["single_variable"], "method": probe["execution"],
        "greedy_predecessor_hypothesis_hash_match": greedy_matches,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "summary": summarize(sanitized_results) if len(sanitized_results) == 16 else None,
        "error_code": error_code, "cleanup": cleanups,
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_PROBE",
        "security": {"audio_device_opened": False, "speaker_playback": False, "pcm_emitted_to_report": False},
    }
    raw = {**base, "git_safety": "CONTROLLED_TRANSCRIPTS_AND_PATHS_DO_NOT_COMMIT", "results": raw_results}
    sanitized = {**base, "results": sanitized_results, "raw_transcript_emitted": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.sanitized_output.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Base Q8 decoder probe: {args.sanitized_output} ({base['execution_status']})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
