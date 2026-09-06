from pathlib import Path
import json
import os
import tempfile
import unittest

from poc_llm.tools.collect_llm_storage_inventory import byte_counts, safe_statuses, walk_metadata
from poc_llm.tools.prepare_curation_postcheck import prepare


class StorageInventoryTests(unittest.TestCase):
    def test_protected_hold_migration_is_complete_and_verify_only(self):
        root = Path(__file__).resolve().parents[3]
        cleanup = json.loads(
            (root / "poc_llm/curation/pi-cleanup-manifest-v1.json").read_text()
        )
        migration = json.loads(
            (root / "poc_llm/curation/protected-hold-migration-v1.json").read_text()
        )
        self.assertEqual(migration["covered_phase1_holds"], cleanup["protected_holds"])
        self.assertEqual(
            {item["phase1_hold"] for item in migration["items"]},
            set(cleanup["protected_holds"]),
        )
        for item in migration["items"]:
            self.assertEqual(item["action"], "verify-only")
            self.assertFalse(item["materialized"])
            self.assertTrue(item["hold"])
            self.assertTrue(item["source_locator"])
            self.assertIn("sha256", item["source_identity"])
            self.assertIn("size_bytes", item["source_identity"])
            self.assertIn("kind", item["target_identity"])
            self.assertIn("object_id", item["target_identity"])
            self.assertIn("locator", item["target_identity"])

    def test_post_download_cleanup_stays_closed_and_has_exact_gates(self):
        root = Path(__file__).resolve().parents[3]
        plan = json.loads(
            (root / "poc_llm/curation/pi-post-download-cleanup-v1.json").read_text()
        )
        self.assertFalse(plan["deletion_authorized"])
        self.assertEqual(len(plan["items"]), 57)
        self.assertEqual(
            {item["cleanup_class"] for item in plan["items"]},
            {"a_download_receipt", "b_canonical_materialization", "c_unresolved_hold"},
        )
        for item in plan["items"]:
            self.assertFalse(item["delete_after_verified_receipt"])
            if item["cleanup_class"] != "c_unresolved_hold":
                self.assertIsInstance(item["allocated_bytes"], int)
                self.assertEqual(item["reclaim_bytes"], item["allocated_bytes"])
                self.assertTrue(item["archive_bundle_id"])
                self.assertEqual(
                    item["required_local_receipt"]["state"],
                    "REQUIRED_NOT_YET_RECORDED",
                )
                self.assertNotIn("*", item["logical_locator"])

    def test_postcheck_retains_unknowns_and_never_authorizes_cleanup(self):
        source = {"scope_roots": ["/private/work", "/private/products", "/private/artifacts", "/private/runs"],
                  "observed_utc": "2026-09-06T00:00:00Z", "collector_sha256": "a" * 64,
                  "whole_scope": {}, "runtime_trees": [], "pi_origin_llm_sha": "b" * 40,
                  "pi_llm_m4_tag_object": None, "pi_llm_m4_tag_commit": None,
                  "active_references": {"references": [], "inaccessible_or_exited_process_count": 1},
                  "known_limits": [], "items": [{"original_path": "/private/runs/preflight-pass",
                  "apparent_file_bytes": 42, "unique_file_bytes": 42, "allocated_unique_bytes": 4096}]}
        inventory, manifest = prepare(source, "c" * 64)
        self.assertEqual(inventory["items"][0]["locator"], "PI_M4B_RUNS/preflight-pass")
        self.assertIsNone(inventory["items"][0]["overall_result"])
        self.assertFalse(manifest["execution_authorized"])
        self.assertEqual(manifest["immediate_reclaimable_unique_bytes"], 0)
        self.assertIsNone(manifest["conditional_reclaimable_unique_bytes"])
        self.assertEqual(manifest["items"][0]["category"], "retain")
        source["items"][0]["original_path"] = "/unmapped/private"
        with self.assertRaises(ValueError):
            prepare(source, "c" * 64)

    def test_hardlinks_are_not_double_counted_and_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one").write_bytes(b"public fixture")
            os.link(root / "one", root / "two")
            (root / "outside").symlink_to("/unreadable-outside-scope")
            rows = walk_metadata(root)
            counts = byte_counts(rows)
            self.assertEqual(counts["apparent_file_bytes"], 28)
            self.assertEqual(counts["unique_file_bytes"], 14)
            self.assertEqual(len([row for row in rows if row["kind"] == "symlink"]), 1)
            self.assertGreaterEqual(counts["allocated_unique_bytes"], root.stat().st_blocks * 512)

    def test_status_extraction_does_not_export_private_strings_or_infer_overall(self):
        value = {"summary": {"status": "Fail", "answer": "PRIVATE", "message": "PRIVATE"},
                 "prompt": "PRIVATE", "checks": [{"status": "Pass", "text": "PRIVATE"}],
                 "result": "PRIVATE", "untrusted_key": {"status": "PASS"}}
        self.assertEqual(safe_statuses(value), [{"json_pointer": "/summary/status", "value": "Fail"},
                                              {"json_pointer": "/checks/0/status", "value": "Pass"}])


if __name__ == "__main__":
    unittest.main()
