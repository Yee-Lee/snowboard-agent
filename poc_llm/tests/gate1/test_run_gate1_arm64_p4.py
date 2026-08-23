#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from poc_llm.tools.run_gate1_arm64_p4 import (
    COLD_COUNT, HOT_COUNT, WARMUP_COUNT, aggregate,
)


class Arm64P4RunnerTest(unittest.TestCase):
    def test_frozen_repetition_counts(self) -> None:
        self.assertEqual((WARMUP_COUNT, COLD_COUNT, HOT_COUNT), (3, 3, 20))

    def test_aggregate_uses_raw_native_metrics(self) -> None:
        samples = [
            {"wall_ms": float(i), "metrics": {
                "ttft_ms": float(i), "prefill_tokens_per_second": float(i),
                "decode_tokens_per_second": float(i),
            }}
            for i in range(1, 21)
        ]
        value = aggregate(samples)
        self.assertEqual(value["ttft_ms_p50"], 10.0)
        self.assertEqual(value["ttft_ms_p95"], 19.0)
        self.assertEqual(value["decode_tps_p50"], 10.0)

    def test_batch_is_two_candidate_arm64_only(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p4_batch.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("CAND-LRT-Q25-15B-Q8-R1", source)
        self.assertIn("CAND-LRT-G4E2B-MOBILE-R1", source)
        self.assertNotIn("CAND-LRT-Q25-05B-Q8-R1", source)
        self.assertNotIn("x86", source)

    def test_runner_never_retains_prompt_or_model_text(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p4.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"response": terminal', source)
        self.assertNotIn('"prompt":', source)


if __name__ == "__main__":
    unittest.main()
