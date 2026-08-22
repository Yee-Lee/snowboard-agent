from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from audio_poc.m2b_c_decoder_probe import predecessor_match, summarize, validate_probe


class M2BCDecoderProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.probe = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_base_q8_decoder_probe.json").read_text()
        )

    def test_probe_changes_only_decoder_on_internal_dev(self) -> None:
        validate_probe(self.probe)
        self.assertEqual(self.probe["scope"]["pcm_profile"], "p0")
        self.assertEqual(self.probe["scope"]["holdout_execution"], "SEALED")

    def test_probe_rejects_beam_size_drift(self) -> None:
        changed = copy.deepcopy(self.probe)
        changed["single_variable"]["probe"]["beam_size"] = 8
        with self.assertRaisesRegex(ValueError, "more than decoder"):
            validate_probe(changed)

    def test_predecessor_hashes_bind_new_greedy_baseline(self) -> None:
        previous = json.loads(
            (self.root / self.probe["greedy_predecessor"]["path"]).read_text()
        )
        results = [
            {**item, "decoder": "greedy"}
            for item in previous["results"] if item["profile"] == "p0"
        ]
        self.assertTrue(predecessor_match(self.probe, results, self.root))

    def test_summary_keeps_decoder_categories_separate(self) -> None:
        results = []
        for decoder, edits in (("greedy", 2), ("beam", 1)):
            results.append({
                "decoder": decoder, "fixture_id": "a", "category": "code_switch",
                "reference_length": 10, "edit_distance": edits, "sentence_correct": False,
                "latency_ms": 100.0 + edits, "rtf": 0.1, "peak_rss_mib": 200.0,
            })
        summary = summarize(results)
        self.assertEqual(summary["decoders"]["greedy"]["cer_percent"], 20.0)
        self.assertEqual(summary["paired_decoder_delta"][0]["edit_distance_delta_beam_minus_greedy"], -1)


if __name__ == "__main__":
    unittest.main()
