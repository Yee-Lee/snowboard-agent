import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asr_r1.m1_baseline import CapturedRun, _run_nemotron, run_monitored


class MonitoredProcessTest(unittest.TestCase):
    def test_success_records_process_tree_rss_without_exposing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = run_monitored(
                [sys.executable, "-c", 'print("ok")'],
                timeout_seconds=2,
                memory_budget_bytes=200_000_000,
                cwd=Path(temporary),
            )
        self.assertEqual("COMPLETED", run.status)
        self.assertEqual(0, run.returncode)
        self.assertEqual("ok", run.stdout.strip())
        self.assertGreater(run.peak_process_tree_rss_bytes, 0)

    def test_timeout_is_typed_and_bounded(self) -> None:
        run = run_monitored(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.05,
            memory_budget_bytes=200_000_000,
        )
        self.assertEqual("TIMEOUT", run.status)
        self.assertLess(run.elapsed_seconds, 2)

    def test_rss_limit_terminates_process(self) -> None:
        run = run_monitored(
            [
                sys.executable,
                "-c",
                "import time; value=bytearray(30000000); time.sleep(2)",
            ],
            timeout_seconds=2,
            memory_budget_bytes=15_000_000,
        )
        self.assertEqual("RSS_LIMIT_EXCEEDED", run.status)
        self.assertGreater(run.peak_process_tree_rss_bytes, 15_000_000)


class NemotronResultTest(unittest.TestCase):
    def test_native_rtfx_is_converted_and_transcript_is_hashed(self) -> None:
        smoke_payload = json.dumps({"text": "controlled words", "duration": 2.66})
        bench_payload = json.dumps(
            {
                "load_ms": 125.0,
                "runs": [
                    {
                        "audio_seconds": 2.66,
                        "wall_seconds": 1.33,
                        "rtfx": 2.0,
                    }
                ],
            }
        )
        runs = [
            CapturedRun("COMPLETED", 0, 1.5, 700_000_000, smoke_payload, ""),
            CapturedRun("COMPLETED", 0, 1.4, 710_000_000, bench_payload, ""),
        ]
        with patch("asr_r1.m1_baseline.run_monitored", side_effect=runs):
            result = _run_nemotron(
                "nemotron-test",
                Path("external-runtime"),
                Path("external-model"),
                Path("external-fixture"),
                timeout_seconds=10,
                memory_budget_bytes=1_000_000_000,
            )
        self.assertTrue(result["smoke_completed"])
        self.assertEqual(0.5, result["rtf"])
        self.assertEqual(710_000_000, result["peak_process_tree_rss_bytes"])
        self.assertNotIn("controlled words", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
