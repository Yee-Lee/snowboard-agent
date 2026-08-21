from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4a_m2a_packet import (  # noqa: E402
    COMMON_VOICE_COUNT,
    EXPECTED_CANDIDATES,
    select_common_voice_rows,
    select_internal_fixtures,
    validate_packet,
)


class M2ACommonPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(
            (REPO_ROOT / "poc_audio/manifests/m4a_m2a_common_packet.json").read_text(
                encoding="utf-8"
            )
        )

    def test_tracked_packet_matches_ack003(self) -> None:
        validate_packet(self.packet)
        self.assertEqual(
            tuple(row["candidate_id"] for row in self.packet["candidate_rows"]),
            EXPECTED_CANDIDATES,
        )
        self.assertEqual(self.packet["fixture_lock"]["internal"]["selection_count"], 8)
        self.assertEqual(
            self.packet["fixture_lock"]["external"]["selection_count"],
            COMMON_VOICE_COUNT,
        )

    def test_q5_is_independent_and_m2a_has_no_elimination_gates(self) -> None:
        serialized = json.dumps(self.packet, sort_keys=True)
        self.assertNotIn("fallback_requires", serialized)
        self.assertNotIn("stop_on_q8_quality_failure", serialized)
        disposition = self.packet["disposition_policy"]
        self.assertFalse(disposition["quality_performance_thresholds_are_elimination_gates"])
        self.assertEqual(
            set(disposition["prohibited_labels"]),
            {"PASS", "FAIL", "WINNER", "PRODUCTION_BASELINE"},
        )

    def test_manifest_rejects_artifact_identity_drift(self) -> None:
        changed = json.loads(json.dumps(self.packet))
        changed["candidate_rows"][3]["artifact"]["sha256"] = "0" * 63
        with self.assertRaisesRegex(ValueError, "artifact SHA-256"):
            validate_packet(changed)

    def test_internal_selection_takes_two_longest_per_group_and_global_longest(self) -> None:
        category_groups = (
            ("taiwan_mandarin", "taiwan_mandarin"),
            ("code_switch", "code_switch"),
            ("number", "number"),
            ("product_term", "product_term"),
        )
        utterances = []
        records = []
        for group_index, (_, category) in enumerate(category_groups):
            for item_index, duration in enumerate((1000, 2000, 3000), start=1):
                fixture_id = f"g{group_index}-{item_index}"
                utterances.append({
                    "fixture_id": fixture_id,
                    "category": category,
                    "reference_text": f"reference {fixture_id}",
                })
                records.append({
                    "fixture_id": fixture_id,
                    "speech_intervals_ms": [[100, 100 + duration]],
                })
        records[-1]["speech_intervals_ms"] = [[100, 5000]]

        selected = select_internal_fixtures(
            {"utterances": utterances},
            {"records": records},
        )
        self.assertEqual(len(selected), 8)
        for group_name in ("taiwan_mandarin", "code_switch", "number_or_date", "product_term"):
            self.assertEqual(sum(item["group"] == group_name for item in selected), 2)
        longest = [item for item in selected if item["globally_longest"]]
        self.assertEqual([item["fixture_id"] for item in longest], ["g3-3"])
        self.assertNotIn("g0-1", {item["fixture_id"] for item in selected})

    def test_common_voice_selection_is_deterministic_and_omits_invalid_locale(self) -> None:
        rows = [
            {"path": f"clip-{index:02d}.mp3", "sentence": f"句子 {index}", "locale": "zh-TW"}
            for index in range(20)
        ]
        rows.extend([
            {"path": "wrong.mp3", "sentence": "錯誤語系", "locale": "zh-CN"},
            {"path": "blank.mp3", "sentence": "", "locale": "zh-TW"},
        ])
        first = select_common_voice_rows(rows)
        second = select_common_voice_rows(reversed(rows[:20]))
        self.assertEqual(len(first), COMMON_VOICE_COUNT)
        self.assertEqual(
            [(item["path"], item["reference_sha256"]) for item in first],
            [(item["path"], item["reference_sha256"]) for item in second],
        )
        self.assertNotIn("wrong.mp3", {item["path"] for item in first})

    def test_common_voice_selection_rejects_conflicting_or_unsafe_paths(self) -> None:
        conflict = [
            {"path": "same.mp3", "sentence": "第一句", "locale": "zh-TW"},
            {"path": "same.mp3", "sentence": "第二句", "locale": "zh-TW"},
        ]
        with self.assertRaisesRegex(ValueError, "conflicting Common Voice transcript"):
            select_common_voice_rows(conflict, count=1)
        with self.assertRaisesRegex(ValueError, "unsafe Common Voice clip path"):
            select_common_voice_rows(
                [{"path": "../escape.mp3", "sentence": "句子", "locale": "zh-TW"}],
                count=1,
            )


if __name__ == "__main__":
    unittest.main()
