#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from poc_llm.tools.run_gate1_arm64_p7_recovery import (
    SmokeFailure,
    cancel_disposition,
    ready_identity,
)


class Arm64P7RecoveryRunnerTest(unittest.TestCase):
    def test_cancel_timeout_is_conditional_escalation(self) -> None:
        self.assertEqual(
            cancel_disposition(None, "request-1", 500),
            "CONDITIONAL_ESCALATION",
        )

    def test_bounded_correlated_cancel_is_pass(self) -> None:
        frame = {"type": "CANCELLED", "request_id": "request-1"}
        self.assertEqual(cancel_disposition(frame, "request-1", 499.9), "PASS")

    def test_late_or_uncorrelated_cancel_is_rejected(self) -> None:
        with self.assertRaises(SmokeFailure):
            cancel_disposition(
                {"type": "CANCELLED", "request_id": "wrong"}, "request-1", 10)
        with self.assertRaises(SmokeFailure):
            cancel_disposition(
                {"type": "CANCELLED", "request_id": "request-1"},
                "request-1", 500.1)

    def test_ready_identity_is_exact_arm64_tuple(self) -> None:
        config = {
            "candidate_id": "candidate", "pairing_revision": "revision",
            "runtime_sha256": "1" * 64, "model_sha256": "2" * 64,
        }
        self.assertEqual(ready_identity(config, "3" * 64), {
            "candidate_id": "candidate", "pairing_revision": "revision",
            "platform": "ubuntu-aarch64", "runtime_sha256": "1" * 64,
            "model_sha256": "2" * 64, "config_sha256": "3" * 64,
        })

    def test_wrapper_is_qwen15_only_and_uses_fresh_path(self) -> None:
        source = Path(
            "poc_llm/tools/run_gate1_arm64_p7_qwen15.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("CAND-LRT-Q25-15B-Q8-R1", source)
        self.assertNotIn("CAND-LRT-Q25-05B-Q8-R1", source)
        self.assertNotIn("CAND-LRT-G4E2B-MOBILE-R1", source)
        self.assertIn("llm-poc-g1-arm64-p7-qwen15-001", source)


if __name__ == "__main__":
    unittest.main()
