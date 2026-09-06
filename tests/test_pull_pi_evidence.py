from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.pull_pi_evidence import DownloadError, verify_archive


def _archive(path: Path, bundle_id: str, *, unsafe_name: str | None = None) -> None:
    manifest = json.dumps({"bundle_id": bundle_id}).encode()
    payload = b"private fixture"
    payload_name = unsafe_name or "payload/result.dat"
    sums = (
        f"{hashlib.sha256(manifest).hexdigest()}  manifest.private.json\n"
        f"{hashlib.sha256(payload).hexdigest()}  {payload_name}\n"
    ).encode()
    with tarfile.open(path, "w:gz") as archive:
        for name, content in (
            ("manifest.private.json", manifest),
            ("SHA256SUMS", sums),
            (payload_name, payload),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


class EvidenceArchiveTests(unittest.TestCase):
    def test_verified_archive_returns_receipt_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.tgz"
            _archive(path, "bundle-001")
            receipt = verify_archive(path, "bundle-001")
            self.assertEqual(receipt["bundle_id"], "bundle-001")
            self.assertRegex(receipt["archive_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(receipt["entry_count"], 3)

    def test_wrong_bundle_and_path_traversal_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.tgz"
            unsafe = root / "unsafe.tgz"
            _archive(valid, "bundle-001")
            _archive(unsafe, "bundle-001", unsafe_name="../outside")
            with self.assertRaises(DownloadError):
                verify_archive(valid, "bundle-002")
            with self.assertRaises(DownloadError):
                verify_archive(unsafe, "bundle-001")

    def test_checksum_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.tgz"
            manifest = b'{"bundle_id":"bundle-001"}'
            sums = ("0" * 64 + "  manifest.private.json\n").encode()
            with tarfile.open(path, "w:gz") as archive:
                for name, content in (
                    ("manifest.private.json", manifest),
                    ("SHA256SUMS", sums),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            with self.assertRaises(DownloadError):
                verify_archive(path, "bundle-001")


if __name__ == "__main__":
    unittest.main()
