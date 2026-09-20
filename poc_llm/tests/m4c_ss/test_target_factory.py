from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from poc_llm.m4c_ss.target_factory import (
    BINDING_FORMAT, CORE_PRODUCT_SHA, TargetBindingError, load_target_binding,
)


class TargetFactoryTests(unittest.TestCase):
    def value(self):
        return {
            "format": BINDING_FORMAT,
            "core_source_sha": CORE_PRODUCT_SHA,
            "tts_model_path": "/private/model",
            "tts_vocoder_path": "/private/vocoder.onnx",
            "tts_runtime_python": "/private/venv/bin/python",
            "audio_artifact_lock_path": "/private/audio-artifacts.json",
        }

    def write(self, root: Path, value) -> Path:
        path = root / "binding.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_loads_exact_private_binding_without_importing_core(self):
        with tempfile.TemporaryDirectory() as directory:
            binding = load_target_binding(self.write(Path(directory), self.value()))
        self.assertEqual(binding.tts_runtime_python, Path("/private/venv/bin/python"))

    def test_rejects_relative_path_and_extra_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = self.value()
            relative["tts_model_path"] = "relative/model"
            with self.assertRaisesRegex(TargetBindingError, "PATH_INVALID"):
                load_target_binding(self.write(root, relative))
            extra = self.value()
            extra["device_override"] = "unsafe"
            with self.assertRaisesRegex(TargetBindingError, "BINDING_INVALID"):
                load_target_binding(self.write(root, extra))

    def test_rejects_wrong_core_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.value()
            value["core_source_sha"] = "0" * 40
            with self.assertRaisesRegex(TargetBindingError, "IDENTITY_MISMATCH"):
                load_target_binding(self.write(Path(directory), value))


if __name__ == "__main__":
    unittest.main()
