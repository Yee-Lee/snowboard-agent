"""Build the sanitized M2A A/B split packet from immutable formal reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


PACKET_ID = "M4A-M2A-AB-SPLIT-001"
SMALL_ID = "asr-whispercpp-small-q8_0-1.9.2"
BASE_ID = "asr-whispercpp-base-q8_0-1.9.2-m2b"
FAMILY_GROUP = {"internal": "A", "common_voice": "B"}
SOURCE_RULES = {
    SMALL_ID: {
        "sha256": "610bcce6949a0f5728c2f6a307bd17acf4968ccf3018f9009e235ad8da6e465a",
        "poc_source_sha": "629784f09f0700e7653cee4789cab8caf6d760a3",
        "artifact_sha256": "49c8fb02b65e6049d5fa6c04f81f53b867b5ec9540406812c643f177317f779f",
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_COMPARATIVE_REVIEW",
    },
    BASE_ID: {
        "sha256": "bb6cacc53d09c26f3bcb5d832dd374b155e3696ef5c9c6daa035d0a6cfcb81eb",
        "poc_source_sha": "f41a3cde6cc5d362579aae90e642356f8cbfc721",
        "artifact_sha256": "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9",
        "execution_status": "M2B_PROBE_OBSERVATIONS_COMPLETE_PENDING_DELTA_REVIEW",
    },
}
REQUIRED_RESULT_KEYS = {
    "fixture_id", "family", "category", "reference_length", "hypothesis_length",
    "edit_distance", "sentence_correct", "latency_ms", "rtf", "peak_rss_mib",
    "hypothesis_sha256",
}
FORBIDDEN_KEYS = {
    "hypothesis", "reference", "reference_text", "relative_wav_path", "wav_path",
    "controlled_path", "runtime_command",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_sanitized(value: Any) -> None:
    if isinstance(value, dict):
        leaked = FORBIDDEN_KEYS.intersection(value)
        if leaked:
            raise ValueError(f"source contains controlled keys: {sorted(leaked)}")
        for child in value.values():
            assert_sanitized(child)
    elif isinstance(value, list):
        for child in value:
            assert_sanitized(child)


def load_source(path: Path, candidate_id: str) -> dict[str, Any]:
    rules = SOURCE_RULES[candidate_id]
    if sha256_file(path) != rules["sha256"]:
        raise ValueError(f"{candidate_id} formal report checksum mismatch")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert_sanitized(document)
    if document.get("candidate_id") != candidate_id:
        raise ValueError("formal candidate identity mismatch")
    if document.get("poc_source_sha") != rules["poc_source_sha"]:
        raise ValueError("formal source SHA mismatch")
    if document.get("artifact", {}).get("sha256") != rules["artifact_sha256"]:
        raise ValueError("formal artifact checksum mismatch")
    if document.get("execution_status") != rules["execution_status"]:
        raise ValueError("formal report status mismatch")
    if document.get("raw_transcript_emitted") is not False:
        raise ValueError("formal report is not sanitized")
    if document.get("cleanup", {}).get("clean") is not True:
        raise ValueError("formal report cleanup is not clean")
    security = document.get("security", {})
    if any(security.get(key) is not False for key in (
        "audio_device_opened", "pcm_emitted_to_report", "speaker_playback",
    )):
        raise ValueError("formal report security boundary is incomplete")
    results = document.get("results")
    if not isinstance(results, list) or len(results) != 20:
        raise ValueError("formal report must contain exactly 20 results")
    if {item.get("family") for item in results} != set(FAMILY_GROUP):
        raise ValueError("formal report A/B families are incomplete")
    if sum(item.get("family") == "internal" for item in results) != 8:
        raise ValueError("formal report must contain exactly eight A items")
    if sum(item.get("family") == "common_voice" for item in results) != 12:
        raise ValueError("formal report must contain exactly twelve B items")
    fixture_ids: set[str] = set()
    for item in results:
        if not REQUIRED_RESULT_KEYS.issubset(item):
            raise ValueError("formal result is missing required sanitized fields")
        if item["fixture_id"] in fixture_ids:
            raise ValueError("formal report contains duplicate fixtures")
        fixture_ids.add(item["fixture_id"])
    return document


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 6)


def metric_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    edits = sum(int(item["edit_distance"]) for item in records)
    reference = sum(int(item["reference_length"]) for item in records)
    correct = sum(bool(item["sentence_correct"]) for item in records)
    latencies = [float(item["latency_ms"]) for item in records]
    rtfs = [float(item["rtf"]) for item in records]
    return {
        "item_count": len(records),
        "correct_count": correct,
        "sentence_correctness_percent": round(100.0 * correct / len(records), 6),
        "edit_distance_total": edits,
        "reference_length_total": reference,
        "cer_percent": round(100.0 * edits / reference, 6),
        "latency_ms": {
            "min": round(min(latencies), 6), "p50": nearest_rank(latencies, 0.50),
            "p95": nearest_rank(latencies, 0.95), "max": round(max(latencies), 6),
        },
        "rtf": {
            "min": round(min(rtfs), 6), "p50": nearest_rank(rtfs, 0.50),
            "p95": nearest_rank(rtfs, 0.95), "max": round(max(rtfs), 6),
        },
        "peak_rss_mib": round(max(float(item["peak_rss_mib"]) for item in records), 6),
    }


def paired_summary(records_by_candidate: dict[str, list[dict[str, Any]]], family: str) -> dict[str, int]:
    indexed = {
        candidate_id: {
            item["fixture_id"]: bool(item["sentence_correct"])
            for item in records if item["family"] == family
        }
        for candidate_id, records in records_by_candidate.items()
    }
    fixture_ids = set(indexed[SMALL_ID])
    if fixture_ids != set(indexed[BASE_ID]):
        raise ValueError("paired fixture identities differ")
    counts = {"both_correct": 0, "small_only_correct": 0, "base_only_correct": 0, "both_wrong": 0}
    for fixture_id in sorted(fixture_ids):
        small = indexed[SMALL_ID][fixture_id]
        base = indexed[BASE_ID][fixture_id]
        key = (
            "both_correct" if small and base else
            "small_only_correct" if small else
            "base_only_correct" if base else "both_wrong"
        )
        counts[key] += 1
    return counts


def build_packets(sources: dict[str, tuple[str, dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any]]:
    documents = {candidate_id: document for candidate_id, (_, document) in sources.items()}
    first = documents[SMALL_ID]
    if any(
        document.get("fixture_lock_sha256") != first.get("fixture_lock_sha256")
        or document.get("controlled_manifest_sha256") != first.get("controlled_manifest_sha256")
        for document in documents.values()
    ):
        raise ValueError("formal reports do not share one fixture lock")
    identity = {
        candidate_id: {
            item["fixture_id"]: (item["family"], item["category"], item["reference_length"])
            for item in document["results"]
        }
        for candidate_id, document in documents.items()
    }
    if identity[SMALL_ID] != identity[BASE_ID]:
        raise ValueError("formal reports do not share exact fixture identities")

    source_reports = [
        {
            "candidate_id": candidate_id,
            "formal_row_sha256": source_sha256,
            "poc_source_sha": document["poc_source_sha"],
            "artifact": document["artifact"],
        }
        for candidate_id, (source_sha256, document) in sources.items()
    ]
    records: list[dict[str, Any]] = []
    records_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for candidate_id, (source_sha256, document) in sources.items():
        candidate_records = []
        for item in document["results"]:
            record = {
                key: item[key] for key in (
                    "fixture_id", "family", "category", "reference_length",
                    "hypothesis_length", "edit_distance", "sentence_correct", "latency_ms",
                    "rtf", "peak_rss_mib", "hypothesis_sha256",
                )
            }
            record.update({
                "candidate_id": candidate_id,
                "fixture_group": FAMILY_GROUP[item["family"]],
                "formal_row_sha256": source_sha256,
            })
            records.append(record)
            candidate_records.append(record)
        records_by_candidate[candidate_id] = candidate_records

    items = {
        "schema_version": "1.0", "packet_id": PACKET_ID,
        "record_count": len(records),
        "fixture_lock_sha256": first["fixture_lock_sha256"],
        "controlled_manifest_sha256": first["controlled_manifest_sha256"],
        "source_reports": source_reports,
        "records": records,
        "security": {"reference_text_included": False, "hypothesis_text_included": False, "pcm_included": False},
    }
    candidates: dict[str, Any] = {}
    for candidate_id, candidate_records in records_by_candidate.items():
        groups = {
            "A": metric_summary([item for item in candidate_records if item["fixture_group"] == "A"]),
            "B": metric_summary([item for item in candidate_records if item["fixture_group"] == "B"]),
            "A_plus_B": metric_summary(candidate_records),
        }
        groups["A_vs_B_delta"] = {
            "sentence_gap_b_minus_a_percentage_points": round(
                groups["B"]["sentence_correctness_percent"] - groups["A"]["sentence_correctness_percent"], 6,
            ),
            "cer_improvement_a_minus_b_percentage_points": round(
                groups["A"]["cer_percent"] - groups["B"]["cer_percent"], 6,
            ),
        }
        groups["A_categories"] = {
            category: metric_summary([item for item in candidate_records if item["category"] == category])
            for category in sorted({item["category"] for item in candidate_records if item["fixture_group"] == "A"})
        }
        candidates[candidate_id] = groups
    summary = {
        "schema_version": "1.0", "packet_id": PACKET_ID,
        "method": "RECOMPUTED_FROM_IMMUTABLE_SANITIZED_FORMAL_ROWS_NO_NEW_INFERENCE",
        "group_definition": {"A": "internal recordings (8)", "B": "Common Voice 26.0 zh-TW (12)"},
        "fixture_lock_sha256": first["fixture_lock_sha256"],
        "controlled_manifest_sha256": first["controlled_manifest_sha256"],
        "source_reports": source_reports,
        "candidates": candidates,
        "paired_sentence_outcomes": {
            "A": paired_summary(records_by_candidate, "internal"),
            "B": paired_summary(records_by_candidate, "common_voice"),
        },
        "unavailable_observations": {
            "insertion_deletion_substitution_totals": "NOT_AVAILABLE_IN_SANITIZED_FORMAL_ROWS",
            "signal_features": "NOT_COMPUTED_NO_FROZEN_SIGNAL_DEFINITION_IN_HANDOFF",
        },
        "reproduction_command": (
            "PYTHONPATH=poc_audio/src python3 -m audio_poc.m2a_ab_split "
            "--small-q8-report <small-q8-sanitized-report> "
            "--base-q8-report <base-q8-sanitized-report> --output-dir <new-output-dir>"
        ),
        "interpretation_boundary": (
            "A/B are different corpora and speakers; grouped observations do not establish recording-quality causation"
        ),
    }
    assert_sanitized(items)
    assert_sanitized(summary)
    return items, summary


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small-q8-report", type=Path, required=True)
    parser.add_argument("--base-q8-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise ValueError("output directory must be a new path")
    sources = {}
    for candidate_id, path in ((SMALL_ID, args.small_q8_report), (BASE_ID, args.base_q8_report)):
        document = load_source(path, candidate_id)
        sources[candidate_id] = (sha256_file(path), document)
    items, summary = build_packets(sources)
    args.output_dir.mkdir(parents=True)
    write_json(args.output_dir / "items.sanitized.json", items)
    write_json(args.output_dir / "summary.json", summary)
    print(f"M2A A/B split packet: {args.output_dir} ({items['record_count']} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
