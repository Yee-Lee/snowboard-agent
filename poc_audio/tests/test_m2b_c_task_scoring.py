from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from audio_poc.m2b_c_task_scoring import (
    chinese_integer,
    metric_summary,
    normalize_task,
    validate_packet,
)


class M2BCTaskScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.packet = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_task_adjusted_scoring.json").read_text()
        )
        cls.script_map = cls.packet["normalization"]["traditional_to_simplified"]

    def test_packet_freezes_four_sources_and_bounded_map(self) -> None:
        validate_packet(self.packet)
        self.assertEqual(self.packet["expected_controlled_rows"], 96)

    def test_chinese_integer_supports_sequence_units_and_percent_value(self) -> None:
        self.assertEqual(chinese_integer("三一八"), 318)
        self.assertEqual(chinese_integer("十五"), 15)
        self.assertEqual(chinese_integer("六十"), 60)
        self.assertEqual(chinese_integer("兩"), 2)

    def test_task_normalization_handles_script_and_numeric_equivalence(self) -> None:
        pairs = (
            ("請檢查 Wi-Fi 狀態", "请检查WiFi状态"),
            ("設定十五分鐘的計時器", "設定15分鐘的計時器"),
            ("今天是三一八公民運動五週年", "今天是318公民运动5周年"),
            ("目前音量是百分之六十", "目前音量是60%"),
            ("信義新天地A四館", "信义新天地A4馆"),
        )
        for left, right in pairs:
            self.assertEqual(normalize_task(left, self.script_map), normalize_task(right, self.script_map))

    def test_task_normalization_does_not_accept_homophone(self) -> None:
        self.assertNotEqual(
            normalize_task("啟動音訊基線測試", self.script_map),
            normalize_task("啟動音訊機線測試", self.script_map),
        )

    def test_metric_summary_retains_raw_and_adjusted(self) -> None:
        rows = [{
            "raw_reference_length": 10, "raw_edit_distance": 2, "raw_sentence_correct": False,
            "task_reference_length": 10, "task_edit_distance": 0, "task_sentence_correct": True,
        }]
        summary = metric_summary(rows)
        self.assertEqual(summary["raw"]["cer_percent"], 20.0)
        self.assertEqual(summary["task_adjusted"]["cer_percent"], 0.0)
        self.assertEqual(summary["adjustment"]["edits_task_minus_raw"], -2)

    def test_packet_rejects_equivalence_expansion(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["invariants"]["homophone_equivalence"] = True
        with self.assertRaisesRegex(ValueError, "invariant mismatch"):
            validate_packet(changed)


if __name__ == "__main__":
    unittest.main()
