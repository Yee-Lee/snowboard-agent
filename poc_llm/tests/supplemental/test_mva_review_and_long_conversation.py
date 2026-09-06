from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from poc_llm.tools.supplemental import run_long_conversation


ROOT = Path(__file__).resolve().parents[3]
MANUAL = ROOT / "poc_llm/evidence/m4b/mva-manual-001"
SCHEMA = ROOT / "poc_llm/contracts/mva/manual-sample-v1.schema.json"


class ManualReviewEvidenceTests(unittest.TestCase):
    def test_all_twelve_sanitized_assessments_validate(self) -> None:
        validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        samples = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(MANUAL.glob("H*.json"))]
        self.assertEqual([sample["case_id"] for sample in samples], [f"H{index:02d}" for index in range(1, 13)])
        for sample in samples:
            validator.validate(sample)
            self.assertFalse({"prompt", "answer", "audio", "raw_prompt", "raw_answer"} & set(sample))

    def test_review_keeps_observed_failures(self) -> None:
        results = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))["overall"]
            for path in MANUAL.glob("H*.json")
        }
        self.assertEqual({case for case, result in results.items() if result == "Fail"}, {"H03", "H05", "H06", "H11"})
        self.assertEqual(sum(result == "Pass" for result in results.values()), 8)


class LongConversationSupplementalTests(unittest.TestCase):
    def test_fixed_public_script_has_twenty_turns(self) -> None:
        self.assertEqual(len(run_long_conversation.PROMPTS), 20)
        self.assertTrue(all(prompt.strip() for prompt in run_long_conversation.PROMPTS))

    def test_evidence_writer_is_private_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            digest = run_long_conversation.exclusive_json(output, {"status": "PASS"})
            self.assertEqual(len(digest), 64)
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                run_long_conversation.exclusive_json(output, {"status": "FAIL"})


if __name__ == "__main__":
    unittest.main()
