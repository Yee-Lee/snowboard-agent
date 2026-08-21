"""Validate the M2A packet and lock pre-output fixture identities."""

from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import json
import re
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


PACKET_ID = "M4A-M2A-COMMON-PACKET-001"
COMMON_VOICE_SOURCE_LOCK_ID = "M4A-M2A-COMMON-VOICE-SOURCE-LOCK-001"
INTERNAL_SOURCE_LOCK_ID = "M4A-M2A-INTERNAL-SOURCE-LOCK-001"
AUTHORITY = "DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003"
PLAN_SHA256 = "d197078d78ad422e1ec6465aea36472adcc4e77c24827c426a03dcbc4b4ba920"
LABEL_INDEX_SHA256 = "85d8579387b7478b864c5dd63ad558c98316a2cb6e96dacb2bdf27498f62ed74"
COMMON_VOICE_DATASET_ID = "cmqinooq000x0nr07b4p4ct4q"
COMMON_VOICE_COUNT = 12
MAX_COMMON_VOICE_TSV_BYTES = 512 * 1024 * 1024
MAX_COMMON_VOICE_CLIP_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}")

EXPECTED_CANDIDATES = (
    "asr-whispercpp-small-q8_0-1.9.2",
    "asr-whispercpp-small-q5_1-1.9.2",
    "asr-whispercpp-base-q5_1-1.9.2",
    "asr-whispercpp-medium-q5_0-1.9.2",
    "asr-whispercpp-large-v3-turbo-q5_0-1.9.2",
    "asr-sherpa-streaming-zipformer-bilingual-zh-en-int8-2023-02-20",
    "asr-vosk-small-cn-0.22",
    "asr-sherpa-qwen3-asr-0.6b-int8-2026-03-25",
)

GROUP_CATEGORIES = {
    "taiwan_mandarin": frozenset({"taiwan_mandarin"}),
    "code_switch": frozenset({"code_switch"}),
    "number_or_date": frozenset({"number", "date"}),
    "product_term": frozenset({"product_term"}),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return document


def validate_packet(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0":
        raise ValueError("M2A packet schema_version must be 1.0")
    if document.get("packet_id") != PACKET_ID or document.get("authority") != AUTHORITY:
        raise ValueError("M2A packet identity or authority mismatch")
    if document.get("status") not in {"PREPARED_FIXTURE_LOCK_PENDING", "LOCKED_NOT_EXECUTED"}:
        raise ValueError("M2A packet has an invalid status")

    runtimes = document.get("runtime_identities")
    if not isinstance(runtimes, dict) or len(runtimes) < 3:
        raise ValueError("M2A packet must pin all runtime families")
    rows = document.get("candidate_rows")
    if not isinstance(rows, list):
        raise ValueError("M2A candidate_rows must be an array")
    candidate_ids = tuple(row.get("candidate_id") for row in rows if isinstance(row, dict))
    if candidate_ids != EXPECTED_CANDIDATES:
        raise ValueError("M2A candidate rows or order differ from ACK-003")

    for row in rows:
        runtime_id = row.get("runtime_id")
        if runtime_id not in runtimes:
            raise ValueError(f"unknown runtime_id for {row.get('candidate_id')}")
        artifact = row.get("artifact")
        if not isinstance(artifact, dict):
            raise ValueError(f"missing artifact for {row.get('candidate_id')}")
        if not isinstance(artifact.get("size_bytes"), int) or artifact["size_bytes"] <= 0:
            raise ValueError(f"invalid artifact size for {row.get('candidate_id')}")
        if not SHA256_RE.fullmatch(str(artifact.get("sha256", ""))):
            raise ValueError(f"invalid artifact SHA-256 for {row.get('candidate_id')}")
        locator = str(artifact.get("controlled_locator", ""))
        if not locator.startswith("controlled://audio-poc/m2a/") or ".." in locator:
            raise ValueError(f"unsafe controlled locator for {row.get('candidate_id')}")
        for field in ("filename", "source_url", "immutable_revision", "license"):
            if not str(artifact.get(field, "")).strip():
                raise ValueError(f"missing artifact {field} for {row.get('candidate_id')}")

    fixture_lock = document.get("fixture_lock", {})
    internal = fixture_lock.get("internal", {})
    external = fixture_lock.get("external", {})
    if internal.get("recording_plan_sha256") != PLAN_SHA256:
        raise ValueError("M2A recording plan identity mismatch")
    if internal.get("vad_label_index_sha256") != LABEL_INDEX_SHA256:
        raise ValueError("M2A VAD label identity mismatch")
    if internal.get("selection_count") != 8 or internal.get("group_counts") != {
        "taiwan_mandarin": 2,
        "code_switch": 2,
        "number_or_date": 2,
        "product_term": 2,
    }:
        raise ValueError("M2A internal fixture allocation mismatch")
    if external.get("dataset_id") != COMMON_VOICE_DATASET_ID:
        raise ValueError("M2A Common Voice dataset identity mismatch")
    if external.get("locale") != "zh-TW" or external.get("license") != "CC0-1.0":
        raise ValueError("M2A Common Voice locale or license mismatch")
    if external.get("selection_count") != COMMON_VOICE_COUNT:
        raise ValueError("M2A Common Voice selection count mismatch")

    budget = document.get("execution_budget", {}).get("standard_rows", {})
    if budget.get("warmups_per_item") != 1 or budget.get("scored_inferences_per_item") != 1:
        raise ValueError("M2A must use one warm-up and one scored inference per item")
    if budget.get("repetitions") != 1 or budget.get("cold_matrix") is not False:
        raise ValueError("M2A packet cannot enable repetitions or a cold matrix")
    disposition = document.get("disposition_policy", {})
    if disposition.get("quality_performance_thresholds_are_elimination_gates") is not False:
        raise ValueError("M2A quality/performance thresholds cannot be elimination gates")
    if set(disposition.get("prohibited_labels", [])) != {"PASS", "FAIL", "WINNER", "PRODUCTION_BASELINE"}:
        raise ValueError("M2A prohibited disposition labels mismatch")


def validate_common_voice_source_lock(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0":
        raise ValueError("Common Voice source lock schema_version must be 1.0")
    if document.get("index_id") != COMMON_VOICE_SOURCE_LOCK_ID:
        raise ValueError("Common Voice source lock identity mismatch")
    if document.get("status") != "SOURCE_CLIPS_LOCKED_DERIVED_PCM_PENDING":
        raise ValueError("Common Voice source lock status mismatch")
    dataset = document.get("dataset", {})
    if (
        dataset.get("dataset_id") != COMMON_VOICE_DATASET_ID
        or dataset.get("release") != "26.0"
        or dataset.get("locale") != "zh-TW"
        or dataset.get("license") != "CC0-1.0"
    ):
        raise ValueError("Common Voice source lock dataset identity mismatch")
    archive = document.get("source_archive", {})
    if not str(archive.get("filename", "")).endswith(".tar.gz"):
        raise ValueError("Common Voice source archive filename mismatch")
    if not isinstance(archive.get("size_bytes"), int) or archive["size_bytes"] <= 0:
        raise ValueError("Common Voice source archive size is invalid")
    if archive.get("sha256") is not None and not SHA256_RE.fullmatch(str(archive["sha256"])):
        raise ValueError("Common Voice source archive SHA-256 is invalid")
    selection = document.get("selection", {})
    records = selection.get("records")
    if selection.get("count") != COMMON_VOICE_COUNT or not isinstance(records, list):
        raise ValueError("Common Voice source lock must contain twelve records")
    if len(records) != COMMON_VOICE_COUNT:
        raise ValueError("Common Voice source lock record count mismatch")
    clip_ids: set[str] = set()
    ranks: list[str] = []
    total_size = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid Common Voice source-lock record")
        if any(key in record for key in ("sentence", "reference_text", "transcript")):
            raise ValueError("tracked Common Voice source lock cannot contain transcript text")
        clip_id = str(record.get("clip_id", ""))
        if not clip_id or clip_id in clip_ids or "/" in clip_id or "\\" in clip_id:
            raise ValueError("invalid or duplicate Common Voice source-lock clip ID")
        member_path = _safe_archive_member(str(record.get("archive_member_path", "")))
        if member_path.name != clip_id or member_path.parts[-3:-1] != ("zh-TW", "clips"):
            raise ValueError(f"Common Voice archive member mismatch: {clip_id}")
        rank = str(record.get("selection_rank_sha256", ""))
        if not SHA256_RE.fullmatch(rank):
            raise ValueError(f"invalid Common Voice selection rank: {clip_id}")
        for field in ("reference_sha256", "source_mp3_sha256"):
            if not SHA256_RE.fullmatch(str(record.get(field, ""))):
                raise ValueError(f"invalid Common Voice {field}: {clip_id}")
        size = record.get("source_mp3_size_bytes")
        if not isinstance(size, int) or not 0 < size <= MAX_COMMON_VOICE_CLIP_BYTES:
            raise ValueError(f"invalid Common Voice clip size: {clip_id}")
        clip_ids.add(clip_id)
        ranks.append(rank)
        total_size += size
    if ranks != sorted(ranks) or len(set(ranks)) != COMMON_VOICE_COUNT:
        raise ValueError("Common Voice source-lock selection ranks are not strictly ordered")
    local = document.get("local_controlled_copy", {})
    if local.get("file_count") != COMMON_VOICE_COUNT or local.get("total_size_bytes") != total_size:
        raise ValueError("Common Voice local controlled-copy summary mismatch")
    controlled_path = PurePosixPath(str(local.get("controlled_selection_relative_path", "")))
    if controlled_path.is_absolute() or ".." in controlled_path.parts:
        raise ValueError("Common Voice controlled-selection path is unsafe")
    if not isinstance(local.get("controlled_selection_size_bytes"), int) or local[
        "controlled_selection_size_bytes"
    ] <= 0:
        raise ValueError("Common Voice controlled-selection size is invalid")
    if not SHA256_RE.fullmatch(str(local.get("controlled_selection_sha256", ""))):
        raise ValueError("Common Voice controlled-selection SHA-256 is invalid")
    handoff = document.get("handoff", {})
    if handoff.get("per_clip_sha256_is_authoritative") is not True:
        raise ValueError("Common Voice handoff must make per-clip SHA-256 authoritative")
    if handoff.get("transcript_in_tracked_index") is not False:
        raise ValueError("Common Voice tracked handoff cannot contain transcripts")


def validate_internal_source_lock(document: dict[str, Any]) -> None:
    if document.get("schema_version") != "1.0" or document.get("index_id") != INTERNAL_SOURCE_LOCK_ID:
        raise ValueError("M2A internal source lock identity mismatch")
    if document.get("status") != "SOURCE_CLIPS_LOCKED_DERIVED_PCM_PENDING":
        raise ValueError("M2A internal source lock status mismatch")
    identities = document.get("source_identities", {})
    if identities.get("recording_plan_sha256") != PLAN_SHA256:
        raise ValueError("M2A internal source lock recording-plan mismatch")
    if identities.get("vad_label_index_sha256") != LABEL_INDEX_SHA256:
        raise ValueError("M2A internal source lock VAD-label mismatch")
    if identities.get("delivered_fixture_manifest_sha256") != (
        "1b33569bbc1f755771c359b2bba4284e72e71a8d836917db9aa8be63ffe530a2"
    ):
        raise ValueError("M2A internal delivered-fixture manifest mismatch")
    if identities.get("delivered_pcm") != {
        "sample_rate_hz": 16000,
        "channels": 1,
        "sample_format": "S16_LE",
    }:
        raise ValueError("M2A internal delivered PCM identity mismatch")
    selection = document.get("selection", {})
    records = selection.get("records")
    if selection.get("count") != 8 or not isinstance(records, list) or len(records) != 8:
        raise ValueError("M2A internal source lock must contain eight records")
    expected_groups = {
        "taiwan_mandarin": 2,
        "code_switch": 2,
        "number_or_date": 2,
        "product_term": 2,
    }
    actual_groups = {group: 0 for group in expected_groups}
    fixture_ids: set[str] = set()
    global_longest = []
    for record in records:
        if not isinstance(record, dict) or any(
            key in record for key in ("reference_text", "transcript")
        ):
            raise ValueError("invalid or unsafe M2A internal source-lock record")
        fixture_id = str(record.get("fixture_id", ""))
        group = str(record.get("group", ""))
        if not fixture_id or fixture_id in fixture_ids or group not in actual_groups:
            raise ValueError("invalid or duplicate M2A internal fixture identity")
        duration = record.get("bounded_duration_ms")
        size = record.get("source_wav_size_bytes")
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError(f"invalid bounded duration: {fixture_id}")
        if not isinstance(size, int) or size <= 44:
            raise ValueError(f"invalid source WAV size: {fixture_id}")
        for field in ("reference_sha256", "source_wav_sha256"):
            if not SHA256_RE.fullmatch(str(record.get(field, ""))):
                raise ValueError(f"invalid internal {field}: {fixture_id}")
        fixture_ids.add(fixture_id)
        actual_groups[group] += 1
        if record.get("globally_longest") is True:
            global_longest.append(record)
    if actual_groups != expected_groups:
        raise ValueError("M2A internal source-lock group allocation mismatch")
    if len(global_longest) != 1 or global_longest[0]["bounded_duration_ms"] != max(
        record["bounded_duration_ms"] for record in records
    ):
        raise ValueError("M2A internal source-lock global-longest marker mismatch")
    local = document.get("local_controlled_copy", {})
    path = PurePosixPath(str(local.get("relative_directory", "")))
    if path.is_absolute() or ".." in path.parts or local.get("source_asr_file_count") != 50:
        raise ValueError("M2A internal controlled-copy summary mismatch")
    handoff = document.get("handoff", {})
    if handoff.get("source_wav_sha256_is_authoritative") is not True:
        raise ValueError("M2A internal handoff must make source WAV SHA-256 authoritative")
    if handoff.get("reference_text_in_tracked_index") is not False:
        raise ValueError("M2A internal tracked handoff cannot contain reference text")


def verify_common_voice_source_files(
    source_lock: dict[str, Any], clips_dir: Path
) -> dict[str, Any]:
    validate_common_voice_source_lock(source_lock)
    records = source_lock["selection"]["records"]
    expected_names = {str(record["clip_id"]) for record in records}
    actual_names = {path.name for path in clips_dir.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise ValueError("controlled Common Voice clip set differs from source lock")
    for record in records:
        path = clips_dir / record["clip_id"]
        if path.stat().st_size != record["source_mp3_size_bytes"]:
            raise ValueError(f"Common Voice clip size mismatch: {record['clip_id']}")
        if sha256_file(path) != record["source_mp3_sha256"]:
            raise ValueError(f"Common Voice clip SHA-256 mismatch: {record['clip_id']}")
    return {
        "result": "PASS",
        "source_lock_id": COMMON_VOICE_SOURCE_LOCK_ID,
        "verified_files": len(records),
        "total_size_bytes": sum(record["source_mp3_size_bytes"] for record in records),
    }


def _label_records(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("frozen VAD label index must contain a records array")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not str(record.get("fixture_id", "")):
            raise ValueError("invalid VAD label record")
        fixture_id = str(record["fixture_id"])
        if fixture_id in result:
            raise ValueError(f"duplicate VAD label record: {fixture_id}")
        result[fixture_id] = record
    return result


def _bounded_duration_ms(record: dict[str, Any]) -> int:
    intervals = record.get("speech_intervals_ms")
    if not isinstance(intervals, list) or not intervals:
        raise ValueError(f"missing speech intervals for {record.get('fixture_id')}")
    parsed: list[tuple[int, int]] = []
    for interval in intervals:
        if not isinstance(interval, list) or len(interval) != 2:
            raise ValueError(f"invalid speech interval for {record.get('fixture_id')}")
        start, end = interval
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise ValueError(f"invalid speech bounds for {record.get('fixture_id')}")
        parsed.append((start, end))
    if parsed != sorted(parsed) or any(left[1] > right[0] for left, right in zip(parsed, parsed[1:])):
        raise ValueError(f"overlapping or unordered speech intervals for {record.get('fixture_id')}")
    return parsed[-1][1] - parsed[0][0]


def select_internal_fixtures(
    recording_plan: dict[str, Any], label_index: dict[str, Any]
) -> list[dict[str, Any]]:
    utterances = recording_plan.get("utterances")
    if not isinstance(utterances, list):
        raise ValueError("recording plan must contain utterances")
    labels = _label_records(label_index)
    candidates: list[dict[str, Any]] = []
    for utterance in utterances:
        if not isinstance(utterance, dict):
            raise ValueError("invalid recording-plan utterance")
        fixture_id = str(utterance.get("fixture_id", ""))
        category = str(utterance.get("category", ""))
        if fixture_id not in labels:
            raise ValueError(f"missing frozen VAD label: {fixture_id}")
        group = next((name for name, categories in GROUP_CATEGORIES.items() if category in categories), None)
        if group is None:
            raise ValueError(f"unsupported ASR category: {category}")
        candidates.append({
            "fixture_id": fixture_id,
            "category": category,
            "group": group,
            "bounded_duration_ms": _bounded_duration_ms(labels[fixture_id]),
            "reference_sha256": hashlib.sha256(
                str(utterance.get("reference_text", "")).encode("utf-8")
            ).hexdigest(),
        })

    selected: list[dict[str, Any]] = []
    for group in GROUP_CATEGORIES:
        ranked = sorted(
            (item for item in candidates if item["group"] == group),
            key=lambda item: (-int(item["bounded_duration_ms"]), str(item["fixture_id"])),
        )
        if len(ranked) < 2:
            raise ValueError(f"fewer than two frozen fixtures in group: {group}")
        selected.extend(ranked[:2])
    if len(selected) != 8 or len({item["fixture_id"] for item in selected}) != 8:
        raise ValueError("internal selection must contain eight unique fixtures")

    global_longest = min(
        (item for item in candidates if item["bounded_duration_ms"] == max(
            candidate["bounded_duration_ms"] for candidate in candidates
        )),
        key=lambda item: str(item["fixture_id"]),
    )
    selected_ids = {str(item["fixture_id"]) for item in selected}
    if global_longest["fixture_id"] not in selected_ids:
        raise ValueError("deterministic selection omitted the globally longest bounded fixture")
    for item in selected:
        item["globally_longest"] = item["fixture_id"] == global_longest["fixture_id"]
    return selected


def select_common_voice_rows(
    rows: Iterable[dict[str, str]], count: int = COMMON_VOICE_COUNT
) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        path = row.get("path", "").strip()
        sentence = row.get("sentence", "").strip()
        locale = row.get("locale", "").strip()
        if not path or not sentence or (locale and locale != "zh-TW"):
            continue
        relative_path = Path(path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"unsafe Common Voice clip path: {path}")
        existing = unique.get(path)
        if existing is not None and existing["sentence"] != sentence:
            raise ValueError(f"conflicting Common Voice transcript for clip: {path}")
        unique.setdefault(path, {"path": path, "sentence": sentence})
    if len(unique) < count:
        raise ValueError(f"Common Voice validated.tsv has fewer than {count} eligible zh-TW rows")

    def rank(item: dict[str, str]) -> str:
        payload = f"{COMMON_VOICE_DATASET_ID}\0{item['path']}\0{item['sentence']}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    selected = sorted(unique.values(), key=lambda item: (rank(item), item["path"]))[:count]
    return [{
        "clip_id": item["path"],
        "path": item["path"],
        "selection_rank_sha256": rank(item),
        "reference_sha256": hashlib.sha256(item["sentence"].encode("utf-8")).hexdigest(),
        "reference_text": item["sentence"],
    } for item in selected]


def _safe_archive_member(name: str) -> PurePosixPath:
    member_path = PurePosixPath(name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError(f"unsafe Common Voice archive member: {name}")
    return member_path


def _select_archive_rows(archive_path: Path) -> tuple[list[dict[str, str]], PurePosixPath]:
    with tarfile.open(archive_path, mode="r|*") as archive:
        for member in archive:
            member_path = _safe_archive_member(member.name)
            if member_path.parts[-2:] != ("zh-TW", "validated.tsv"):
                continue
            if not member.isfile() or not 0 < member.size <= MAX_COMMON_VOICE_TSV_BYTES:
                raise ValueError("invalid Common Voice validated.tsv archive member")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError("unable to read Common Voice validated.tsv")
            with extracted:
                text = codecs.getreader("utf-8")(extracted)
                selected = select_common_voice_rows(csv.DictReader(text, delimiter="\t"))
            return selected, member_path.parent
    raise ValueError("Common Voice archive does not contain zh-TW/validated.tsv")


def select_common_voice_archive(archive_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select and hash twelve clips by streaming a Common Voice archive without extraction."""

    selected, locale_root = _select_archive_rows(archive_path)
    wanted = {
        str(locale_root / "clips" / str(item["path"])): item
        for item in selected
    }
    seen: set[str] = set()
    with tarfile.open(archive_path, mode="r|*") as archive:
        for member in archive:
            member_path = _safe_archive_member(member.name)
            name = str(member_path)
            item = wanted.get(name)
            if item is None:
                continue
            if name in seen:
                raise ValueError(f"duplicate selected Common Voice archive member: {name}")
            if not member.isfile() or not 0 < member.size <= MAX_COMMON_VOICE_CLIP_BYTES:
                raise ValueError(f"invalid selected Common Voice clip member: {name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read selected Common Voice clip: {name}")
            digest = hashlib.sha256()
            size = 0
            with extracted:
                for chunk in iter(lambda: extracted.read(1024 * 1024), b""):
                    size += len(chunk)
                    digest.update(chunk)
            if size != member.size:
                raise ValueError(f"truncated selected Common Voice clip: {name}")
            item["source_mp3_sha256"] = digest.hexdigest()
            item["source_size_bytes"] = size
            item["archive_member_path"] = name
            seen.add(name)
            if len(seen) == len(wanted):
                break
    missing = sorted(set(wanted) - seen)
    if missing:
        raise ValueError(f"missing selected Common Voice clip in archive: {missing[0]}")
    return selected, {
        "mode": "streamed_archive",
        "archive_filename": archive_path.name,
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": None,
        "archive_sha256_status": "NOT_REQUIRED_PER_CLIP_SHA256_IS_AUTHORITATIVE",
    }


def build_preselection(
    packet: dict[str, Any], recording_plan_path: Path, label_index_path: Path,
    validated_tsv_path: Path | None = None, clips_dir: Path | None = None,
    *, archive_path: Path | None = None,
) -> dict[str, Any]:
    validate_packet(packet)
    if sha256_file(recording_plan_path) != PLAN_SHA256:
        raise ValueError("frozen recording plan checksum mismatch")
    if sha256_file(label_index_path) != LABEL_INDEX_SHA256:
        raise ValueError("frozen VAD label index checksum mismatch")
    internal = select_internal_fixtures(load_json(recording_plan_path), load_json(label_index_path))
    if archive_path is not None:
        if validated_tsv_path is not None or clips_dir is not None:
            raise ValueError("choose either a Common Voice archive or an extracted tree")
        external, source_identity = select_common_voice_archive(archive_path)
    else:
        if validated_tsv_path is None or clips_dir is None:
            raise ValueError("extracted Common Voice input requires validated.tsv and clips directory")
        with validated_tsv_path.open("r", encoding="utf-8", newline="") as source:
            external = select_common_voice_rows(csv.DictReader(source, delimiter="\t"))
        for item in external:
            source_path = (clips_dir / item["path"]).resolve()
            if not source_path.is_relative_to(clips_dir.resolve()):
                raise ValueError(f"selected Common Voice clip escapes the clip directory: {item['path']}")
            if not source_path.is_file():
                raise ValueError(f"missing selected Common Voice clip: {item['path']}")
            item["source_mp3_sha256"] = sha256_file(source_path)
            item["source_size_bytes"] = source_path.stat().st_size
        source_identity = {"mode": "extracted_tree"}
    return {
        "schema_version": "1.0",
        "index_id": "M4A-M2A-FIXTURE-PRESELECTION-001",
        "status": "PRESELECTED_DERIVED_PCM_LOCK_PENDING",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "packet_id": PACKET_ID,
        "git_safety": "CONTROLLED_INDEX_CONTAINS_COMMON_VOICE_TEXT_DO_NOT_COMMIT",
        "selection_timing": "COMPLETED_BEFORE_ANY_M2A_CANDIDATE_OUTPUT_REVIEW",
        "internal": internal,
        "common_voice": {
            "dataset_id": COMMON_VOICE_DATASET_ID,
            "release": "26.0",
            "locale": "zh-TW",
            "license": "CC0-1.0",
            "source_identity": source_identity,
            "records": external,
        },
        "remaining_lock_work": [
            "derive and hash all selected 16 kHz mono S16_LE WAV files",
            "record duration and conversion tool identity",
            "write a sanitized tracked index without reference text or audio paths",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        type=Path,
        default=repo_root() / "poc_audio/manifests/m4a_m2a_common_packet.json",
    )
    parser.add_argument(
        "--common-voice-source-lock",
        type=Path,
        default=repo_root() / "poc_audio/manifests/m4a_m2a_common_voice_source_lock.json",
    )
    parser.add_argument(
        "--internal-source-lock",
        type=Path,
        default=repo_root() / "poc_audio/manifests/m4a_m2a_internal_source_lock.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-common-voice-clips-dir", type=Path)
    parser.add_argument("--recording-plan", type=Path)
    parser.add_argument("--vad-label-index", type=Path)
    parser.add_argument("--common-voice-validated-tsv", type=Path)
    parser.add_argument("--common-voice-clips-dir", type=Path)
    parser.add_argument("--common-voice-archive", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = load_json(args.packet)
    validate_packet(packet)
    source_lock = load_json(args.common_voice_source_lock)
    validate_common_voice_source_lock(source_lock)
    internal_source_lock = load_json(args.internal_source_lock)
    validate_internal_source_lock(internal_source_lock)
    if args.verify_common_voice_clips_dir is not None:
        result = verify_common_voice_source_files(
            source_lock, args.verify_common_voice_clips_dir
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.validate_only:
        print(f"M2A packet valid: {args.packet}")
        return 0
    required = (args.recording_plan, args.vad_label_index, args.output)
    if any(value is None for value in required):
        raise ValueError("fixture preselection requires all controlled input and output arguments")
    archive_mode = args.common_voice_archive is not None
    extracted_mode = (
        args.common_voice_validated_tsv is not None
        and args.common_voice_clips_dir is not None
    )
    if archive_mode == extracted_mode:
        raise ValueError("choose exactly one Common Voice input mode: archive or extracted tree")
    if not extracted_mode and (
        args.common_voice_validated_tsv is not None
        or args.common_voice_clips_dir is not None
    ):
        raise ValueError("extracted Common Voice input requires both validated.tsv and clips directory")
    assert args.output is not None
    if args.output.resolve().is_relative_to(repo_root().resolve()):
        raise ValueError("controlled preselection output must stay outside the repository")
    if args.output.exists():
        raise ValueError("preselection output already exists")
    assert args.recording_plan is not None
    assert args.vad_label_index is not None
    result = build_preselection(
        packet,
        args.recording_plan,
        args.vad_label_index,
        args.common_voice_validated_tsv,
        args.common_voice_clips_dir,
        archive_path=args.common_voice_archive,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M2A controlled preselection: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
