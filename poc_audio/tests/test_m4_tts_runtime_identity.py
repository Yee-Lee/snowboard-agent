from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4_combined_domains import _validate_tts_runtime  # noqa: E402


class M4TtsRuntimeIdentityTests(unittest.TestCase):
    def test_rejects_unpinned_sherpa_runtime(self) -> None:
        runtime = Path("/tmp/m4-runtime/bin/python")
        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "read_text", return_value="include-system-site-packages = false\n"
        ), patch("audio_poc.m4_combined_domains.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "1.12.25\n"
            with self.assertRaisesRegex(RuntimeError, "runtime identity mismatch"):
                _validate_tts_runtime(runtime)


if __name__ == "__main__":
    unittest.main()
