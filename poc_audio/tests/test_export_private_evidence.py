import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "poc_audio/tools/export_private_evidence.py"
sys.path.insert(0, str(TOOL.parent))
from export_private_evidence import list_ready  # noqa: E402


class PrivateEvidenceExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ready = self.root / "ready"
        self.ready.mkdir()
        self.ready.chmod(0o700)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def bundle(self, *, archive_name: str = "result.json", missing: bool = False) -> Path:
        payload = self.ready / "result.json"
        data = b'{"result":"PASS"}\n'
        if not missing:
            payload.write_bytes(data)
            payload.chmod(0o600)
        manifest = self.ready / "bundle-001.private.json"
        manifest.write_text(json.dumps({
            "schema_version": "1.0", "status": "READY", "bundle_id": "bundle-001",
            "payload": [{
                "source": "result.json", "archive_name": archive_name,
                "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            }],
        }))
        manifest.chmod(0o600)
        return manifest

    def test_list_ready_exposes_no_physical_path(self) -> None:
        self.bundle()
        output = json.dumps(list_ready(self.ready))
        self.assertIn("bundle-001", output)
        self.assertNotIn(str(self.root), output)

    def test_stream_stdout_is_archive_only(self) -> None:
        self.bundle()
        process = subprocess.run(
            [sys.executable, str(TOOL), "stream", "--ready-root", str(self.ready),
             "--bundle-id", "bundle-001"],
            capture_output=True, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        with tarfile.open(fileobj=io.BytesIO(process.stdout), mode="r:gz") as archive:
            self.assertEqual(
                archive.getnames(),
                ["manifest.private.json", "SHA256SUMS", "payload/result.json"],
            )
        self.assertNotIn(b"streamed", process.stdout)
        self.assertIn(b"streamed", process.stderr)

    def test_path_traversal_is_rejected(self) -> None:
        self.bundle(archive_name="../private.json")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            list_ready(self.ready)

    def test_checksum_mismatch_is_rejected(self) -> None:
        self.bundle()
        (self.ready / "result.json").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            list_ready(self.ready)

    def test_missing_payload_fails_closed_before_stdout(self) -> None:
        self.bundle(missing=True)
        process = subprocess.run(
            [sys.executable, str(TOOL), "stream", "--ready-root", str(self.ready),
             "--bundle-id", "bundle-001"],
            capture_output=True, check=False,
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(process.stdout, b"")

    def test_symlink_payload_is_rejected(self) -> None:
        outside = self.root / "outside.json"
        outside.write_bytes(b'{"result":"PASS"}\n')
        (self.ready / "result.json").symlink_to(outside)
        self.bundle(missing=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            list_ready(self.ready)

    def test_nonprivate_root_or_payload_is_rejected(self) -> None:
        self.bundle()
        self.ready.chmod(0o750)
        with self.assertRaisesRegex(ValueError, "ready root must be owner-only"):
            list_ready(self.ready)
        self.ready.chmod(0o700)
        (self.ready / "result.json").chmod(0o640)
        with self.assertRaisesRegex(ValueError, "payload must be owner-only"):
            list_ready(self.ready)


if __name__ == "__main__":
    unittest.main()
