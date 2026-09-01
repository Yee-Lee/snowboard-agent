import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asr_r1.m1_baseline import (
    CapturedRun,
    _environment_fields,
    _run_nemotron,
    _verify_sherpa_runtime_artifacts,
    run_monitored,
)


class MonitoredProcessTest(unittest.TestCase):
    def test_environment_is_explicitly_not_pi5(self) -> None:
        environment = _environment_fields()
        self.assertEqual(
            "WORKSTATION_FEASIBILITY_NOT_PI5",
            environment["execution_environment"],
        )
        self.assertFalse(environment["pi5_hardware_result"])
        self.assertFalse(environment["gpu_acceleration"])
        self.assertGreater(environment["affinity_vcpu_count"], 0)

    def test_success_records_process_tree_rss_without_exposing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = run_monitored(
                [sys.executable, "-c", 'print("ok")'],
                timeout_seconds=2,
                cwd=Path(temporary),
            )
        self.assertEqual("COMPLETED", run.status)
        self.assertEqual(0, run.returncode)
        self.assertEqual("ok", run.stdout.strip())
        self.assertGreater(run.peak_process_tree_rss_bytes, 0)
        self.assertGreater(run.peak_process_tree_pss_bytes, 0)
        self.assertGreaterEqual(run.peak_process_tree_threads, 1)
        self.assertGreaterEqual(run.process_tree_cpu_seconds, 0)

    def test_timeout_is_typed_and_bounded(self) -> None:
        run = run_monitored(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.05,
        )
        self.assertEqual("TIMEOUT", run.status)
        self.assertLess(run.elapsed_seconds, 2)

    def test_high_rss_is_observed_without_termination(self) -> None:
        run = run_monitored(
            [
                sys.executable,
                "-c",
                "value=bytearray(30000000); print(len(value))",
            ],
            timeout_seconds=2,
        )
        self.assertEqual("COMPLETED", run.status)
        self.assertEqual(0, run.returncode)
        self.assertGreater(run.peak_process_tree_rss_bytes, 15_000_000)


class NemotronResultTest(unittest.TestCase):
    def test_native_rtfx_is_converted_and_transcript_is_hashed(self) -> None:
        smoke_payload = json.dumps({"text": "controlled words", "duration": 2.66})
        bench_payload = json.dumps(
            {
                "load_ms": 125.0,
                "warmup_ms": 250.0,
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
                memory_reference_bytes=1_000_000_000,
            )
        self.assertTrue(result["smoke_completed"])
        self.assertEqual(0.5, result["full_utterance_rtf"])
        self.assertEqual(
            1.33, result["full_utterance_decode_wall_seconds"]
        )
        self.assertEqual(0.25, result["benchmark_warmup_seconds"])
        self.assertEqual(710_000_000, result["peak_process_tree_rss_bytes"])
        self.assertFalse(result["rss_above_reference"])
        self.assertEqual(
            "WORKSTATION_FEASIBILITY_NOT_PI5",
            result["execution_environment"],
        )
        self.assertNotIn("controlled words", json.dumps(result))


class RuntimeClosureTest(unittest.TestCase):
    def test_exact_two_wheel_closure_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "runtime-one.whl"
            second = root / "runtime-two.whl"
            first.write_bytes(b"one")
            second.write_bytes(b"two")
            identity = {
                "shared_sherpa_runtime": {
                    "workstation_cp312_x86_64_wheels": [
                        {
                            "filename": first.name,
                            "size_bytes": 3,
                            "sha256": hashlib.sha256(b"one").hexdigest(),
                        },
                        {
                            "filename": second.name,
                            "size_bytes": 3,
                            "sha256": hashlib.sha256(b"two").hexdigest(),
                        },
                    ]
                }
            }
            with patch("asr_r1.m1_baseline._load_json", return_value=identity):
                _verify_sherpa_runtime_artifacts([first, second], root / "repo")
                with self.assertRaisesRegex(ValueError, "exact sherpa"):
                    _verify_sherpa_runtime_artifacts([first], root / "repo")


if __name__ == "__main__":
    unittest.main()
