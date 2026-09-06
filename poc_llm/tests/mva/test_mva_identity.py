from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness import mva_product_layout as layout
from poc_llm.harness.mva_identity import load_config, verify_receipt
from poc_llm.harness.mva_process import RunError
from poc_llm.harness.mva_surface import canonical_bytes
from poc_llm.harness.pi_artifact_auth import authenticate_model, stat_identity


class IdentityTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, dict, Path, Path, Path, Path, Path]:
        dev = root / "dev"
        source_root = dev / "poc_llm"
        runs_root = dev / "runs/poc_llm"
        evidence_root = dev / "evidence-export/poc_llm"
        cache_root = dev / "cache/poc_llm"
        product_root = root / "products/m4b/8279e79"
        artifact_root = root / "artifacts"
        profile_bytes = b"public selected profile"
        schema_bytes = b"public selected schema"
        model_bytes = b"public fake model"
        wheel_bytes = b"public fake wheel"
        manifest_bytes = b"public runtime manifest"
        native_bytes = b"public native library"
        model_sha = hashlib.sha256(model_bytes).hexdigest()
        wheel_sha = hashlib.sha256(wheel_bytes).hexdigest()
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        storage = {
            "selected_profile": {"sha256": hashlib.sha256(profile_bytes).hexdigest()},
            "selected_schema": {"sha256": hashlib.sha256(schema_bytes).hexdigest()},
            "model": {"object_id": "sha256:" + model_sha, "sha256": model_sha,
                      "size_bytes": len(model_bytes)},
            "runtime": {
                "object_id": "sha256:" + manifest_sha,
                "runtime_manifest_sha256": manifest_sha,
                "wheel_sha256": wheel_sha,
                "native_library_sha256": hashlib.sha256(native_bytes).hexdigest(),
                "api_revision": "test-api",
                "source_revision": "3" * 40,
            },
            "cache": {"format_revision": "test-cache-v1"},
        }
        storage["product"] = {"id": "8279e79"}
        selected_profile = product_root / "profiles/product-profile.json"
        selected_schema = product_root / "schemas/product-profile.schema.json"
        model = artifact_root / "sha256" / model_sha[:2] / model_sha / "payload"
        wheel = artifact_root / "sha256" / wheel_sha[:2] / wheel_sha / "payload"
        runtime = product_root / "runtime"
        runtime_manifest = runtime / "runtime-manifest.json"
        runtime_source = runtime / "runtime.py"
        native_library = runtime / "lib" / "libLiteRtLm.so"
        for target in (
            source_root, runs_root, evidence_root, cache_root, selected_profile.parent,
            selected_schema.parent, model.parent, wheel.parent, runtime,
            native_library.parent,
        ):
            target.mkdir(parents=True, exist_ok=True)
        selected_profile.write_bytes(profile_bytes)
        selected_schema.write_bytes(schema_bytes)
        model.write_bytes(model_bytes)
        wheel.write_bytes(wheel_bytes)
        runtime_manifest.write_bytes(manifest_bytes)
        runtime_source.write_bytes(b"public fake runtime")
        native_library.write_bytes(native_bytes)
        for target in (
            selected_profile, selected_schema, model, wheel, runtime_manifest, runtime_source,
            native_library,
        ):
            target.chmod(0o400)
        config = {
            "source_root": str(source_root.resolve()),
            "product_root": str(product_root.resolve()),
            "artifact_root": str(artifact_root.resolve()),
            "runs_root": str(runs_root.resolve()),
            "evidence_export_root": str(evidence_root.resolve()),
            "cache_root": str(cache_root.resolve()),
            "selected_profile_path": str(selected_profile.resolve()),
            "selected_schema_path": str(selected_schema.resolve()),
            "model_path": str(model.resolve()),
            "runtime_root": str(runtime.resolve()),
            "runtime_wheel": str(wheel.resolve()),
            "runtime_manifest": str(runtime_manifest.resolve()),
            "runtime_native_library": str(native_library.resolve()),
            "install_generation": 1,
            "device_abi": "test-abi",
            "backend": "cpu",
            "delegate": "xnnpack",
            "cache_format_revision": "test-cache-v1",
            "active_cache_key": "",
            "rollback_cache_keys": [],
        }
        config["active_cache_key"] = layout.cache_key(config, storage)
        return storage, config, model, wheel, runtime_manifest, runtime_source, native_library

    def test_same_install_check_uses_metadata_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            root = Path(directory).resolve()
            (storage, config, model, wheel, runtime_manifest, runtime_source,
             native_library) = self.fixture(root)
            product_storage = root / "product-storage.json"
            product_storage.write_text("public product storage")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"candidate": {
                "model_sha256": storage["model"]["sha256"],
                "runtime_wheel_sha256": storage["runtime"]["wheel_sha256"],
            }}))
            runtime_files = {}
            for source in (runtime_manifest, runtime_source, native_library):
                runtime_files[str(source.relative_to(Path(config["runtime_root"])))] = {
                    "stat": stat_identity(source),
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }
            storage_identity = {
                "selected_profile_sha256": storage["selected_profile"]["sha256"],
                "model_object_id": storage["model"]["object_id"],
                "runtime_object_id": storage["runtime"]["object_id"],
                "runtime_manifest_sha256": storage["runtime"]["runtime_manifest_sha256"],
                "cache_key": layout.cache_key(config, storage),
                "cache_identity": layout.cache_identity(config, storage),
            }
            receipt = {
                "format": "mva-install-receipt-v2",
                "config_sha256": hashlib.sha256(canonical_bytes(config)).hexdigest(),
                "install_generation": 1,
                "model": authenticate_model(
                    model, storage["model"]["sha256"], model.stat().st_size
                ),
                "runtime_files": runtime_files,
                "wheel_stat": stat_identity(wheel),
                "wheel_sha256": storage["runtime"]["wheel_sha256"],
                "native_library": {
                    "relative_path": str(native_library.relative_to(Path(config["runtime_root"]))),
                    "sha256": storage["runtime"]["native_library_sha256"],
                    "stat": stat_identity(native_library),
                },
                "product_storage_sha256": hashlib.sha256(
                    product_storage.read_bytes()
                ).hexdigest(),
                "storage_identity": storage_identity,
            }
            digest = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
            with (
                patch("poc_llm.harness.mva_identity.PROFILE_PATH", profile),
                patch("poc_llm.harness.mva_identity.PRODUCT_STORAGE_PATH", product_storage),
                patch("poc_llm.harness.mva_identity.load_product_storage", return_value=storage),
            ):
                verify_receipt(config, receipt, digest)
                runtime_source.chmod(0o600)
                runtime_source.write_bytes(b"changed")
                with self.assertRaises(RunError):
                    verify_receipt(config, receipt, digest)

    def test_config_rejects_relative_paths_extra_keys_bool_generation_and_bad_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            root = Path(directory).resolve()
            storage, original, *_ = self.fixture(root)
            path = root / "config.json"
            with patch(
                "poc_llm.harness.mva_identity.load_product_storage", return_value=storage
            ):
                path.write_text(json.dumps(original))
                self.assertEqual(load_config(path), original)
                for changed in (
                    {"model_path": "relative"},
                    {"extra": "private"},
                    {"install_generation": True},
                    {"active_cache_key": "0" * 64},
                ):
                    value = copy.deepcopy(original)
                    value.update(changed)
                    path.write_text(json.dumps(value))
                    with self.subTest(changed=changed), self.assertRaises(RunError):
                        load_config(path)


if __name__ == "__main__":
    unittest.main()
