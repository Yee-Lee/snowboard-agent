from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from audio_poc.m2b_c_common_voice_baseline import BASE_ID, SMALL_ID, summarize, validate_packet


class M2BCCommonVoiceBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[2]
        cls.packet = json.loads(
            (root / "poc_audio/manifests/m2b_c_common_voice_dev_baseline.json").read_text()
        )

    def test_packet_keeps_common_voice_holdout_sealed(self) -> None:
        validate_packet(self.packet)
        self.assertEqual(self.packet["scope"]["review_ids"], ["D02", "D05", "N03", "L03"])
        self.assertEqual(self.packet["scope"]["holdout_execution"], "SEALED")

    def test_packet_rejects_decoder_drift(self) -> None:
        changed = copy.deepcopy(self.packet)
        changed["runtime"]["decoder"] = "beam"
        with self.assertRaisesRegex(ValueError, "runtime"):
            validate_packet(changed)

    def test_summary_keeps_candidates_and_categories_separate(self) -> None:
        results = []
        for candidate, edits in ((BASE_ID, 2), (SMALL_ID, 1)):
            results.append({
                "candidate_id": candidate, "review_id": "D02", "category": "external_mandarin",
                "reference_length": 10, "edit_distance": edits, "sentence_correct": False,
                "latency_ms": 100.0 + edits, "rtf": 0.1, "peak_rss_mib": 200.0 + edits,
            })
        summary = summarize(results)
        self.assertEqual(summary["family"], "common_voice")
        self.assertEqual(summary["candidates"][BASE_ID]["cer_percent"], 20.0)
        self.assertEqual(summary["paired_candidate_delta"][0]["edit_distance_delta_small_minus_base"], -1)


if __name__ == "__main__":
    unittest.main()
