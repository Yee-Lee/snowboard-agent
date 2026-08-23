from __future__ import annotations

import unittest
import json
from pathlib import Path

from audio_poc.m2a_ab_split import BASE_ID, SMALL_ID, build_packets, metric_summary, paired_summary


def records(candidate_id: str) -> list[dict]:
    return [
        {
            "candidate_id": candidate_id, "fixture_id": "a1", "family": "internal",
            "fixture_group": "A", "category": "taiwan_mandarin", "reference_length": 10,
            "hypothesis_length": 10, "edit_distance": 0 if candidate_id == SMALL_ID else 2,
            "sentence_correct": candidate_id == SMALL_ID, "latency_ms": 10.0, "rtf": 0.1,
            "peak_rss_mib": 20.0, "hypothesis_sha256": "a" * 64,
            "formal_row_sha256": "b" * 64,
        },
        {
            "candidate_id": candidate_id, "fixture_id": "b1", "family": "common_voice",
            "fixture_group": "B", "category": "common_voice", "reference_length": 20,
            "hypothesis_length": 18, "edit_distance": 2, "sentence_correct": False,
            "latency_ms": 20.0, "rtf": 0.2, "peak_rss_mib": 21.0,
            "hypothesis_sha256": "c" * 64, "formal_row_sha256": "b" * 64,
        },
    ]


class M2AABSplitTests(unittest.TestCase):
    def test_metric_summary_uses_frozen_counts_and_nearest_rank(self) -> None:
        summary = metric_summary(records(SMALL_ID))
        self.assertEqual(summary["edit_distance_total"], 2)
        self.assertEqual(summary["reference_length_total"], 30)
        self.assertEqual(summary["cer_percent"], 6.666667)
        self.assertEqual(summary["latency_ms"]["p50"], 10.0)
        self.assertEqual(summary["latency_ms"]["p95"], 20.0)

    def test_pairing_keeps_a_and_b_separate(self) -> None:
        source = {SMALL_ID: records(SMALL_ID), BASE_ID: records(BASE_ID)}
        self.assertEqual(
            paired_summary(source, "internal"),
            {"both_correct": 0, "small_only_correct": 1, "base_only_correct": 0, "both_wrong": 0},
        )
        self.assertEqual(
            paired_summary(source, "common_voice"),
            {"both_correct": 0, "small_only_correct": 0, "base_only_correct": 0, "both_wrong": 1},
        )

    def test_build_rejects_fixture_identity_drift(self) -> None:
        def document(candidate_id: str) -> dict:
            return {
                "poc_source_sha": "d" * 40,
                "artifact": {"sha256": "e" * 64},
                "fixture_lock_sha256": "f" * 64,
                "controlled_manifest_sha256": "0" * 64,
                "results": records(candidate_id),
            }

        small = document(SMALL_ID)
        base = document(BASE_ID)
        base["results"][0]["reference_length"] = 11
        with self.assertRaisesRegex(ValueError, "exact fixture identities"):
            build_packets({SMALL_ID: ("1" * 64, small), BASE_ID: ("2" * 64, base)})

    def test_tracked_packet_reproduces_frozen_ab_totals(self) -> None:
        root = Path(__file__).resolve().parents[2]
        evidence = root / "poc_audio/evidence/m2/M4A-M2A-AB-SPLIT-001"
        items = json.loads((evidence / "items.sanitized.json").read_text(encoding="utf-8"))
        summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(items["record_count"], 40)
        self.assertEqual(
            items["security"],
            {"reference_text_included": False, "hypothesis_text_included": False, "pcm_included": False},
        )
        small = summary["candidates"][SMALL_ID]
        base = summary["candidates"][BASE_ID]
        self.assertEqual((small["A"]["edit_distance_total"], small["B"]["edit_distance_total"]), (30, 9))
        self.assertEqual((base["A"]["edit_distance_total"], base["B"]["edit_distance_total"]), (34, 29))
        self.assertEqual(small["A_plus_B"]["cer_percent"], 15.983607)
        self.assertEqual(base["A_plus_B"]["cer_percent"], 25.819672)


if __name__ == "__main__":
    unittest.main()
