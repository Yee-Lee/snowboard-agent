import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from asr_r1.fixture_preflight import verify_controlled_smoke_fixture


class FixturePreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary.name)
        self.repo_root = temporary_root / "repo"
        manifest_dir = self.repo_root / "asr_r1" / "manifests"
        manifest_dir.mkdir(parents=True)
        self.external_wav = temporary_root / "controlled.wav"
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


if __name__ == "__main__":
    unittest.main()
