"""Run the frozen base Q8 domain-prompt probe on C dev fixtures."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from .m2b_c_common_voice_baseline import verify_inputs as verify_common_voice
from .m2b_c_decoder_probe import verify_inputs as verify_internal
from .m2b_c_fixture_lock import load_json, sha256_file
from .m2b_c_padding_probe import _summary
from .m4a_candidate_worker import edit_distance, normalize_asr
from .m4a_runtime_preflight import assert_target, audio_device_owner_count, target_platform
from .m4a_whispercpp_build import assert_network_isolated
from .m4a_whispercpp_qualification import NativeWhisperWorker


PROBE_ID = "M2B-C-BASE-Q8-DOMAIN-PROMPT-001"
HOLDOUT_ID = "M2B-C-BASE-Q8-DOMAIN-PROMPT-HOLDOUT-001"
MODEL_SHA256 = "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"
WORKER_SHA256 = "64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b"
PROMPT = "繁體中文。常用技術詞彙：Wi-Fi、audio frame、音訊基線、候選語音模型、離線執行。"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def validate_probe(probe: dict[str, Any]) -> None:
    if probe.get("probe_id") != PROBE_ID or probe.get("status") != "FROZEN_BEFORE_PROMPT_INFERENCE":
        raise ValueError("prompt probe identity mismatch")
    if probe.get("artifact") != {
        "filename": "ggml-base-q8_0.bin", "size_bytes": 81768585, "sha256": MODEL_SHA256,
    }:
        raise ValueError("prompt probe artifact mismatch")
    runtime = probe.get("runtime", {})
    if (
        runtime.get("source_sha") != "62aac01389d06f7f218db0e45acf3de30b4476af"
        or runtime.get("native_worker_sha256") != WORKER_SHA256
        or runtime.get("build_report_sha256") != "5539acd951a09169f140181264506f4a4cee0035b7f5ad917bdf4c838175dd0c"
        or runtime.get("threads") != 4 or runtime.get("decoder") != "greedy"
        or runtime.get("language") != "zh"
        or any(runtime.get(key) is not False for key in ("context", "timestamps", "internal_vad"))
    ):
        raise ValueError("prompt probe runtime mismatch")
    variable = probe.get("single_variable", {})
    if variable != {
        "name": "initial_prompt", "baseline": None, "probe": PROMPT,
        "probe_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
        "probe_utf8_bytes": len(PROMPT.encode()), "full_test_sentences_included": False,
    }:
        raise ValueError("prompt probe must change only the frozen initial prompt")
    scope = probe.get("scope", {})
    internal, common = scope.get("internal", {}), scope.get("common_voice", {})
    if (
        internal.get("family") != "internal" or internal.get("split") != "dev"
        or internal.get("pcm_profile") != "p0" or internal.get("fixture_ids") != [
            "asr-clear-002", "asr-pause-028", "asr-clear-012", "asr-pause-036",
            "asr-clear-016", "asr-pause-046", "asr-clear-023", "asr-pause-049",
        ]
        or common != {"family": "common_voice", "split": "dev", "review_ids": ["D02", "D05", "N03", "L03"]}
        or scope.get("internal_holdout_execution") != "SEALED"
        or scope.get("common_voice_holdout_execution") != "SEALED"
    ):
        raise ValueError("prompt probe scope mismatch")
    expected_execution = {
        "profile_order": ["domain_prompt", "baseline"], "family_order": ["internal", "common_voice"],
        "warmups_per_item": 1, "scored_inferences_per_item": 1, "scored_observations": 24,
        "per_item_timeout_seconds": 120, "profile_budget_seconds": 1200,
        "network": "isolated_namespace", "audio_capture": False, "audio_playback": False,
    }
    if probe.get("execution") != expected_execution:
        raise ValueError("prompt probe execution controls mismatch")
    if probe.get("domain_terms") != {
        "wifi": "Wi-Fi", "audio_frame": "audio frame", "audio_baseline": "音訊基線",
        "speech_model": "語音模型", "offline_execution": "離線執行",
    } or probe.get("expected_internal_terms") != {
        "asr-clear-012": ["wifi"], "asr-pause-036": ["audio_frame"],
        "asr-clear-023": ["audio_baseline"],
        "asr-pause-049": ["speech_model", "offline_execution"],
    }:
        raise ValueError("prompt probe domain-term set mismatch")
    if probe.get("predecessors") != {
        "internal": {
            "path": "poc_audio/manifests/m2b_c_padding_dev_result.json",
            "sha256": "73132c6dcf8c029105ec3ca298b9f4a5234f6cd625c4992d654d0c2cc9d75c90",
            "profile": "p0",
        },
        "common_voice": {
            "path": "poc_audio/manifests/m2b_c_common_voice_dev_result.json",
            "sha256": "2552595f91f231206933cc5836b73ae3174aca174d442a54712812fd5293d58f",
            "candidate_id": "asr-whispercpp-base-q8_0-1.9.2-m2b",
        },
        "required_baseline_hypothesis_hash_match": True,
    }:
        raise ValueError("prompt probe predecessor identity mismatch")


def validate_holdout_probe(probe: dict[str, Any]) -> None:
    if probe.get("probe_id") != HOLDOUT_ID or probe.get("status") != "FROZEN_BEFORE_PROMPT_HOLDOUT_INFERENCE":
        raise ValueError("prompt holdout identity mismatch")
    authorization = probe.get("dev_authorization")
    if authorization != {
        "result_path": "poc_audio/manifests/m2b_c_base_q8_prompt_dev_result.json",
        "result_sha256": "33e0e875a976c211015f659714d5c2ad7e23ad064a06a34de3d0876d80c44595",
        "evidence_path": "poc_audio/evidence/m2/M2B-C-BASE-Q8-PROMPT-DEV-001.md",
        "disposition": "REVIEWED_ADVANCE_TO_PRE_FROZEN_C_HOLDOUT",
    }:
        raise ValueError("prompt holdout dev authorization mismatch")
    adapted = {
        **probe,
        "probe_id": PROBE_ID,
        "status": "FROZEN_BEFORE_PROMPT_INFERENCE",
        "scope": {
            "internal": {
                "family": "internal", "split": "dev", "pcm_profile": "p0",
                "fixture_ids": [
                    "asr-clear-002", "asr-pause-028", "asr-clear-012", "asr-pause-036",
                    "asr-clear-016", "asr-pause-046", "asr-clear-023", "asr-pause-049",
                ],
            },
            "common_voice": {
                "family": "common_voice", "split": "dev",
                "review_ids": ["D02", "D05", "N03", "L03"],
            },
            "internal_holdout_execution": "SEALED",
            "common_voice_holdout_execution": "SEALED",
        },
        "predecessors": {
            "internal": {
                "path": "poc_audio/manifests/m2b_c_padding_dev_result.json",
                "sha256": "73132c6dcf8c029105ec3ca298b9f4a5234f6cd625c4992d654d0c2cc9d75c90",
                "profile": "p0",
            },
            "common_voice": {
                "path": "poc_audio/manifests/m2b_c_common_voice_dev_result.json",
                "sha256": "2552595f91f231206933cc5836b73ae3174aca174d442a54712812fd5293d58f",
                "candidate_id": "asr-whispercpp-base-q8_0-1.9.2-m2b",
            },
            "required_baseline_hypothesis_hash_match": True,
        },
        "expected_internal_terms": {
            "asr-clear-012": ["wifi"], "asr-pause-036": ["audio_frame"],
            "asr-clear-023": ["audio_baseline"],
            "asr-pause-049": ["speech_model", "offline_execution"],
        },
    }
    adapted.pop("dev_authorization", None)
    validate_probe(adapted)
    scope = probe["scope"]
    if scope != {
        "internal": {
            "family": "internal", "split": "holdout", "pcm_profile": "p0",
            "fixture_ids": [
                "asr-clear-008", "asr-pause-034", "asr-clear-014", "asr-pause-039",
                "asr-clear-017", "asr-clear-022", "asr-clear-024", "asr-clear-025",
            ],
        },
        "common_voice": {
            "family": "common_voice", "split": "holdout",
            "review_ids": ["H02", "H03", "H04", "N06"],
        },
        "dev_execution": "REVIEWED_COMPLETE",
    }:
        raise ValueError("prompt holdout scope mismatch")
    if probe.get("expected_internal_terms") != {
        fixture_id: [] for fixture_id in scope["internal"]["fixture_ids"]
    }:
        raise ValueError("prompt holdout expected-term lock mismatch")


def load_items(
    probe: dict[str, Any], tracked_lock: Path, controlled_lock: Path, fixtures_root: Path,
) -> list[dict[str, Any]]:
    internal_packet = {
        "fixture_lock": probe["fixture_lock"],
        "scope": {"fixture_ids": probe["scope"]["internal"]["fixture_ids"]},
    }
    common_packet = {
        "fixture_lock": probe["fixture_lock"],
        "scope": {"review_ids": probe["scope"]["common_voice"]["review_ids"]},
    }
    internal_split = probe["scope"]["internal"]["split"]
    common_split = probe["scope"]["common_voice"]["split"]
    internal = [
        {**item, "family": "internal", "item_id": item["fixture_id"],
         "split": internal_split, "duration_seconds": item["p0"]["duration_seconds"]}
        for item in verify_internal(
            internal_packet, tracked_lock, controlled_lock, fixtures_root, internal_split
        )
    ]
    common = [
        {**item, "family": "common_voice", "item_id": item["review_id"], "split": common_split}
        for item in verify_common_voice(
            common_packet, tracked_lock, controlled_lock, fixtures_root, common_split
        )
    ]
    return internal + common


def score(
    profile: str, item: dict[str, Any], metrics: dict[str, Any], probe: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    hypothesis = str(metrics["hypothesis"])
    reference, normalized = normalize_asr(str(item["reference_text"])), normalize_asr(hypothesis)
    duration, latency = float(item["duration_seconds"]), float(metrics["latency_ms"])
    term_hits = sorted(
        term_id for term_id, term in probe["domain_terms"].items()
        if normalize_asr(str(term)) in normalized
    )
    expected = probe["expected_internal_terms"].get(item["fixture_id"], []) \
        if item["family"] == "internal" else []
    common = {
        "profile": profile, "family": item["family"], "split": item["split"],
        "item_id": item["item_id"], "fixture_id": item["fixture_id"],
        "category": item["category"], "audio_duration_seconds": duration,
        "latency_ms": round(latency, 3), "native_inference_ms": float(metrics["native_inference_ms"]),
        "cpu_ms": float(metrics["cpu_ms"]), "peak_rss_mib": float(metrics["peak_rss_mib"]),
        "rtf": round(latency / 1000.0 / duration, 6), "reference_length": len(reference),
        "hypothesis_length": len(normalized), "edit_distance": edit_distance(reference, normalized),
        "sentence_correct": reference == normalized,
        "domain_term_hits": term_hits, "expected_domain_terms": expected,
        "expected_domain_term_hits": sorted(set(expected).intersection(term_hits)),
        "unexpected_domain_term_hits": sorted(set(term_hits).difference(expected)),
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
    }
    return {**common, "reference_text": item["reference_text"], "hypothesis": hypothesis}, common


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for profile in ("baseline", "domain_prompt"):
        selected = [item for item in results if item["profile"] == profile]
        profiles[profile] = {
            family: {
                **_summary([item for item in selected if item["family"] == family]),
                "expected_domain_term_hits": sum(
                    len(item["expected_domain_term_hits"]) for item in selected if item["family"] == family
                ),
                "unexpected_domain_term_hits": sum(
                    len(item["unexpected_domain_term_hits"]) for item in selected if item["family"] == family
                ),
            }
            for family in ("internal", "common_voice")
        }
    pairs = {(item["item_id"], item["profile"]): item for item in results}
    paired = []
    for item_id in sorted({str(item["item_id"]) for item in results}):
        baseline, prompt = pairs[(item_id, "baseline")], pairs[(item_id, "domain_prompt")]
        paired.append({
            "item_id": item_id, "family": baseline["family"], "category": baseline["category"],
            "edit_distance_delta_prompt_minus_baseline": prompt["edit_distance"] - baseline["edit_distance"],
            "sentence_correctness_delta_prompt_minus_baseline":
                int(prompt["sentence_correct"]) - int(baseline["sentence_correct"]),
            "expected_domain_term_hit_delta_prompt_minus_baseline":
                len(prompt["expected_domain_term_hits"]) - len(baseline["expected_domain_term_hits"]),
            "unexpected_domain_term_hit_delta_prompt_minus_baseline":
                len(prompt["unexpected_domain_term_hits"]) - len(baseline["unexpected_domain_term_hits"]),
            "latency_ms_delta_prompt_minus_baseline": round(prompt["latency_ms"] - baseline["latency_ms"], 3),
        })
    return {"profiles": profiles, "paired_profile_delta": paired}


def predecessor_match(probe: dict[str, Any], results: list[dict[str, Any]], root: Path) -> bool:
    expected: dict[str, str] = {}
    for family, identity in probe["predecessors"].items():
        if family == "required_baseline_hypothesis_hash_match":
            continue
        path = root / identity["path"]
        if sha256_file(path) != identity["sha256"]:
            raise ValueError(f"prompt predecessor checksum mismatch: {family}")
        previous = load_json(path)
        if family == "internal":
            selected = [item for item in previous["results"] if item.get("profile") == identity["profile"]]
            expected.update({item["fixture_id"]: item["hypothesis_sha256"] for item in selected})
        else:
            selected = [item for item in previous["results"] if item.get("candidate_id") == identity["candidate_id"]]
            expected.update({item["review_id"]: item["hypothesis_sha256"] for item in selected})
    observed = {
        item["item_id"]: item["hypothesis_sha256"]
        for item in results if item["profile"] == "baseline"
    }
    return observed == expected


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, default=root / "poc_audio/manifests/m2b_c_base_q8_prompt_probe.json")
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
    args, root = parse_args(), repo_root().resolve()
    for path in (args.work_dir, args.output, args.sanitized_output):
        if path.exists() or path.resolve().is_relative_to(root):
            raise ValueError("prompt probe outputs must be new and outside Git")
    validators = {
        root / "poc_audio/manifests/m2b_c_base_q8_prompt_probe.json": validate_probe,
        root / "poc_audio/manifests/m2b_c_base_q8_prompt_holdout.json": validate_holdout_probe,
    }
    validator = validators.get(args.probe.resolve())
    if validator is None:
        raise ValueError("prompt probe must use the tracked packet")
    probe = load_json(args.probe)
    validator(probe)
    if probe["probe_id"] == HOLDOUT_ID:
        authorization = probe["dev_authorization"]
        if sha256_file(root / authorization["result_path"]) != authorization["result_sha256"]:
            raise ValueError("prompt holdout tracked dev result mismatch")
    artifact = probe["artifact"]
    if args.model.name != artifact["filename"] or args.model.stat().st_size != artifact["size_bytes"] \
            or sha256_file(args.model) != artifact["sha256"]:
        raise ValueError("prompt probe model mismatch")
    if sha256_file(args.binary) != WORKER_SHA256 \
            or sha256_file(args.build_report) != probe["runtime"]["build_report_sha256"]:
        raise ValueError("prompt probe runtime closure mismatch")
    assert_target(target_platform())
    assert_network_isolated()
    items = load_items(probe, args.tracked_lock, args.controlled_lock, args.fixtures_root)
    args.work_dir.mkdir(parents=True)
    raw_results: list[dict[str, Any]] = []
    sanitized_results: list[dict[str, Any]] = []
    runtimes: dict[str, Any] = {}
    cleanups: dict[str, Any] = {}
    error_code = None
    started = time.monotonic()
    try:
        for profile in probe["execution"]["profile_order"]:
            command = [str(args.binary.resolve()), "--model", str(args.model.resolve()), "--threads", "4"]
            if profile == "domain_prompt":
                command += ["--initial-prompt", PROMPT]
            worker = NativeWhisperWorker(command, args.work_dir / f"{profile}.stderr.log")
            owners_before, profile_started = audio_device_owner_count(), time.monotonic()
            try:
                worker.start()
                for item in items:
                    timeout = float(probe["execution"]["per_item_timeout_seconds"])
                    worker.transcribe(item["wav_path"], timeout)
                    metrics = worker.transcribe(item["wav_path"], timeout)
                    raw, sanitized = score(profile, item, metrics, probe)
                    raw_results.append(raw)
                    sanitized_results.append(sanitized)
                    if time.monotonic() - profile_started > probe["execution"]["profile_budget_seconds"]:
                        raise TimeoutError("prompt profile budget exceeded")
            finally:
                cleanup = worker.stop()
            owners_after = audio_device_owner_count()
            cleanup.update({"threads": 0, "iterators": 0, "streams": 0, "device_owners": owners_after})
            cleanup["clean"] = bool(cleanup["clean"] and owners_before == owners_after == 0)
            cleanups[profile] = cleanup
            runtimes[profile] = {
                "load_ms": worker.load_ms,
                "command_sha256": hashlib.sha256(json.dumps(command, ensure_ascii=False).encode()).hexdigest(),
                "runtime_executable_sha256": sha256_file(args.binary),
                "initial_prompt_sha256": hashlib.sha256((PROMPT if profile == "domain_prompt" else "").encode()).hexdigest(),
            }
    except Exception as error:
        error_code = type(error).__name__
    assert_network_isolated()
    is_holdout = probe["probe_id"] == HOLDOUT_ID
    baseline_matches = (
        None if is_holdout else
        predecessor_match(probe, sanitized_results, root) if len(sanitized_results) == 24 else False
    )
    if error_code is None and baseline_matches is False:
        error_code = "BASELINE_PREDECESSOR_MISMATCH"
    complete = len(sanitized_results) == 24 and error_code is None \
        and len(cleanups) == 2 and all(item["clean"] for item in cleanups.values())
    base = {
        "schema_version": "1.0", "report_id": probe["probe_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(), "review_status": "UNREVIEWED",
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_REVIEW" if complete else "INCONCLUSIVE_RETAINED",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "candidate_id": probe["candidate_id"], "artifact": artifact, "runtime": runtimes,
        "fixture_lock": probe["fixture_lock"], "scope": probe["scope"],
        "single_variable": {**probe["single_variable"], "probe": None},
        "method": probe["execution"], "baseline_predecessor_hypothesis_hash_match": baseline_matches,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "summary": summarize(sanitized_results) if len(sanitized_results) == 24 else None,
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
    print(f"Base Q8 prompt probe: {args.sanitized_output} ({base['execution_status']})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
