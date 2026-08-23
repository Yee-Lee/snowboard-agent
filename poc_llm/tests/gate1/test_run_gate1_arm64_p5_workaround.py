#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from poc_llm.tools.run_gate1_arm64_p5_workaround_child import (
    WORKAROUND_TIMEOUT_MS, config_digest, effective_config,
)


class Arm64P5WorkaroundTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = {
            "candidate_id": "CAND-TEST", "generate_timeout_ms": 15000,
            "max_input_tokens": 128, "max_output_tokens": 16,
        }

    def test_effective_config_changes_only_timeout(self) -> None:
        value = effective_config(self.base)
        changed = [key for key in self.base if self.base[key] != value[key]]
        self.assertEqual(changed, ["generate_timeout_ms"])
        self.assertEqual(value["generate_timeout_ms"], 1000)

    def test_base_config_is_not_mutated(self) -> None:
        effective_config(self.base)
        self.assertEqual(self.base["generate_timeout_ms"], 15000)

    def test_effective_config_digest_is_deterministic(self) -> None:
        value = effective_config(self.base)
        self.assertEqual(config_digest(value), config_digest(value))
        self.assertEqual(len(config_digest(value)), 64)

    def test_timeout_is_fixed_not_operator_selectable(self) -> None:
        self.assertEqual(WORKAROUND_TIMEOUT_MS, 1000)
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p5_workaround_child.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--timeout', source)

    def test_result_cannot_claim_contract_p5_pass(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p5_workaround.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"contract_p5_disposition": "INCONCLUSIVE"', source)
        self.assertIn('"result": "INCONCLUSIVE"', source)

    def test_batch_is_two_candidate_arm64_only(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p5_workaround_batch.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("CAND-LRT-Q25-15B-Q8-R1", source)
        self.assertIn("CAND-LRT-G4E2B-MOBILE-R1", source)
        self.assertNotIn("CAND-LRT-Q25-05B-Q8-R1", source)
        self.assertNotIn("x86", source)


if __name__ == "__main__":
    unittest.main()
