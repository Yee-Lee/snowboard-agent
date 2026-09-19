from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from poc_llm.m4c_ss.preflight import TargetPreflightError, verify_artifact
from poc_llm.m4c_ss.surface import build_manifest, surface_digest, verify_manifest


ROOT = Path(__file__).resolve().parents[3]


class PreflightTests(unittest.TestCase):
    def test_artifact_verification_binds_size_and_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "artifact.bin"
            path.write_bytes(b"controlled")
            digest = hashlib.sha256(b"controlled").hexdigest()
            self.assertEqual(verify_artifact(path, digest, 10), {"bytes": 10, "sha256": digest})
            with self.assertRaisesRegex(TargetPreflightError, "SIZE_MISMATCH"):
                verify_artifact(path, digest, 11)
            with self.assertRaisesRegex(TargetPreflightError, "DIGEST_MISMATCH"):
                verify_artifact(path, "0" * 64, 10)

    def test_artifact_verification_rejects_relative_and_symlink_paths(self):
        with self.assertRaisesRegex(TargetPreflightError, "PATH_INVALID"):
            verify_artifact(Path("artifact.bin"), "0" * 64)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact.bin"
            artifact.write_bytes(b"controlled")
            link = root / "redirect.bin"
            link.symlink_to(artifact)
            digest = hashlib.sha256(b"controlled").hexdigest()
            with self.assertRaisesRegex(TargetPreflightError, "PATH_INVALID"):
                verify_artifact(link, digest)


class SurfaceTests(unittest.TestCase):
    def test_surface_is_explicit_nonrecursive_and_self_verifying(self):
        manifest = build_manifest(ROOT)
        digest = surface_digest(manifest)
        self.assertEqual(len(digest), 64)
        self.assertNotIn("surface_sha256", manifest)
        verify_manifest(ROOT, json.loads(json.dumps(manifest)), digest)
        changed = json.loads(json.dumps(manifest))
        first = next(iter(changed["files"]))
        changed["files"][first] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SURFACE_IDENTITY_DRIFT"):
            verify_manifest(ROOT, changed, digest)


if __name__ == "__main__":
    unittest.main()
