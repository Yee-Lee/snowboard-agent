#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import time
import unittest
from pathlib import Path

from poc_llm.tools.run_gate1_arm64_measurement import (
    RssSampler,
    SmokeFailure,
    checked_metrics,
    percentile,
)


def result_frame(**overrides: int | float) -> dict[str, object]:
    metrics: dict[str, int | float] = {
        "init_ms": 100.0,
        "ttft_ms": 200.0,
        "prefill_tokens": 20,
        "prefill_tokens_per_second": 10.0,
        "decode_tokens": 8,
        "decode_tokens_per_second": 5.0,
        "kv_tokens": 28,
    }
    metrics.update(overrides)
    return {"type": "RESULT", "metrics": metrics}


class Arm64MeasurementRunnerTest(unittest.TestCase):
    def test_complete_positive_metrics_are_accepted(self) -> None:
        self.assertEqual(checked_metrics(result_frame())["decode_tokens"], 8)

    def test_missing_metric_is_rejected(self) -> None:
        frame = result_frame()
        del frame["metrics"]["ttft_ms"]  # type: ignore[index]
        with self.assertRaises(SmokeFailure):
            checked_metrics(frame)

    def test_zero_decode_rate_is_rejected(self) -> None:
        with self.assertRaises(SmokeFailure):
            checked_metrics(result_frame(decode_tokens_per_second=0.0))

    def test_more_than_sixteen_decode_tokens_is_rejected(self) -> None:
        with self.assertRaises(SmokeFailure):
            checked_metrics(result_frame(decode_tokens=17))

    def test_percentile_uses_nearest_rank(self) -> None:
        self.assertEqual(percentile([9, 1, 5, 3], 50), 3)
        self.assertEqual(percentile([9, 1, 5, 3], 95), 9)

    def test_rss_sampler_observes_child_and_batch_excludes_deferred_model(self) -> None:
        process = subprocess.Popen(
            ["python3", "-c", "import time; value=bytearray(1000000); time.sleep(0.2)"]
        )
        with RssSampler(process.pid) as sampler:
            process.wait(timeout=2)
            time.sleep(0.03)
        self.assertGreater(sampler.peak_kib, 0)
        batch = Path(
            "poc_llm/tools/run_gate1_arm64_measurement_batch.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("CAND-LRT-Q25-15B-Q8-R1", batch)
        self.assertIn("CAND-LRT-G4E2B-MOBILE-R1", batch)
        self.assertNotIn("CAND-LRT-Q25-05B-Q8-R1", batch)


if __name__ == "__main__":
    unittest.main()
