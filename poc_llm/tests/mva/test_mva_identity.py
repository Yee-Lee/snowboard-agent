from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness.mva_identity import load_config, verify_receipt
from poc_llm.harness.mva_process import RunError
from poc_llm.harness.mva_surface import canonical_bytes
from poc_llm.harness.pi_artifact_auth import authenticate_model, stat_identity


class IdentityTests(unittest.TestCase):
    def test_same_install_check_uses_metadata_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            model = root / "model"
            model.write_bytes(b"public fake model")
            model.chmod(0o400)
            wheel = root / "wheel"
            wheel.write_bytes(b"public fake wheel")
            runtime = root / "runtime"
            runtime.mkdir()
            source = runtime / "runtime.py"
            source.write_bytes(b"public fake runtime")
            source.chmod(0o400)
            config = {"model_path": str(model), "runtime_root": str(runtime), "runtime_wheel": str(wheel), "install_generation": 1}
            model_sha = hashlib.sha256(model.read_bytes()).hexdigest()
            wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
            receipt = {"format": "mva-install-receipt-v1", "config_sha256": hashlib.sha256(canonical_bytes(config)).hexdigest(),
                "install_generation": 1, "model": authenticate_model(model, model_sha, model.stat().st_size),
                "runtime_files": {"runtime.py": {"stat": stat_identity(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}},
                "wheel_stat": stat_identity(wheel), "wheel_sha256": wheel_sha}
            digest = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
            profile = root / "profile.json"
            profile.write_text(json.dumps({"candidate": {"model_sha256": model_sha, "runtime_wheel_sha256": wheel_sha}}))
            with patch("poc_llm.harness.mva_identity.PROFILE_PATH", profile), patch(
                "poc_llm.harness.pi_artifact_auth.streaming_digest", side_effect=AssertionError("no rehash allowed")):
                verify_receipt(config, receipt, digest)
                source.chmod(0o600)
                source.write_bytes(b"changed")
                with self.assertRaises(RunError):
                    verify_receipt(config, receipt, digest)

    def test_config_rejects_relative_paths_extra_keys_and_bool_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            original = {"model_path": "/model", "runtime_root": "/runtime", "runtime_wheel": "/wheel", "install_generation": 1}
            for changed in ({"model_path": "relative"}, {"extra": "private"}, {"install_generation": True}):
                path.write_text(json.dumps(dict(original, **changed)))
                with self.assertRaises(RunError):
                    load_config(path)


if __name__ == "__main__":
    unittest.main()
