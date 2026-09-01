import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from asr_r1.fixture_preflight import (
    restore_controlled_smoke_fixture,
    verify_controlled_smoke_fixture,
)


class FixturePreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary.name)
        self.repo_root = temporary_root / "repo"
        manifest_dir = self.repo_root / "asr_r1" / "manifests"
        manifest_dir.mkdir(parents=True)
        self.source_wav = temporary_root / "source.wav"
        self.external_wav = temporary_root / "controlled.wav"
        with wave.open(str(self.source_wav), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16_000)
            target.writeframes(b"\x00\x00" * 640)
        with wave.open(str(self.external_wav), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16_000)
            target.writeframes(b"\x00\x00" * 320)
        payload = self.external_wav.read_bytes()
        manifest = {
            "fixture_id": "test-smoke",
            "pcm": {
                "channels": 1,
                "sample_rate_hz": 16_000,
                "frames": 320,
                "duration_seconds": 0.02,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "source_fixture_sha256": hashlib.sha256(
                    self.source_wav.read_bytes()
                ).hexdigest(),
                "source_size_bytes": self.source_wav.stat().st_size,
                "source_frames": 640,
                "crop_start_ms": 10,
                "crop_end_ms": 30,
            },
            "speech_interval": {
                "annotation_status": "HUMAN_REVIEWED_FROZEN",
                "source_start_ms": 10,
                "source_end_ms": 30,
                "derived_start_ms": 0,
                "derived_end_ms": 20,
            },
        }
        (manifest_dir / "m1_smoke_fixture.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_exact_external_fixture_passes(self) -> None:
        identity = verify_controlled_smoke_fixture(self.repo_root, self.external_wav)
        self.assertEqual("test-smoke", identity.fixture_id)
        self.assertEqual(320, identity.frames)
        self.assertEqual(0, identity.speech_start_offset_ms)
        self.assertEqual(20, identity.speech_end_offset_ms)

    def test_unfrozen_speech_interval_fails(self) -> None:
        manifest_path = (
            self.repo_root / "asr_r1" / "manifests" / "m1_smoke_fixture.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["speech_interval"]["derived_start_ms"] = 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "speech interval mismatch"):
            verify_controlled_smoke_fixture(self.repo_root, self.external_wav)

    def test_checksum_mismatch_fails(self) -> None:
        with self.external_wav.open("ab") as target:
            target.write(b"changed")
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            verify_controlled_smoke_fixture(self.repo_root, self.external_wav)

    def test_audio_inside_repo_fails(self) -> None:
        inside = self.repo_root / "controlled.wav"
        inside.write_bytes(self.external_wav.read_bytes())
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            verify_controlled_smoke_fixture(self.repo_root, inside)

    def test_exact_source_reproduces_frozen_crop(self) -> None:
        restored = self.external_wav.with_name("restored.wav")
        identity = restore_controlled_smoke_fixture(
            self.repo_root, self.source_wav, restored
        )
        self.assertEqual(320, identity.frames)
        self.assertEqual(
            hashlib.sha256(self.external_wav.read_bytes()).hexdigest(),
            identity.sha256,
        )

    def test_restore_refuses_existing_output(self) -> None:
        with self.assertRaises(FileExistsError):
            restore_controlled_smoke_fixture(
                self.repo_root, self.source_wav, self.external_wav
            )


if __name__ == "__main__":
    unittest.main()
