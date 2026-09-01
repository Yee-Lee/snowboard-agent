import os
import tempfile
import unittest
from pathlib import Path

from asr_r1.paths import resolve_repo_resource


class RepoPathTest(unittest.TestCase):
    def test_relative_resource_stays_below_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolved = resolve_repo_resource(root, "asr_r1/schemas/example.json")
            self.assertEqual(
                Path("asr_r1/schemas/example.json"), resolved.relative_to(root.resolve())
            )

    def test_parent_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_repo_resource(Path(directory), Path("..") / "outside")

    def test_absolute_resource_is_rejected(self) -> None:
        absolute = Path(os.sep) / "outside"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "must be relative"):
                resolve_repo_resource(Path(directory), absolute)


if __name__ == "__main__":
    unittest.main()
