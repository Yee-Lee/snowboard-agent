from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness import mva_surface as surface


ROOT = Path(__file__).resolve().parents[3]


class MvaSurfaceTests(unittest.TestCase):
    def test_checkout_roundtrip_is_deterministic_and_nonrecursive(self):
        manifest = surface.build_manifest(ROOT)
        self.assertEqual(manifest, surface.build_manifest(ROOT))
        self.assertNotIn("implementation_sha", manifest)
        self.assertNotIn("surface_sha256", manifest)
        self.assertIn("poc_llm/harness/mva_contract.py", manifest["files"])
        surface.verify_manifest(ROOT, manifest, surface.surface_digest(manifest))

    def test_deleted_inventory_entry_rejected_even_with_recomputed_digest(self):
        manifest = surface.build_manifest(ROOT)
        del manifest["files"]["poc_llm/harness/mva_litert_backend.py"]
        with self.assertRaises(surface.SurfaceError):
            surface.verify_manifest(ROOT, manifest, surface.surface_digest(manifest))

    def test_extra_receipt_and_forged_hash_rejected(self):
        original = surface.build_manifest(ROOT)
        for name in ("receipt.json", "poc_llm/harness/mva_contract.py"):
            manifest = copy.deepcopy(original)
            manifest["files"][name] = "0" * 64
            with self.subTest(name=name), self.assertRaises(surface.SurfaceError):
                surface.verify_manifest(ROOT, manifest, surface.surface_digest(manifest))

    def test_untrusted_digest_rejected(self):
        with self.assertRaises(surface.SurfaceError):
            surface.verify_manifest(ROOT, surface.build_manifest(ROOT), "0" * 64)

    def test_file_change_invalidates_previously_valid_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_bytes(b"original\n")
            with patch.object(surface, "SURFACE_FILES", ("source.py",)):
                manifest = surface.build_manifest(root)
                source.write_bytes(b"changed\n")
                with self.assertRaises(surface.SurfaceError):
                    surface.verify_manifest(root, manifest, surface.surface_digest(manifest))

    def test_path_escape_missing_duplicate_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_bytes(b"source")
            (root / "link.py").symlink_to(root / "source.py")
            for names in (("../source.py",), ("/source.py",), ("./source.py",),
                          ("missing.py",), ("link.py",), ("source.py", "source.py")):
                with self.subTest(names=names), patch.object(surface, "SURFACE_FILES", names):
                    with self.assertRaises(surface.SurfaceError):
                        surface.build_manifest(root)


if __name__ == "__main__":
    unittest.main()
