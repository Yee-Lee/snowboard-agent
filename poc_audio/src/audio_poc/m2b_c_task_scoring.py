"""Produce bounded C task-adjusted ASR metrics without changing raw CER."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from typing import Any

from .m2b_c_fixture_lock import load_json, sha256_file
from .m4a_candidate_worker import edit_distance
from .m4a_whispercpp_build import assert_network_isolated


SCORING_ID = "M2B-C-TASK-ADJUSTED-SCORING-001"
CHINESE_NUMBER = re.compile(r"[零〇一二兩两三四五六七八九十百千]+")
PERCENT_NUMBER = re.compile(r"百分之([零〇一二兩两三四五六七八九十百千]+)")
DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2, "三": 3,
          "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
UNITS = {"十": 10, "百": 100, "千": 1000}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def chinese_integer(text: str) -> int:
    if not text or any(char not in DIGITS and char not in UNITS for char in text):
        raise ValueError("unsupported Chinese integer")
    if not any(char in UNITS for char in text):
        return int("".join(str(DIGITS[char]) for char in text))
    total, number = 0, 0
    for char in text:
        if char in DIGITS:
            number = DIGITS[char]
        else:
            total += (number or 1) * UNITS[char]
            number = 0
    value = total + number
    if value > 9999:
        raise ValueError("Chinese integer exceeds bounded scorer")
    return value


def normalize_task(text: str, script_map: dict[str, str]) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = "".join(script_map.get(char, char) for char in normalized)
    normalized = PERCENT_NUMBER.sub(lambda match: f"{chinese_integer(match.group(1))}%", normalized)
    normalized = CHINESE_NUMBER.sub(lambda match: str(chinese_integer(match.group(0))), normalized)
    return "".join(
        char for char in normalized
        if char == "%" or char.isdecimal() or "a" <= char <= "z" or "\u3400" <= char <= "\u9fff"
    )


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("scoring_id") != SCORING_ID \
            or packet.get("status") != "FROZEN_BEFORE_TASK_ADJUSTED_SCORING":
        raise ValueError("task scoring identity mismatch")
    sources = packet.get("sources", [])
    if [item.get("source_id") for item in sources] != [
        "base_dev", "base_holdout", "small_dev", "small_holdout",
    ] or packet.get("profiles") != ["baseline", "domain_prompt"] \
            or packet.get("families") != ["internal", "common_voice"] \
            or packet.get("expected_controlled_rows") != 96:
        raise ValueError("task scoring source matrix mismatch")
    normalization = packet.get("normalization", {})
    mapping = normalization.get("traditional_to_simplified")
    if not isinstance(mapping, dict) or len(mapping) != 71 \
            or any(len(key) != 1 or len(value) != 1 or key == value for key, value in mapping.items()):
        raise ValueError("task scoring script map mismatch")
    if normalization.get("numeric_policy") != \
            "CHINESE_DIGIT_SEQUENCE_AND_UNIT_INTEGER_0_TO_9999_PLUS_PERCENT_OF":
        raise ValueError("task scoring numeric policy mismatch")
    if packet.get("invariants") != {
        "raw_metrics_must_match_source": True, "raw_transcript_or_cer_overwrite": False,
        "homophone_equivalence": False, "domain_alias_equivalence": False,
        "runtime_postprocessing": False, "controlled_text_in_git": False,
    }:
        raise ValueError("task scoring invariant mismatch")


def score_row(
    source: dict[str, Any], controlled: dict[str, Any], sanitized: dict[str, Any],
    script_map: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_reference = str(controlled["reference_text"])
    raw_hypothesis = str(controlled["hypothesis"])
    if (
        controlled["hypothesis_sha256"] != sanitized["hypothesis_sha256"]
        or controlled["edit_distance"] != sanitized["edit_distance"]
        or controlled["reference_length"] != sanitized["reference_length"]
        or controlled["sentence_correct"] != sanitized["sentence_correct"]
        or hashlib.sha256(raw_hypothesis.encode()).hexdigest() != sanitized["hypothesis_sha256"]
    ):
        raise ValueError("controlled and sanitized raw metrics mismatch")
    task_reference = normalize_task(raw_reference, script_map)
    task_hypothesis = normalize_task(raw_hypothesis, script_map)
    common = {
        "source_id": source["source_id"], "candidate_id": source["candidate_id"],
        "split": source["split"], "profile": controlled["profile"],
        "family": controlled["family"], "item_id": controlled["item_id"],
        "fixture_id": controlled["fixture_id"], "category": controlled["category"],
        "raw_reference_length": controlled["reference_length"],
        "raw_edit_distance": controlled["edit_distance"],
        "raw_sentence_correct": controlled["sentence_correct"],
        "task_reference_length": len(task_reference),
        "task_hypothesis_length": len(task_hypothesis),
        "task_edit_distance": edit_distance(task_reference, task_hypothesis),
        "task_sentence_correct": task_reference == task_hypothesis,
        "task_reference_sha256": hashlib.sha256(task_reference.encode()).hexdigest(),
        "task_hypothesis_sha256": hashlib.sha256(task_hypothesis.encode()).hexdigest(),
    }
    common["edit_adjustment_task_minus_raw"] = \
        common["task_edit_distance"] - common["raw_edit_distance"]
    return {
        **common, "reference_text": raw_reference, "hypothesis": raw_hypothesis,
        "task_reference": task_reference, "task_hypothesis": task_hypothesis,
    }, common


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_chars = sum(item["raw_reference_length"] for item in rows)
    task_chars = sum(item["task_reference_length"] for item in rows)
    raw_edits = sum(item["raw_edit_distance"] for item in rows)
    task_edits = sum(item["task_edit_distance"] for item in rows)
    return {
        "items": len(rows),
        "raw": {
            "edits": raw_edits, "reference_chars": raw_chars,
            "cer_percent": round(raw_edits / raw_chars * 100.0, 6),
            "correct_sentences": sum(bool(item["raw_sentence_correct"]) for item in rows),
            "sentence_correctness_percent": round(
                sum(bool(item["raw_sentence_correct"]) for item in rows) / len(rows) * 100.0, 6
            ),
        },
        "task_adjusted": {
            "edits": task_edits, "reference_chars": task_chars,
            "cer_percent": round(task_edits / task_chars * 100.0, 6),
            "correct_sentences": sum(bool(item["task_sentence_correct"]) for item in rows),
            "sentence_correctness_percent": round(
                sum(bool(item["task_sentence_correct"]) for item in rows) / len(rows) * 100.0, 6
            ),
        },
        "adjustment": {
            "edits_task_minus_raw": task_edits - raw_edits,
            "correct_sentences_task_minus_raw":
                sum(bool(item["task_sentence_correct"]) for item in rows)
                - sum(bool(item["raw_sentence_correct"]) for item in rows),
        },
    }


def summarize(rows: list[dict[str, Any]], packet: dict[str, Any]) -> dict[str, Any]:
    candidates = sorted({str(item["candidate_id"]) for item in rows})
    matrix: dict[str, Any] = {}
    for candidate in candidates:
        matrix[candidate] = {}
        for profile in packet["profiles"]:
            selected_profile = [
                item for item in rows if item["candidate_id"] == candidate and item["profile"] == profile
            ]
            matrix[candidate][profile] = {
                "combined": {
                    family: metric_summary([
                        item for item in selected_profile if item["family"] == family
                    ]) for family in packet["families"]
                },
                "by_split": {
                    split: {
                        family: metric_summary([
                            item for item in selected_profile
                            if item["split"] == split and item["family"] == family
                        ]) for family in packet["families"]
                    } for split in ("dev", "holdout")
                },
            }
    return matrix


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=root / "poc_audio/manifests/m2b_c_task_adjusted_scoring.json")
    parser.add_argument("--base-dev", type=Path, required=True)
    parser.add_argument("--base-holdout", type=Path, required=True)
    parser.add_argument("--small-dev", type=Path, required=True)
    parser.add_argument("--small-holdout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitized-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args, root = parse_args(), repo_root().resolve()
    if args.packet.resolve() != root / "poc_audio/manifests/m2b_c_task_adjusted_scoring.json":
        raise ValueError("task scoring must use the tracked packet")
    for output in (args.output, args.sanitized_output):
        if output.exists() or output.resolve().is_relative_to(root):
            raise ValueError("task scoring outputs must be new and outside Git")
    packet = load_json(args.packet)
    validate_packet(packet)
    controlled_paths = {
        "base_dev": args.base_dev, "base_holdout": args.base_holdout,
        "small_dev": args.small_dev, "small_holdout": args.small_holdout,
    }
    raw_rows: list[dict[str, Any]] = []
    sanitized_rows: list[dict[str, Any]] = []
    for source in packet["sources"]:
        controlled_path = controlled_paths[source["source_id"]]
        sanitized_path = root / source["sanitized_path"]
        if sha256_file(controlled_path) != source["controlled_sha256"] \
                or sha256_file(sanitized_path) != source["sanitized_sha256"]:
            raise ValueError(f"task scoring source checksum mismatch: {source['source_id']}")
        controlled, sanitized = load_json(controlled_path), load_json(sanitized_path)
        sanitized_index = {
            (item["profile"], item["item_id"]): item for item in sanitized["results"]
        }
        for item in controlled["results"]:
            peer = sanitized_index.get((item["profile"], item["item_id"]))
            if peer is None:
                raise ValueError("task scoring sanitized row missing")
            raw, clean = score_row(
                source, item, peer, packet["normalization"]["traditional_to_simplified"]
            )
            raw_rows.append(raw)
            sanitized_rows.append(clean)
    complete = len(sanitized_rows) == packet["expected_controlled_rows"]
    base = {
        "schema_version": "1.0", "report_id": SCORING_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "execution_status": "TASK_ADJUSTED_OBSERVATIONS_COMPLETE_PENDING_REVIEW" if complete else "INCONCLUSIVE",
        "poc_source_sha": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "source_results": packet["sources"], "normalization": packet["normalization"],
        "invariants": packet["invariants"],
        "summary": summarize(sanitized_rows, packet) if complete else None,
        "security": {"audio_opened": False, "model_loaded": False, "inference_run": False},
    }
    raw = {**base, "git_safety": "CONTROLLED_TEXT_DO_NOT_COMMIT", "results": raw_rows}
    sanitized = {**base, "raw_text_emitted": False, "results": sanitized_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.sanitized_output.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Task-adjusted scoring: {args.sanitized_output} ({base['execution_status']})")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
