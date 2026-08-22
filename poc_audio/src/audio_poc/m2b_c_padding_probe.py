"""Run reviewed M2B C Internal endpoint-padding probes."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from .m2a_survey import numeric_summary
from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_qualification import NativeWhisperWorker
from .m2b_c_fixture_lock import load_json, sha256_file


DEV_REPORT_ID = "M2B-C-INTERNAL-PADDING-PROBE-001"
HOLDOUT_REPORT_ID = "M2B-C-INTERNAL-PADDING-HOLDOUT-001"
PROFILES = ("p0", "p300", "p500")
MODEL_SHA256 = "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"
WORKER_SHA256 = "ad71dd80efbac7d346a99b776ade2e0e2b849d9dc389e690120b7b592ba31210"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _validate_candidate_controls(document: dict[str, Any]) -> None:
    if document.get("candidate_id") != "asr-whispercpp-base-q8_0-1.9.2-m2b":
        raise ValueError("padding probe candidate mismatch")
    if document.get("artifact") != {
        "filename": "ggml-base-q8_0.bin",
        "size_bytes": 81768585,
        "sha256": MODEL_SHA256,
    }:
        raise ValueError("padding probe artifact mismatch")
    runtime = document.get("runtime", {})
    if (
        runtime.get("id") != "whispercpp-1.9.2-native-aarch64"
        or runtime.get("native_worker_sha256") != WORKER_SHA256
        or runtime.get("threads") != 4
        or runtime.get("decoder") != "greedy"
        or runtime.get("language") != "zh"
        or any(runtime.get(key) is not False for key in ("context", "timestamps", "internal_vad"))
    ):
        raise ValueError("padding probe runtime control mismatch")


def validate_probe(document: dict[str, Any]) -> None:
    if document.get("probe_id") != DEV_REPORT_ID:
        raise ValueError("padding probe identity mismatch")
    if document.get("status") != "AUTHORIZED_BY_USER_REVIEWED_C_LOCK":
        raise ValueError("padding probe is not authorized")
    _validate_candidate_controls(document)
    variable = document.get("single_variable")
    if variable != {
        "name": "frozen_label_padding_ms_each_side",
        "baseline": "p0",
        "probe_arms": ["p300", "p500"],
    }:
        raise ValueError("padding probe changes more than the authorized variable")
    scope = document.get("scope", {})
    fixtures = scope.get("fixture_ids")
    if (
        scope.get("family") != "internal"
        or scope.get("split") != "dev"
        or not isinstance(fixtures, list)
        or len(fixtures) != 8
        or len(set(fixtures)) != 8
        or scope.get("holdout_execution") != "SEALED"
        or scope.get("common_voice_execution") != "NOT_PART_OF_PADDING_PROBE"
    ):
        raise ValueError("padding probe scope mismatch")
    execution = document.get("execution", {})
    if execution.get("profile_orders") != [
        ["p0", "p300", "p500"],
        ["p300", "p500", "p0"],
        ["p500", "p0", "p300"],
    ]:
        raise ValueError("padding probe order mismatch")
    expected = {
        "warmups_per_fixture_profile": 1,
        "scored_inferences_per_fixture_profile": 1,
        "scored_observations": 24,
        "per_item_timeout_seconds": 120,
        "row_budget_seconds": 1200,
        "network": "isolated_namespace",
        "audio_capture": False,
        "audio_playback": False,
    }
    for key, value in expected.items():
        if execution.get(key) != value:
            raise ValueError(f"padding probe execution control mismatch: {key}")


def validate_holdout_probe(document: dict[str, Any]) -> None:
    if document.get("probe_id") != HOLDOUT_REPORT_ID:
        raise ValueError("padding holdout identity mismatch")
    if document.get("status") != "P300_FROZEN_FROM_REVIEWED_DEV_BEFORE_HOLDOUT":
        raise ValueError("padding holdout selection is not frozen")
    _validate_candidate_controls(document)
    review = document.get("dev_review", {})
    if review.get("sanitized_result_sha256") != "73132c6dcf8c029105ec3ca298b9f4a5234f6cd625c4992d654d0c2cc9d75c90" \
            or review.get("selection") != "p300":
        raise ValueError("padding holdout dev-review identity mismatch")
    if document.get("single_variable") != {
        "name": "frozen_label_padding_ms_each_side",
        "baseline": "p0",
        "probe_arms": ["p300"],
    }:
        raise ValueError("padding holdout changes more than the frozen variable")
    scope = document.get("scope", {})
    fixtures = scope.get("fixture_ids")
    if (
        scope.get("family") != "internal"
        or scope.get("split") != "holdout"
        or not isinstance(fixtures, list)
        or len(fixtures) != 8
        or len(set(fixtures)) != 8
        or scope.get("common_voice_execution") != "NOT_PART_OF_PADDING_PROBE"
    ):
        raise ValueError("padding holdout scope mismatch")
    execution = document.get("execution", {})
    if execution.get("profile_orders") != [["p0", "p300"], ["p300", "p0"]]:
        raise ValueError("padding holdout order mismatch")
    expected = {
        "warmups_per_fixture_profile": 1,
        "scored_inferences_per_fixture_profile": 1,
        "scored_observations": 16,
        "per_item_timeout_seconds": 120,
        "row_budget_seconds": 900,
        "network": "isolated_namespace",
        "audio_capture": False,
        "audio_playback": False,
    }
    for key, value in expected.items():
        if execution.get(key) != value:
            raise ValueError(f"padding holdout execution control mismatch: {key}")


def verify_inputs(
    probe: dict[str, Any], tracked_path: Path, controlled_path: Path,
    fixtures_root: Path,
) -> list[dict[str, Any]]:
    lock_identity = probe["fixture_lock"]
    if sha256_file(tracked_path) != lock_identity["tracked_manifest_sha256"]:
        raise ValueError("tracked C PCM lock checksum mismatch")
    if sha256_file(controlled_path) != lock_identity["controlled_manifest_sha256"]:
        raise ValueError("controlled C PCM lock checksum mismatch")
    tracked = load_json(tracked_path)
    controlled = load_json(controlled_path)
    if tracked.get("fixture_lock_id") != lock_identity["id"]:
        raise ValueError("tracked C PCM lock identity mismatch")
    if controlled.get("fixture_lock_id") != lock_identity["id"]:
        raise ValueError("controlled C PCM lock identity mismatch")
    sanitized_by_id = {item["fixture_id"]: item for item in tracked["records"]["internal"]}
    private_by_id = {item["fixture_id"]: item for item in controlled["records"]["internal"]}
    selected_profiles = {
        probe["single_variable"]["baseline"], *probe["single_variable"]["probe_arms"]
    }
    selected_split = probe["scope"]["split"]
    items = []
    for fixture_id in probe["scope"]["fixture_ids"]:
        sanitized, private = sanitized_by_id.get(fixture_id), private_by_id.get(fixture_id)
        if sanitized is None or private is None or private.get("split") != selected_split:
            raise ValueError(f"missing {selected_split} Internal fixture: {fixture_id}")
        for field in ("review_id", "split", "fixture_id", "category", "reference_sha256", "source_sha256"):
            if private.get(field) != sanitized.get(field):
                raise ValueError(f"controlled C fixture identity mismatch: {fixture_id}")
        reference = str(private.get("reference_text", ""))
        if not reference or hashlib.sha256(reference.encode()).hexdigest() != sanitized["reference_sha256"]:
            raise ValueError(f"controlled C reference mismatch: {fixture_id}")
        variants = {}
        for expected, raw in zip(sanitized["variants"], private["variants"], strict=True):
            for field in (
                "profile", "requested_padding_ms_each_side", "start_ms", "end_ms",
                "frames", "duration_seconds", "derived_wav_size_bytes", "derived_wav_sha256",
            ):
                if raw.get(field) != expected.get(field):
                    raise ValueError(f"controlled C variant mismatch: {fixture_id}")
            wav = fixtures_root / str(raw["relative_wav_path"])
            if (
                wav.stat().st_size != expected["derived_wav_size_bytes"]
                or sha256_file(wav) != expected["derived_wav_sha256"]
            ):
                raise ValueError(f"C PCM file mismatch: {fixture_id}/{expected['profile']}")
            variants[expected["profile"]] = {**raw, "wav_path": wav}
        if not selected_profiles.issubset(variants):
            raise ValueError(f"C padding profiles mismatch: {fixture_id}")
        items.append({**private, "variants_by_profile": variants})
    return items


def _score(
    item: dict[str, Any], profile: str, metrics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    variant = item["variants_by_profile"][profile]
    hypothesis = str(metrics["hypothesis"])
    reference = normalize_asr(str(item["reference_text"]))
    normalized = normalize_asr(hypothesis)
    latency = float(metrics["latency_ms"])
    duration = float(variant["duration_seconds"])
    common = {
        "review_id": item["review_id"],
        "fixture_id": item["fixture_id"],
        "family": "internal",
        "split": item["split"],
        "category": item["category"],
        "profile": profile,
        "requested_padding_ms_each_side": variant["requested_padding_ms_each_side"],
        "audio_duration_seconds": duration,
        "latency_ms": round(latency, 3),
        "native_inference_ms": float(metrics["native_inference_ms"]),
        "cpu_ms": float(metrics["cpu_ms"]),
        "peak_rss_mib": float(metrics["peak_rss_mib"]),
        "rtf": round(latency / 1000.0 / duration, 6),
        "reference_length": len(reference),
        "hypothesis_length": len(normalized),
        "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
    }
    return {**common, "reference_text": item["reference_text"], "hypothesis": hypothesis}, common


def _summary(selected: list[dict[str, Any]]) -> dict[str, Any]:
    reference_length = sum(int(item["reference_length"]) for item in selected)
    edits = sum(int(item["edit_distance"]) for item in selected)
    return {
        "item_count": len(selected),
        "reference_length": reference_length,
        "edit_distance": edits,
        "cer_percent": round(100.0 * edits / reference_length, 6) if reference_length else None,
        "sentence_correctness_percent": round(
            100.0 * sum(bool(item["sentence_correct"]) for item in selected) / len(selected), 6
        ) if selected else None,
        "latency_ms": numeric_summary([float(item["latency_ms"]) for item in selected]),
        "rtf": numeric_summary([float(item["rtf"]) for item in selected]),
        "peak_rss_mib": max((float(item["peak_rss_mib"]) for item in selected), default=None),
    }


def summarize(
    results: list[dict[str, Any]], profiles_to_score: tuple[str, ...] = PROFILES,
) -> dict[str, Any]:
    profiles = {
        profile: _summary([item for item in results if item["profile"] == profile])
        for profile in profiles_to_score
    }
    categories = {
        profile: {
            category: _summary([
                item for item in results
                if item["profile"] == profile and item["category"] == category
            ])
            for category in sorted({str(item["category"]) for item in results})
        }
        for profile in profiles_to_score
    }
    by_pair = {(item["fixture_id"], item["profile"]): item for item in results}
    paired = {}
    baseline_profile = profiles_to_score[0]
    for profile in profiles_to_score[1:]:
        rows = []
        for fixture_id in sorted({str(item["fixture_id"]) for item in results}):
            baseline, probe = by_pair[(fixture_id, baseline_profile)], by_pair[(fixture_id, profile)]
            rows.append({
                "fixture_id": fixture_id,
                "edit_distance_delta": int(probe["edit_distance"]) - int(baseline["edit_distance"]),
                "sentence_correctness_delta": int(bool(probe["sentence_correct"])) - int(bool(baseline["sentence_correct"])),
                "latency_ms_delta": round(float(probe["latency_ms"]) - float(baseline["latency_ms"]), 3),
                "rtf_delta": round(float(probe["rtf"]) - float(baseline["rtf"]), 6),
            })
        paired[profile] = rows
    split = str(results[0]["split"]) if results else None
    return {"family": "internal", "split": split, "profiles": profiles, "profile_categories": categories, "paired_fixture_delta_from_p0": paired}


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, default=root / "poc_audio/manifests/m2b_c_padding_probe.json")
    parser.add_argument("--tracked-lock", type=Path, default=root / "poc_audio/manifests/m2b_c_pcm_lock.json")
    parser.add_argument("--controlled-lock", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
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
            raise ValueError("padding probe outputs must be new paths outside the repository")
    probe_paths = {
        root / "poc_audio/manifests/m2b_c_padding_probe.json": validate_probe,
        root / "poc_audio/manifests/m2b_c_padding_holdout.json": validate_holdout_probe,
    }
    validator = probe_paths.get(args.probe.resolve())
    if validator is None:
        raise ValueError("padding probe must use the tracked packet")
    probe = load_json(args.probe)
    validator(probe)
    artifact = probe["artifact"]
    if (
        args.model.name != artifact["filename"]
        or args.model.stat().st_size != artifact["size_bytes"]
        or sha256_file(args.model) != artifact["sha256"]
    ):
        raise ValueError("base Q8 artifact identity mismatch")
    if sha256_file(args.binary) != probe["runtime"]["native_worker_sha256"]:
        raise ValueError("native worker identity mismatch")
    target = target_platform()
    assert_target(target)
    assert_network_isolated()
    items = verify_inputs(probe, args.tracked_lock, args.controlled_lock, args.fixtures_root)
    command = [str(args.binary.resolve()), "--model", str(args.model.resolve()), "--threads", "4"]
    worker = NativeWhisperWorker(command, args.work_dir / "worker.stderr.log")
    args.work_dir.mkdir(parents=True)
    owners_before = audio_device_owner_count()
    started = time.monotonic()
    raw_results, sanitized_results = [], []
    error_code = None
    timeout_seconds = float(probe["execution"]["per_item_timeout_seconds"])
    row_budget_seconds = float(probe["execution"]["row_budget_seconds"])
    expected_observations = int(probe["execution"]["scored_observations"])
    profiles_to_score = (
        probe["single_variable"]["baseline"], *probe["single_variable"]["probe_arms"]
    )
    try:
        worker.start()
        orders = probe["execution"]["profile_orders"]
        for index, item in enumerate(items):
            for profile in orders[index % len(orders)]:
                wav = item["variants_by_profile"][profile]["wav_path"]
                worker.transcribe(wav, timeout_seconds)
                metrics = worker.transcribe(wav, timeout_seconds)
                raw, sanitized = _score(item, profile, metrics)
                raw_results.append(raw)
                sanitized_results.append(sanitized)
                if time.monotonic() - started > row_budget_seconds:
                    raise TimeoutError("padding probe row budget exceeded")
    except Exception as error:
        error_code = type(error).__name__
    cleanup = worker.stop()
    assert_network_isolated()
    owners_after = audio_device_owner_count()
    cleanup.update({"threads": 0, "iterators": 0, "streams": 0, "device_owners": owners_after})
    cleanup["clean"] = bool(cleanup["clean"] and owners_before == owners_after == 0)
    complete = len(sanitized_results) == expected_observations and error_code is None and cleanup["clean"]
    base = {
        "schema_version": "1.0",
        "report_id": probe["probe_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "review_status": "UNREVIEWED",
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_REVIEW" if complete else "INCONCLUSIVE_RETAINED",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "candidate_id": probe["candidate_id"],
        "artifact": artifact,
        "runtime": {
            "id": probe["runtime"]["id"],
            "runtime_executable_sha256": sha256_file(args.binary),
            "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
            "threads": 4,
        },
        "fixture_lock": probe["fixture_lock"],
        "method": probe["execution"],
        "scope": probe["scope"],
        "single_variable": probe["single_variable"],
        "load_ms": worker.load_ms,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "summary": summarize(sanitized_results, profiles_to_score) if complete else None,
        "error_code": error_code,
        "cleanup": cleanup,
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_PROBE",
        "security": {"audio_device_opened": False, "speaker_playback": False, "pcm_emitted_to_report": False},
    }
    raw = {**base, "git_safety": "CONTROLLED_TRANSCRIPTS_AND_PATHS_DO_NOT_COMMIT", "runtime_command": command, "results": raw_results}
    sanitized = {**base, "results": sanitized_results, "raw_transcript_emitted": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.sanitized_output.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"C padding probe: {args.sanitized_output} ({base['execution_status']})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
