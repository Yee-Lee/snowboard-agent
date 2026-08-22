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
        cls.erratum = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_reference_erratum.json").read_text()
        )
        cls.audit = json.loads(
            (cls.root / "poc_audio/manifests/m2b_c_label_audit_result.json").read_text()
        )

    def test_source_results_are_exact_and_sanitized(self) -> None:
        for identity in self.proposal["source_results"][:5]:
            path = self.root / identity["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), identity["sha256"])
            result = json.loads(path.read_text())
            self.assertFalse(any("hypothesis" in item for item in result["results"]))
            self.assertFalse(any("reference_text" in item for item in result["results"]))

    def test_combined_metrics_recompute_from_prompt_profiles(self) -> None:
        sources = {
            "primary": self.proposal["source_results"][:2],
            "fallback": self.proposal["source_results"][2:4],
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
                correct = sum(item["sentence_correct"] for item in selected)
                if family == "internal":
                    corrected = self.erratum["corrected_internal_combined"][
                        self.proposal[role]["candidate_id"]
                    ]["domain_prompt"]["raw"]
                    edits = corrected["edits"]
                    reference = corrected["reference_chars"]
                    correct = corrected["correct_sentences"]
                self.assertEqual((len(selected), edits, reference), (
                    expected["items"], expected["edits"], expected["reference_chars"],
                ))
                self.assertEqual(round(edits / reference * 100.0, 6), expected["cer_percent"])
                self.assertEqual(correct, expected["correct_sentences"])
                latencies = sorted(item["latency_ms"] for item in selected)
                p50 = latencies[math.ceil(len(latencies) * 0.5) - 1]
                p95 = latencies[math.ceil(len(latencies) * 0.95) - 1]
                self.assertEqual((p50, p95), (expected["latency_p50_ms"], expected["latency_p95_ms"]))

    def test_task_adjusted_metrics_match_formal_result(self) -> None:
        identity = self.proposal["source_results"][4]
        result = json.loads((self.root / identity["path"]).read_text())
        candidate_roles = {
            self.proposal["primary"]["candidate_id"]: "primary",
            self.proposal["fallback"]["candidate_id"]: "fallback",
        }
        for candidate_id, role in candidate_roles.items():
            for family in ("internal", "common_voice"):
                if family == "internal":
                    actual = self.erratum["corrected_internal_combined"][candidate_id][
                        "domain_prompt"
                    ]["task_adjusted"]
                else:
                    actual = result["summary"][candidate_id]["domain_prompt"]["combined"][family][
                        "task_adjusted"
                    ]
                expected = self.proposal["combined_c_task_adjusted_observations"][role][family]
                self.assertEqual(actual["edits"], expected["edits"])
                self.assertEqual(actual["reference_chars"], expected["reference_chars"])
                self.assertEqual(actual["cer_percent"], expected["cer_percent"])
                self.assertEqual(actual["correct_sentences"], expected["correct_sentences"])

    def test_task_adjusted_result_is_metadata_only(self) -> None:
        result_path = self.root / self.proposal["source_results"][4]["path"]
        result = json.loads(result_path.read_text())
        self.assertEqual(len(result["results"]), 96)
        forbidden = {"reference_text", "hypothesis", "task_reference", "task_hypothesis"}
        self.assertTrue(all(forbidden.isdisjoint(row) for row in result["results"]))
        self.assertFalse(result["raw_text_emitted"])

    def test_reference_erratum_is_exact_and_contains_no_transcript(self) -> None:
        identity = self.proposal["source_results"][5]
        path = self.root / identity["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), identity["sha256"])
        serialized = path.read_text()
        for forbidden in ("reference_text", "hypothesis", "User comment"):
            self.assertNotIn(forbidden, serialized)
        self.assertTrue(self.erratum["evidence_policy"]["preserve_original_results"])
        self.assertFalse(self.erratum["evidence_policy"]["rerun_inference"])

    def test_label_audit_is_exact_complete_and_sanitized(self) -> None:
        identity = self.proposal["source_results"][6]
        path = self.root / identity["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), identity["sha256"])
        self.assertEqual(self.audit["status"], "COMPLETE")
        self.assertEqual(
            self.audit["counts"],
            {
                "total": 24,
                "label_ok": 23,
                "label_erratum": 1,
                "audio_quality": 0,
                "speaker_slip": 0,
                "needs_review": 0,
            },
        )
        self.assertEqual(self.audit["controlled_evidence"]["file_mode"], "0600")
        self.assertTrue(all(value is False for value in self.audit["privacy"].values()))

        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value))
            return set()

        self.assertTrue({"reference_text", "hypothesis", "comment"}.isdisjoint(keys(self.audit)))

    def test_proposal_keeps_raw_and_task_scoring_separate(self) -> None:
        boundary = self.proposal["scoring_boundary"]
        self.assertEqual(boundary["runtime_postprocessing"], "NOT_ADDED_BY_THIS_PROPOSAL")
        self.assertEqual(
            boundary["task_adjusted_status"],
            "FORMAL_BOUNDED_C_V1_COMPLETE_SEPARATE_FROM_RAW_CER",
        )
        self.assertEqual(boundary["homophone_and_domain_alias_equivalence"], "NOT_ACCEPTED")
        self.assertEqual(
            self.proposal["prompt_observations"]["unexpected_domain_term_hits_all_dev_and_holdout"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
