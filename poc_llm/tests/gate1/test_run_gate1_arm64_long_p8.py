#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from poc_llm.tools.run_gate1_arm64_long_p8 import (
    HISTORY_COUNT, LONG_PROMPT, response_hash,
)


class Arm64LongP8RunnerTest(unittest.TestCase):
    def test_long_prompt_is_schema_valid(self) -> None:
        schema = json.loads(Path(
            "poc_llm/contracts/m1/prompt-input.schema.json"
        ).read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(LONG_PROMPT)

    def test_response_hash_is_deterministic_and_redacts_content(self) -> None:
        frame = {"response": {"action": "rest", "parameters": {}}}
        value = response_hash(frame)
        self.assertEqual(value, response_hash(frame))
        self.assertEqual(len(value), 64)
        self.assertNotIn("rest", value)

    def test_p8_uses_five_turns(self) -> None:
        self.assertEqual(HISTORY_COUNT, 5)

    def test_batch_is_two_candidate_arm64_only(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_long_p8_batch.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("CAND-LRT-Q25-15B-Q8-R1", source)
        self.assertIn("CAND-LRT-G4E2B-MOBILE-R1", source)
        self.assertNotIn("CAND-LRT-Q25-05B-Q8-R1", source)
        self.assertNotIn("x86", source)

    def test_result_retains_hashes_not_model_text(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_long_p8.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"response_sha256": response_hash(terminal)', source)
        self.assertNotIn('"response": terminal', source)
        self.assertNotIn('"prompt":', source)


if __name__ == "__main__":
    unittest.main()
