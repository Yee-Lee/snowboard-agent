import tempfile
import unittest
from pathlib import Path

from asr_r1.data_safety import scan_repository


class DataSafetyTest(unittest.TestCase):
    def test_clean_text_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("sanitized evidence index", encoding="utf-8")
            self.assertEqual([], scan_repository(root))

    def test_model_audio_secret_and_raw_paths_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.onnx").write_bytes(b"fake")
            (root / "key.txt").write_text(
                "-----BEGIN " + "PRIVATE KEY-----\nnot-a-real-key", encoding="utf-8"
            )
            raw = root / "asr_r1" / "evidence" / "raw"
            raw.mkdir(parents=True)
            (raw / "result.json").write_text("{}", encoding="utf-8")

            reasons = {(item.path, item.reason) for item in scan_repository(root)}
            self.assertIn(("model.onnx", "prohibited model, binary, or audio suffix"), reasons)
            self.assertIn(("key.txt", "possible private key"), reasons)
            self.assertIn(
                ("asr_r1/evidence/raw/result.json", "controlled or raw-data path"), reasons
            )

    def test_git_directory_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git = root / ".git"
            git.mkdir()
            (git / "object.onnx").write_bytes(b"ignored")
            self.assertEqual([], scan_repository(root))


if __name__ == "__main__":
    unittest.main()
