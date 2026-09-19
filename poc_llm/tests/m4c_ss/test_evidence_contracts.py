from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from poc_llm.m4c_ss.evidence import EvidenceError, SanitizedEvidenceWriter, bundle_manifest, require_sanitized


ROOT = Path(__file__).resolve().parents[3]


class ContractAssetTests(unittest.TestCase):
    def test_profile_and_catalog_are_internally_consistent(self):
        profile = json.loads((ROOT / "poc_llm/contracts/m4c_ss/m4c-ss-profile-001.json").read_text())
        catalog = json.loads((ROOT / "poc_llm/fixtures/m4c_ss/public-catalog-001.json").read_text())
        self.assertEqual(profile["expected_case_count"], 82)
        self.assertEqual(profile["queue"], {
            "maximum_pending_fragments": 2,
            "maximum_pending_utf8_bytes": 256,
        })
        for trace in catalog["mapping_traces"].values():
            self.assertEqual("".join(trace["fragments"]), trace["terminal_text"])

    def test_sanitized_sample_schema_accepts_minimal_record(self):
        schema = json.loads((ROOT / "poc_llm/contracts/m4c_ss/sanitized-sample-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        sample = {
            "format": "m4c-ss-sanitized-sample-v1",
            "case_key": "controller:C01-ONE:-:-:-:-",
            "partition": "controller",
            "status": "PASS",
            "identity": {
                "execution_sha": "a" * 40, "surface_sha256": "b" * 64,
                "profile_sha256": "c" * 64, "private_bundle_sha256": None,
                "private_locator": None,
            },
            "text_facts": {
                "terminal_text_sha256": "d" * 64, "terminal_codepoints": 4,
                "fragment_count": 1, "fragment_sha256": ["e" * 64],
            },
            "timings_ns": {"llm_send": 1, "acoustic_onset": None},
            "queue": {"high_water_fragments": 1, "high_water_utf8_bytes": 12, "backpressure_count": 0},
            "resources": {"swap_delta_bytes": 0},
            "cleanup": {"owner_absent": True, "pending_fragments": 0,
                        "audio_owner_absent": True, "normal_success_published": True},
            "null_reasons": {"acoustic_onset": "NO_TARGET_CAPTURE"},
        }
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(sample)), [])


class EvidenceWriterTests(unittest.TestCase):
    def test_append_only_writer_and_manifest_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = SanitizedEvidenceWriter(Path(directory), "RUN-001", "controller:C01")
            writer.append({"event": "ADMISSION", "sequence": 0})
            manifest = writer.finalize({"status": "PASS", "terminal_sha256": "a" * 64})
            self.assertEqual([item["path"] for item in manifest["files"]], ["events.jsonl", "summary.json"])
            self.assertEqual(manifest, bundle_manifest(writer.directory))
            with self.assertRaises(FileExistsError):
                SanitizedEvidenceWriter(Path(directory), "RUN-001", "controller:C01")

    def test_private_fields_and_nonfinite_values_fail_before_write(self):
        for value in ({"prompt": "private"}, {"nested": {"pcm_sha256": "x"}}, {"session_id": "x"}):
            with self.subTest(value=value), self.assertRaisesRegex(EvidenceError, "PRIVATE_FIELD"):
                require_sanitized(value)
        with tempfile.TemporaryDirectory() as directory:
            writer = SanitizedEvidenceWriter(Path(directory), "RUN-002", "controller:C02")
            with self.assertRaisesRegex(EvidenceError, "NON_CANONICAL_VALUE"):
                writer.append({"value": float("nan")})

    def test_sanitized_audio_timing_and_cleanup_facts_are_allowed(self):
        require_sanitized({
            "audio_first_write_ns": 10,
            "acoustic_onset_ns": 20,
            "audio_owner_absent": True,
        })


if __name__ == "__main__":
    unittest.main()
