from __future__ import annotations

import unittest

from audio_poc.m2a_scorecard import assert_sanitized, validate_formal_row


def valid_document() -> dict:
    return {
        "execution_status": "OBSERVATIONS_COMPLETE_PENDING_COMPARATIVE_REVIEW",
        "candidate_id": "candidate",
        "artifact": {"sha256": "a" * 64},
        "method": {"fixture_count": 20},
        "results": [{"hypothesis_sha256": "b" * 64} for _ in range(20)],
        "raw_transcript_emitted": False,
        "cleanup": {"clean": True},
        "security": {
            "audio_device_opened": False,
            "speaker_playback": False,
            "pcm_emitted_to_report": False,
        },
        "runtime": {
            "loaded_identity": {
                "packages": {"sherpa-onnx": "1.13.5", "sherpa-onnx-core": "1.13.5"},
            }
        },
    }


class M2AScorecardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = {"candidate_id": "candidate", "artifact": {"sha256": "a" * 64}}
        self.runtime = {
            "engine": "sherpa-onnx",
            "runtime_artifacts": [
                {"filename": "sherpa_onnx-1.13.5-cp313-cp313-manylinux_aarch64.whl"},
                {"filename": "sherpa_onnx_core-1.13.5-py3-none-manylinux_aarch64.whl"},
            ],
        }

    def test_accepts_exact_sanitized_formal_row(self) -> None:
        validate_formal_row(valid_document(), self.candidate, self.runtime)

    def test_rejects_diagnostic_row(self) -> None:
        document = valid_document()
        document["execution_status"] = "DIAGNOSTIC_RECHECK_COMPLETE_NOT_SCORECARD"
        with self.assertRaisesRegex(ValueError, "diagnostic or inconclusive"):
            validate_formal_row(document, self.candidate, self.runtime)

    def test_rejects_loaded_runtime_mismatch(self) -> None:
        document = valid_document()
        document["runtime"]["loaded_identity"]["packages"]["sherpa-onnx"] = "1.12.25"
        with self.assertRaisesRegex(ValueError, "loaded runtime"):
            validate_formal_row(document, self.candidate, self.runtime)

    def test_rejects_controlled_transcript_key_at_any_depth(self) -> None:
        with self.assertRaisesRegex(ValueError, "controlled keys"):
            assert_sanitized({"nested": [{"hypothesis": "sensitive"}]})


if __name__ == "__main__":
    unittest.main()
