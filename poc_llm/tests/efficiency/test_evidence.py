from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from poc_llm.efficiency.evidence import EvidenceError, EvidenceWriter, RESOURCE_KEYS, TIMING_KEYS, TOKEN_KEYS, validate_sample


def sample():
    return {
        "format": "m4b-mva-efficiency-sample-v1", "run_id": "EFF-A-J1", "case_id": "A-J1",
        "experiment": "A", "pair": 1, "variant": "J", "implementation_sha": "a" * 40,
        "surface_sha256": "b" * 64, "profile_sha256": "c" * 64, "terminal": "RESULT",
        "status": "INCONCLUSIVE", "timing_ms": {key: None for key in TIMING_KEYS},
        "token_metrics": {key: None for key in TOKEN_KEYS},
        "resources": {key: None for key in RESOURCE_KEYS},
        "cleanup": {"status": "INCONCLUSIVE", "owners_absent": None},
        "missing_reasons": {"speech_end_to_audible_onset": "NO_AUDIO_PROOF"},
        "raw_sanitized_log_path": "EFF-A-J1/samples.jsonl", "audio_onset_reason": "NO_AUDIO_PROOF",
    }


class EvidenceTests(unittest.TestCase):
    def test_valid_sample_roundtrip_and_append_only_directory(self):
        value = sample()
        self.assertEqual(validate_sample(value), value)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = EvidenceWriter(root, value["run_id"])
            writer.append(value)
            self.assertEqual(len(writer.path.read_text().splitlines()), 1)
            with self.assertRaises(FileExistsError):
                EvidenceWriter(root, value["run_id"])

    def test_rejects_paths_raw_fields_nonfinite_and_bad_audio_claim(self):
        for mutation in (
            {"raw_sanitized_log_path": "/private/path"},
            {"audio_onset_reason": "MEASURED"},
            {"extra": "answer"},
        ):
            value = dict(sample(), **mutation)
            with self.subTest(mutation=mutation), self.assertRaises(EvidenceError):
                validate_sample(value)
        value = deepcopy(sample())
        value["timing_ms"]["runtime_ttc"] = float("nan")
        with self.assertRaises(EvidenceError):
            validate_sample(value)


if __name__ == "__main__":
    unittest.main()
