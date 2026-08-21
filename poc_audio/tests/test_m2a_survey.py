from __future__ import annotations

import copy
import json
import tempfile
import unittest
import wave
from pathlib import Path

from audio_poc.m2a_asr_worker import _read_wav
from audio_poc.m2a_survey import (
    executable_path_preserving_venv,
    execution_status,
    expected_wheel_packages,
    load_m2b_probe,
    numeric_summary,
    summarize,
)


class M2ASurveyTests(unittest.TestCase):
    def test_tracked_base_q8_probe_is_one_variable_only(self) -> None:
        root = Path(__file__).resolve().parents[2]
        packet = json.loads(
            (root / "poc_audio/manifests/m4a_m2a_common_packet.json").read_text(encoding="utf-8")
        )
        row, probe = load_m2b_probe(
            root / "poc_audio/manifests/m2b_base_q8_probe.json", packet,
        )
        self.assertEqual(row["artifact"]["filename"], "ggml-base-q8_0.bin")
        self.assertEqual(probe["single_variable"]["name"], "model_quantization")

    def test_base_q8_probe_rejects_changed_frozen_control(self) -> None:
        root = Path(__file__).resolve().parents[2]
        packet = json.loads(
            (root / "poc_audio/manifests/m4a_m2a_common_packet.json").read_text(encoding="utf-8")
        )
        probe = json.loads(
            (root / "poc_audio/manifests/m2b_base_q8_probe.json").read_text(encoding="utf-8")
        )
        changed = copy.deepcopy(probe)
        changed["fixed_controls"]["threads"] = 3
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen control"):
                load_m2b_probe(path, packet)

    def test_runtime_python_path_preserves_venv_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "python-target"
            target.write_text("executable", encoding="utf-8")
            target.chmod(0o755)
            venv_python = Path(directory) / "python"
            venv_python.symlink_to(target)
            self.assertEqual(executable_path_preserving_venv(venv_python), venv_python)
            self.assertNotEqual(executable_path_preserving_venv(venv_python), target)

    def test_expected_wheel_packages_covers_exact_closure(self) -> None:
        runtime = {
            "runtime_artifacts": [
                {"filename": "sherpa_onnx-1.13.5-cp313-cp313-manylinux_aarch64.whl"},
                {"filename": "sherpa_onnx_core-1.13.5-py3-none-manylinux_aarch64.whl"},
            ]
        }
        self.assertEqual(
            expected_wheel_packages(runtime),
            {"sherpa-onnx": "1.13.5", "sherpa-onnx-core": "1.13.5"},
        )

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
        self.assertEqual(
            execution_status(True, None, True),
            "M2B_PROBE_OBSERVATIONS_COMPLETE_PENDING_DELTA_REVIEW",
        )
        self.assertEqual(
            execution_status(True, None, True, 2),
            "M2B_DIAGNOSTIC_RECHECK_COMPLETE_NOT_DELTA_TABLE",
        )

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
