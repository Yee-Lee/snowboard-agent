from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from audio_poc.m2b_c_prompt_probe import PROMPT, predecessor_match, summarize, validate_probe


class M2BCPromptProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.probe = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_base_q8_prompt_probe.json").read_text()
        )

    def test_probe_is_one_variable_and_keeps_both_holdouts_sealed(self) -> None:
        validate_probe(self.probe)
        self.assertNotIn("請把", PROMPT)
        self.assertEqual(self.probe["scope"]["internal_holdout_execution"], "SEALED")
        self.assertEqual(self.probe["scope"]["common_voice_holdout_execution"], "SEALED")

    def test_probe_rejects_prompt_drift(self) -> None:
        changed = copy.deepcopy(self.probe)
        changed["single_variable"]["probe"] += "測試句"
        with self.assertRaisesRegex(ValueError, "only the frozen initial prompt"):
            validate_probe(changed)

    def test_predecessor_hashes_cover_internal_and_common_voice(self) -> None:
        results = []
        for family, identity in self.probe["predecessors"].items():
            if family == "required_baseline_hypothesis_hash_match":
                continue
            previous = json.loads((self.root / identity["path"]).read_text())
            if family == "internal":
                selected = [x for x in previous["results"] if x.get("profile") == identity["profile"]]
                results.extend({**x, "profile": "baseline", "item_id": x["fixture_id"]} for x in selected)
            else:
                selected = [x for x in previous["results"] if x.get("candidate_id") == identity["candidate_id"]]
                results.extend({**x, "profile": "baseline", "item_id": x["review_id"]} for x in selected)
        self.assertTrue(predecessor_match(self.probe, results, self.root))

    def test_summary_reports_quality_terms_and_false_insertions(self) -> None:
        results = []
        for profile, edits, expected, unexpected in (
            ("baseline", 2, [], []), ("domain_prompt", 1, ["audio_frame"], ["wifi"]),
        ):
            for family in ("internal", "common_voice"):
                results.append({
                    "profile": profile, "family": family, "item_id": family,
                    "category": "x", "reference_length": 10, "edit_distance": edits,
                    "sentence_correct": False, "latency_ms": 100.0,
                    "rtf": 0.1, "peak_rss_mib": 200.0,
                    "expected_domain_term_hits": expected if family == "internal" else [],
                    "unexpected_domain_term_hits": unexpected,
                })
        summary = summarize(results)
        self.assertEqual(summary["profiles"]["domain_prompt"]["internal"]["cer_percent"], 10.0)
        self.assertEqual(summary["profiles"]["domain_prompt"]["common_voice"]["unexpected_domain_term_hits"], 1)


if __name__ == "__main__":
    unittest.main()
