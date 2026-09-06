from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from poc_llm.tools.export_private_evidence import ExportError, list_ready


class PrivateEvidenceExporterTests(unittest.TestCase):
    def fixture(self, root: Path, *, archive_name: str = "payload/result.json",
                source: str = "source/result.json") -> Path:
        bundle = root / "bundle-001"
        payload = bundle / "source/result.json"
        payload.parent.mkdir(parents=True)
        payload.write_bytes(b'{"public_fixture":true}\n')
        manifest = {
            "format": "llm-private-evidence-ready-v1",
            "bundle_id": "bundle-001",
            "ready": True,
            "entries": [{
                "archive_name": archive_name,
                "source": source,
                "size_bytes": payload.stat().st_size,
                "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
            }],
        }
        manifest_path = bundle / "manifest.private.json"
        manifest_path.write_text(json.dumps(manifest))
        manifest_path.chmod(0o600)
        return manifest_path

    def command(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "poc_llm.tools.export_private_evidence", *args,
             "--ready-root", str(root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_exact_list_schema_and_stream_stdout_is_only_gzip_tar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.fixture(root)
            listed = self.command(root, "list-ready")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            value = json.loads(listed.stdout)
            self.assertEqual(set(value), {"schema_version", "bundles"})
            self.assertEqual(set(value["bundles"][0]), {"bundle_id", "estimated_bytes"})
            self.assertNotIn(str(root).encode(), listed.stdout)
            streamed = self.command(root, "stream", "--bundle-id", "bundle-001")
            self.assertEqual(streamed.returncode, 0, streamed.stderr)
            with tarfile.open(fileobj=io.BytesIO(streamed.stdout), mode="r:gz") as archive:
                self.assertTrue(all(item.isfile() or item.isdir() for item in archive))
                self.assertEqual(
                    archive.getnames(),
                    ["manifest.private.json", "SHA256SUMS", "payload", "payload/result.json"],
                )
                payload = archive.extractfile("payload/result.json").read()
                sums = archive.extractfile("SHA256SUMS").read().decode()
            self.assertEqual(
                sums,
                f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  manifest.private.json\n"
                f"{hashlib.sha256(payload).hexdigest()}  payload/result.json\n",
            )

    def test_traversal_duplicate_symlink_and_missing_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.fixture(root, archive_name="../escape")
            with self.assertRaises(ExportError):
                list_ready(root)
            manifest = json.loads(manifest_path.read_text())
            manifest["entries"][0]["archive_name"] = "payload/result.json"
            manifest["entries"] = [manifest["entries"][0], manifest["entries"][0]]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ExportError):
                list_ready(root)
            manifest["entries"] = [manifest["entries"][0]]
            manifest["entries"][0]["source"] = "source/missing"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ExportError):
                list_ready(root)
            manifest["entries"][0]["source"] = "source/link"
            manifest_path.write_text(json.dumps(manifest))
            (root / "bundle-001/source/link").symlink_to("result.json")
            with self.assertRaises(ExportError):
                list_ready(root)

    def test_checksum_mismatch_and_missing_source_emit_no_archive_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.fixture(root)
            manifest = json.loads(manifest_path.read_text())
            manifest["entries"][0]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest))
            result = self.command(root, "stream", "--bundle-id", "bundle-001")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            manifest["entries"][0]["sha256"] = hashlib.sha256(
                b'{"public_fixture":true}\n'
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            (root / "bundle-001/source/result.json").unlink()
            result = self.command(root, "stream", "--bundle-id", "bundle-001")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
