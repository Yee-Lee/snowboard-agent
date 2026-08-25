from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import wave


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_failure_fixture import build_sustained_probe  # noqa: E402


class M4FailureFixtureTests(unittest.TestCase):
    def test_builds_external_16khz_mono_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            with wave.open(str(source), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16_000)
                output.writeframes(b"\x00\x00" * 160)
            destination = root / "controlled" / "sustained.wav"
            build_sustained_probe(source, destination, 2)
            with wave.open(str(destination), "rb") as result:
                self.assertEqual(result.getparams()[:3], (1, 2, 16_000))
                self.assertGreaterEqual(result.getnframes(), 32_000)


if __name__ == "__main__":
    unittest.main()
