from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.m4c_ss.preflight import (
    TargetPreflightError,
    verify_artifact,
    verify_private_receipt,
    verify_usb_microphone_inventory,
)
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

    def test_private_receipt_binds_complete_usb_capture_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            artifacts = {}
            profile = {
                "llm": {}, "tts": {},
                "acoustic_measurement": {
                    "capture_transport": "usb",
                    "capture_card_id": "Audio",
                    "capture_identity": "AB13X USB Audio",
                    "capture_device": "hw:CARD=Audio,DEV=0",
                    "capture_sample_rate_hz": 48000,
                    "capture_channels": 1,
                    "capture_sample_format": "S16_LE",
                    "capture_period_frames": 480,
                },
            }
            for name, section, key in (
                ("runtime_wheel", "llm", "runtime_wheel_sha256"),
                ("native_library", "llm", "native_library_sha256"),
                ("model", "llm", "model_sha256"),
                ("tts_archive", "tts", "archive_sha256"),
                ("tts_vocoder", "tts", "vocoder_sha256"),
                ("tts_wrapper_wheel", "tts", "wrapper_wheel_sha256"),
                ("tts_core_wheel", "tts", "core_wheel_sha256"),
            ):
                path = root / name
                path.write_bytes(name.encode())
                digest = hashlib.sha256(name.encode()).hexdigest()
                profile[section][key] = digest
                artifacts[name] = {"path": str(path)}
            profile["llm"]["model_bytes"] = len(b"model")
            microphone = {
                "transport": "usb",
                "alsa_card_id": "Audio",
                "identity": "AB13X USB Audio",
                "capture_device": "hw:CARD=Audio,DEV=0",
                "sample_rate_hz": 48000,
                "channels": 1,
                "sample_format": "S16_LE",
                "period_frames": 480,
            }
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({
                "artifacts": artifacts,
                "measurement_microphone": microphone,
            }))
            observed = verify_private_receipt(receipt, profile)
            self.assertEqual(observed["measurement_microphone"], microphone)
            receipt.write_text(json.dumps({
                "artifacts": artifacts,
                "measurement_microphone": {**microphone, "sample_rate_hz": 16000},
            }))
            with self.assertRaisesRegex(TargetPreflightError, "IDENTITY_INVALID"):
                verify_private_receipt(receipt, profile)

    def test_usb_inventory_requires_card_id_and_display_identity_together(self):
        completed = type("Completed", (), {
            "returncode": 0,
            "stdout": "card 2: Audio [AB13X USB Audio], device 0: USB Audio [USB Audio]\n",
        })()
        with patch("poc_llm.m4c_ss.preflight.subprocess.run", return_value=completed):
            verify_usb_microphone_inventory("Audio", "AB13X USB Audio")
            with self.assertRaisesRegex(TargetPreflightError, "NOT_PRESENT"):
                verify_usb_microphone_inventory("Audio", "Different Device")


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
