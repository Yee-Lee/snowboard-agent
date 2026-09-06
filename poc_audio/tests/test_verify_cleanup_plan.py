import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "poc_audio/tools/verify_cleanup_plan.py"
SHA = "a" * 64


class CleanupPlanVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_plan(self, expected_hash, expected_size, receipt: dict) -> dict:
        manifest = self.root / "manifest.json"
        receipts = self.root / "receipts.json"
        conditions = self.root / "conditions.json"
        manifest.write_text(json.dumps({
            "entries": [{
                "locator": "PI_AUDIO_WORKSPACE/scratch",
                "delete_after_verified_receipt": True,
                "active_references": [],
                "archive_bundle_id": "bundle-001",
                "required_local_receipt_hash": expected_hash,
                "required_local_receipt_size": expected_size,
                "preflight_conditions": [
                    "private_bundle_download_verified", "reference_check_clean",
                ],
            }],
        }))
        receipts.write_text(json.dumps({"bundles": [receipt]}))
        conditions.write_text(json.dumps({"satisfied": [
            "private_bundle_download_verified", "reference_check_clean",
        ]}))
        completed = subprocess.run(
            [sys.executable, str(TOOL), "--manifest", str(manifest),
             "--receipts", str(receipts), "--conditions", str(conditions)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(completed.stdout)

    def test_null_receipt_values_never_become_eligible(self) -> None:
        result = self.run_plan(None, None, {
            "bundle_id": "bundle-001", "archive_sha256": None, "archive_bytes": None,
        })
        self.assertEqual(result, {"schema_version": 1, "dry_run": True, "eligible": []})

    def test_exact_nonempty_receipt_can_be_listed_in_dry_run(self) -> None:
        result = self.run_plan(SHA, 123, {
            "bundle_id": "bundle-001", "archive_sha256": SHA, "archive_bytes": 123,
        })
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["eligible"], ["PI_AUDIO_WORKSPACE/scratch"])

    def test_mismatched_receipt_remains_ineligible(self) -> None:
        result = self.run_plan(SHA, 123, {
            "bundle_id": "bundle-001", "archive_sha256": "b" * 64,
            "archive_bytes": 123,
        })
        self.assertEqual(result["eligible"], [])


if __name__ == "__main__":
    unittest.main()
