from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from audio_poc.m2b_c_padding_probe import summarize, validate_probe


class M2BCPaddingProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[2]
        cls.probe = json.loads(
            (root / "poc_audio/manifests/m2b_c_padding_probe.json").read_text()
        )

    def test_tracked_probe_is_dev_only_and_one_variable(self) -> None:
        validate_probe(self.probe)
        self.assertEqual(self.probe["scope"]["holdout_execution"], "SEALED")
        self.assertEqual(self.probe["scope"]["common_voice_execution"], "NOT_PART_OF_PADDING_PROBE")

    def test_probe_rejects_runtime_drift(self) -> None:
        changed = copy.deepcopy(self.probe)
        changed["runtime"]["internal_vad"] = True
        with self.assertRaisesRegex(ValueError, "runtime control"):
            validate_probe(changed)

    def test_summary_keeps_profiles_and_categories_separate(self) -> None:
        results = []
        for fixture_id, category in (("a", "code_switch"), ("b", "product_term")):
            for profile, edits in (("p0", 2), ("p300", 1), ("p500", 0)):
                results.append({
                    "fixture_id": fixture_id,
                    "category": category,
                    "profile": profile,
                    "reference_length": 10,
                    "edit_distance": edits,
                    "sentence_correct": edits == 0,
                    "latency_ms": 100.0,
                    "rtf": 0.1,
                    "peak_rss_mib": 200.0,
                })
        summary = summarize(results)
        self.assertEqual(summary["family"], "internal")
        self.assertEqual(summary["profiles"]["p0"]["cer_percent"], 20.0)
        self.assertEqual(summary["profiles"]["p500"]["sentence_correctness_percent"], 100.0)
        self.assertEqual(set(summary["profile_categories"]["p300"]), {"code_switch", "product_term"})
        self.assertEqual(len(summary["paired_fixture_delta_from_p0"]["p300"]), 2)


if __name__ == "__main__":
    unittest.main()
