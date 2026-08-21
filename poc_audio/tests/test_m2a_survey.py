from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path

from audio_poc.m2a_asr_worker import _read_wav
from audio_poc.m2a_survey import execution_status, numeric_summary, summarize


class M2ASurveyTests(unittest.TestCase):
    def test_diagnostic_recheck_cannot_be_mistaken_for_scorecard_row(self) -> None:
        self.assertEqual(
            execution_status(True, 1),
            "DIAGNOSTIC_RECHECK_COMPLETE_NOT_SCORECARD",
        )
        self.assertEqual(
            execution_status(True, None),
            "OBSERVATIONS_COMPLETE_PENDING_COMPARATIVE_REVIEW",
        )
        self.assertEqual(execution_status(False, 2), "INCONCLUSIVE_RETAINED")

    def test_numeric_summary_uses_nearest_rank(self) -> None:
        self.assertEqual(
            numeric_summary([4.0, 1.0, 3.0, 2.0]),
            {"min": 1.0, "p50": 2.0, "p95": 4.0, "max": 4.0},
        )

    def test_summary_is_comparative_and_category_scoped(self) -> None:
        results = [
            {
                "category": "taiwan_mandarin", "reference_length": 2,
                "edit_distance": 0, "sentence_correct": True,
                "latency_ms": 100.0, "rtf": 0.1, "peak_rss_mib": 20.0,
            },
            {
                "category": "common_voice", "reference_length": 2,
                "edit_distance": 1, "sentence_correct": False,
                "latency_ms": 200.0, "rtf": 0.2, "peak_rss_mib": 21.0,
            },
        ]
        summary = summarize(results)
        self.assertEqual(summary["overall_cer_percent"], 25.0)
        self.assertEqual(summary["latency_ms"]["p95"], 200.0)
        self.assertNotIn("pass", json.dumps(summary).lower())
        self.assertNotIn("winner", json.dumps(summary).lower())

    def test_worker_rejects_sample_rate_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong-rate.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"\0\0" * 32)
            with self.assertRaisesRegex(ValueError, "16 kHz mono"):
                _read_wav(path)


if __name__ == "__main__":
    unittest.main()
