from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest


class M2BCRecipeProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.proposal = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_asr_recipe_proposal.json").read_text()
        )

    def test_source_results_are_exact_and_sanitized(self) -> None:
        for identity in self.proposal["source_results"]:
            path = self.root / identity["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), identity["sha256"])
            result = json.loads(path.read_text())
            self.assertFalse(any("hypothesis" in item for item in result["results"]))
            self.assertFalse(any("reference_text" in item for item in result["results"]))

    def test_combined_metrics_recompute_from_prompt_profiles(self) -> None:
        sources = {
            "primary": self.proposal["source_results"][:2],
            "fallback": self.proposal["source_results"][2:],
        }
        for role, identities in sources.items():
            rows = []
            for identity in identities:
                result = json.loads((self.root / identity["path"]).read_text())
                rows.extend(item for item in result["results"] if item["profile"] == "domain_prompt")
            for family in ("internal", "common_voice"):
                selected = [item for item in rows if item["family"] == family]
                expected = self.proposal["combined_c_observations"][role][family]
                edits = sum(item["edit_distance"] for item in selected)
                reference = sum(item["reference_length"] for item in selected)
                self.assertEqual((len(selected), edits, reference), (
                    expected["items"], expected["edits"], expected["reference_chars"],
                ))
                self.assertEqual(round(edits / reference * 100.0, 6), expected["cer_percent"])
                latencies = sorted(item["latency_ms"] for item in selected)
                p50 = latencies[math.ceil(len(latencies) * 0.5) - 1]
                p95 = latencies[math.ceil(len(latencies) * 0.95) - 1]
                self.assertEqual((p50, p95), (expected["latency_p50_ms"], expected["latency_p95_ms"]))

    def test_proposal_keeps_raw_and_task_scoring_separate(self) -> None:
        boundary = self.proposal["scoring_boundary"]
        self.assertEqual(boundary["runtime_postprocessing"], "NOT_ADDED_BY_THIS_PROPOSAL")
        self.assertIn("DO_NOT_OVERWRITE_RAW_CER", boundary["numeric_equivalence"])
        self.assertEqual(
            self.proposal["prompt_observations"]["unexpected_domain_term_hits_all_dev_and_holdout"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
