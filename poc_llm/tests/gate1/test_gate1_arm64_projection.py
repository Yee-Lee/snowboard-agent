#!/usr/bin/env python3
"""Synthetic tests for the append-only ARM64 WIP projection."""
from __future__ import annotations
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from poc_llm.harness.gate1_arm64_projection import command_digest, projection

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "poc_llm/harness/gate1-lock-arm64-wip-v1.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

class Gate1Arm64ProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="gate1-arm64-", dir=ROOT / "poc_llm/tests/gate1")
        self.directory = Path(self.tmp.name)
        self.files: dict[str, Path] = {}
        for name in ("runtime", "deps", "adapter", "model"):
            path = self.directory / name
            path.write_text(name, encoding="utf-8")
            self.files[name] = path
        logical = {"name":"litert-lm","version":"0.16.0","source_sha256":sha(self.files["runtime"]),"license":"Apache-2.0"}
        native = {
            "runtime_artifact":{"path":str(self.files["runtime"]),"sha256":sha(self.files["runtime"])},
            "dependency_bundle":{"path":str(self.files["deps"]),"sha256":sha(self.files["deps"])},
            "adapter_binding_bundle":{"path":str(self.files["adapter"]),"sha256":sha(self.files["adapter"])},
            "deployed_model":{"path":str(self.files["model"]),"sha256":sha(self.files["model"])},
            "install_argv":["true"],
        }
        native["install_argv_sha256"] = command_digest(native["install_argv"])
        config = {
            "candidate_id":"CAND-ARM64-TEST","pairing_revision":"synthetic-arm64-v1",
            "platform":"ubuntu-aarch64","protocol_version":"snowboard.llm/1","driver":"litert_lm",
            "runtime_path":native["runtime_artifact"]["path"],"model_path":native["deployed_model"]["path"],
            "runtime_sha256":native["runtime_artifact"]["sha256"],"model_sha256":native["deployed_model"]["sha256"],
            "max_input_tokens":128,"max_output_tokens":16,"temperature":0.0,"top_p":1.0,"threads":4,
            "ready_timeout_ms":180000,"generate_timeout_ms":15000,"cancel_timeout_ms":500,
            "term_timeout_ms":2000,"kill_timeout_ms":1000,"rebuild_timeout_ms":10000,
            "runtime_download":False,"network_fallback":False,"fallback_model":None,
        }
        self.config_path = self.directory / "config.json"
        write(self.config_path, config)
        acquisition = {
            "acquisition_id":"ACQ-ARM64-TEST","candidate_id":"CAND-ARM64-TEST",
            "pairing_revision":"synthetic-arm64-v1","logical_runtime":logical,
            "platforms":{"ubuntu-aarch64":native},
        }
        self.acquisition_path = self.directory / "acquisition.json"
        write(self.acquisition_path, acquisition)
        argv = ["synthetic-arm64-runner"]
        self.manifest = {
            "candidate_id":"CAND-ARM64-TEST","pairing_revision":"synthetic-arm64-v1",
            "logical_runtime":logical,
            "model":{"name":"model","version":"0","path":str(self.files["model"]),"sha256":sha(self.files["model"])},
            "configs":{"ubuntu-aarch64":{"path":str(self.config_path),"sha256":sha(self.config_path)}},
            "quantization":"synthetic","license":"Apache-2.0","offline":True,
            "acquisition_manifest":{"path":str(self.acquisition_path),"sha256":sha(self.acquisition_path)},
            "commands":{"ubuntu-aarch64":{"argv":argv,"sha256":command_digest(argv)}},
        }
        self.manifest_path = self.directory / "candidate.json"
        write(self.manifest_path, self.manifest)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_projection_authenticates_arm64_identity(self) -> None:
        value = projection(self.manifest_path, LOCK)
        self.assertEqual(value["platform"], "ubuntu-aarch64")

    def test_x86_platform_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            projection(self.manifest_path, LOCK, "ubuntu-x86_64")

    def test_artifact_drift_is_rejected(self) -> None:
        self.files["adapter"].write_text("tampered", encoding="utf-8")
        with self.assertRaises(Exception):
            projection(self.manifest_path, LOCK)

    def test_config_projection_drift_is_rejected(self) -> None:
        value = json.loads(self.config_path.read_text(encoding="utf-8"))
        value["model_path"] = str(self.files["runtime"])
        bad_config = self.directory / "bad-config.json"
        write(bad_config, value)
        manifest = copy.deepcopy(self.manifest)
        manifest["configs"]["ubuntu-aarch64"] = {"path":str(bad_config),"sha256":sha(bad_config)}
        bad_manifest = self.directory / "bad-candidate.json"
        write(bad_manifest, manifest)
        with self.assertRaises(Exception):
            projection(bad_manifest, LOCK)

if __name__ == "__main__":
    unittest.main()
