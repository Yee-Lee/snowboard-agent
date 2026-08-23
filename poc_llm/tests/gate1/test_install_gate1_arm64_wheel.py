#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "poc_llm/tools/install_gate1_arm64_wheel.py"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Arm64WheelInstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="arm64-installer-", dir="/tmp")
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def run_installer(self, wheel: Path, target: Path):
        return subprocess.run(
            ["python3",str(INSTALLER),"--wheel",str(wheel),"--wheel-sha256",sha(wheel),"--target",str(target)],
            cwd=ROOT,text=True,capture_output=True,check=False,
        )
    def test_clean_authenticated_wheel_extracts(self):
        wheel = self.root / "good.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("package/__init__.py", "VALUE = 1\n")
        target = self.root / "install"
        run = self.run_installer(wheel, target)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["result"], "PASS")
        self.assertTrue((target / "package/__init__.py").is_file())
    def test_dirty_target_is_rejected_without_removal(self):
        wheel = self.root / "good.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("package/__init__.py", "")
        target = self.root / "install"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_text("owned", encoding="utf-8")
        run = self.run_installer(wheel, target)
        self.assertEqual(run.returncode, 2)
        self.assertTrue(sentinel.is_file())
    def test_traversal_member_is_rejected_and_target_absent(self):
        wheel = self.root / "bad.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("../escape", "bad")
        target = self.root / "install"
        run = self.run_installer(wheel, target)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "escape").exists())

if __name__ == "__main__":
    unittest.main()
