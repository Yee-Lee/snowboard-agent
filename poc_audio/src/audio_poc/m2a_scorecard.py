"""Assemble sanitized formal M2A rows into one observation-only scorecard."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m2a_survey import expected_wheel_packages
from .m4a_m2a_packet import load_json, repo_root, sha256_file, validate_packet


REPORT_ID = "M4A-M2A-COMPARATIVE-SCORECARD-001"
FORMAL_STATUS = "OBSERVATIONS_COMPLETE_PENDING_COMPARATIVE_REVIEW"
FORBIDDEN_KEYS = {
    "hypothesis", "reference_text", "relative_wav_path", "runtime_command", "wav_path",
}


def assert_sanitized(value: Any) -> None:
    if isinstance(value, dict):
        leaked = FORBIDDEN_KEYS.intersection(value)
        if leaked:
            raise ValueError(f"report contains controlled keys: {sorted(leaked)}")
        for child in value.values():
            assert_sanitized(child)
    elif isinstance(value, list):
        for child in value:
            assert_sanitized(child)


def validate_formal_row(
    document: dict[str, Any], candidate: dict[str, Any], runtime: dict[str, Any],
) -> None:
    assert_sanitized(document)
    if document.get("execution_status") != FORMAL_STATUS:
        raise ValueError("diagnostic or inconclusive report cannot enter the scorecard")
    if document.get("candidate_id") != candidate["candidate_id"]:
        raise ValueError("candidate identity mismatch")
    if document.get("artifact", {}).get("sha256") != candidate["artifact"]["sha256"]:
        raise ValueError("candidate artifact mismatch")
    if document.get("method", {}).get("fixture_count") != 20 or len(document.get("results", [])) != 20:
        raise ValueError("formal row does not contain the exact 20 observations")
    if document.get("raw_transcript_emitted") is not False:
        raise ValueError("scorecard input is not explicitly sanitized")
    if document.get("cleanup", {}).get("clean") is not True:
        raise ValueError("formal row cleanup is not clean")
    security = document.get("security", {})
    if any(security.get(key) is not False for key in (
        "audio_device_opened", "speaker_playback", "pcm_emitted_to_report",
    )):
        raise ValueError("formal row audio security evidence is incomplete")
    if runtime.get("runtime_artifacts") and runtime["engine"] != "whisper.cpp":
        expected = {"packages": expected_wheel_packages(runtime)}
        if document.get("runtime", {}).get("loaded_identity") != expected:
            raise ValueError("formal row loaded runtime identity mismatch")


def scorecard_row(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    summary = document["summary"]
    return {
        "candidate_id": document["candidate_id"],
        "poc_source_sha": document["poc_source_sha"],
        "artifact": document["artifact"],
        "runtime_loaded_identity": document["runtime"]["loaded_identity"],
        "overall_cer_percent": summary["overall_cer_percent"],
        "overall_sentence_correctness_percent": summary["overall_sentence_correctness_percent"],
        "latency_ms": summary["latency_ms"],
        "rtf": summary["rtf"],
        "peak_rss_mib": summary["peak_rss_mib"],
        "categories": summary["categories"],
        "cleanup": document["cleanup"],
        "sanitized_report_sha256": sha256_file(path),
    }


def assemble(report_paths: list[Path], omitted_optional: dict[str, str]) -> dict[str, Any]:
    root = repo_root()
    packet = load_json(root / "poc_audio/manifests/m4a_m2a_common_packet.json")
    validate_packet(packet)
    candidates = {row["candidate_id"]: row for row in packet["candidate_rows"]}
    documents: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in report_paths:
        document = load_json(path)
        candidate_id = document.get("candidate_id")
        if candidate_id not in candidates or candidate_id in documents:
            raise ValueError("unknown or duplicate candidate report")
        candidate = candidates[candidate_id]
        runtime = packet["runtime_identities"][candidate["runtime_id"]]
        validate_formal_row(document, candidate, runtime)
        documents[candidate_id] = (path, document)
    required = {row["candidate_id"] for row in packet["candidate_rows"] if row["required"]}
    if set(documents) != required:
        raise ValueError(f"formal report set mismatch: expected {sorted(required)}")
    optional = {row["candidate_id"] for row in packet["candidate_rows"] if not row["required"]}
    if set(omitted_optional) != optional or any(not reason.strip() for reason in omitted_optional.values()):
        raise ValueError("every optional row needs one non-empty omission reason")
    ordered = [
        scorecard_row(*documents[row["candidate_id"]])
        for row in packet["candidate_rows"] if row["candidate_id"] in documents
    ]
    first = documents[next(iter(documents))][1]
    if any(
        document["fixture_lock_sha256"] != first["fixture_lock_sha256"]
        or document["controlled_manifest_sha256"] != first["controlled_manifest_sha256"]
        for _, document in documents.values()
    ):
        raise ValueError("formal reports do not share one fixture lock")
    return {
        "schema_version": "1.0", "report_id": REPORT_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(), "review_status": "UNREVIEWED",
        "disposition": "OBSERVATIONS_ONLY_PENDING_SHORTLIST_REVIEW",
        "fixture_lock_sha256": first["fixture_lock_sha256"],
        "controlled_manifest_sha256": first["controlled_manifest_sha256"],
        "rows": ordered,
        "omitted_optional": [
            {"candidate_id": candidate_id, "reason": omitted_optional[candidate_id]}
            for candidate_id in sorted(omitted_optional)
        ],
        "shortlist": [],
        "security": {"controlled_transcripts_included": False, "raw_audio_included": False},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, required=True)
    parser.add_argument("--omit-optional", action="append", default=[], metavar="CANDIDATE=REASON")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    omissions: dict[str, str] = {}
    for item in args.omit_optional:
        candidate_id, separator, reason = item.partition("=")
        if not separator or candidate_id in omissions:
            raise ValueError("optional omission must be unique CANDIDATE=REASON")
        omissions[candidate_id] = reason
    document = assemble(args.report, omissions)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M2A scorecard: {args.output} ({document['disposition']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
