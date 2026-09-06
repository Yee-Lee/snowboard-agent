from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from poc_llm.harness import mva_product_layout as layout
from poc_llm.harness.mva_process import RunError


class ProductLayoutTests(unittest.TestCase):
    def test_runtime_model_path_presents_payload_without_copying_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "artifact" / "payload"
            model.parent.mkdir()
            model.write_bytes(b"model")
            run = root / "run"
            run.mkdir()

            alias = layout.runtime_model_path({"model_path": str(model)}, run)

            self.assertEqual(alias, run / "model.litertlm")
            self.assertTrue(alias.is_symlink())
            self.assertEqual(os.readlink(alias), str(model))
            self.assertEqual(alias.stat().st_ino, model.stat().st_ino)

    def test_runtime_model_path_rejects_wrong_existing_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            run.mkdir()
            (run / "model.litertlm").write_bytes(b"do-not-overwrite")
            with self.assertRaises(RunError) as raised:
                layout.runtime_model_path(
                    {"model_path": str(root / "artifact" / "payload")}, run
                )
            self.assertEqual(raised.exception.code, "IDENTITY_DRIFT")

    def fixture(self, root: Path) -> tuple[dict, dict]:
        storage = copy.deepcopy(layout.load_product_storage())
        profile_bytes = b"small selected profile fixture"
        schema_bytes = b"small selected schema fixture"
        model_bytes = b"small public model fixture"
        wheel_bytes = b"small public wheel fixture"
        manifest_bytes = b"small runtime manifest fixture"
        native_bytes = b"small native library fixture"
        storage["selected_profile"]["sha256"] = hashlib.sha256(profile_bytes).hexdigest()
        storage["selected_schema"]["sha256"] = hashlib.sha256(schema_bytes).hexdigest()
        storage["model"]["sha256"] = hashlib.sha256(model_bytes).hexdigest()
        storage["model"]["object_id"] = "sha256:" + storage["model"]["sha256"]
        storage["model"]["size_bytes"] = len(model_bytes)
        storage["runtime"]["wheel_sha256"] = hashlib.sha256(wheel_bytes).hexdigest()
        storage["runtime"]["runtime_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
        storage["runtime"]["object_id"] = (
            "sha256:" + storage["runtime"]["runtime_manifest_sha256"]
        )
        storage["runtime"]["native_library_sha256"] = hashlib.sha256(
            native_bytes
        ).hexdigest()
        dev = root / "dev"
        source = dev / "poc_llm"
        runs = dev / "runs/poc_llm"
        export = dev / "evidence-export/poc_llm"
        cache = dev / "cache/poc_llm"
        product = root / "products/m4b/8279e79"
        artifact = root / "artifacts"
        profile = product / "profiles/product-profile.json"
        schema = product / "schemas/product-profile.schema.json"
        model_sha = storage["model"]["sha256"]
        wheel_sha = storage["runtime"]["wheel_sha256"]
        model = artifact / "sha256" / model_sha[:2] / model_sha / "payload"
        wheel = artifact / "sha256" / wheel_sha[:2] / wheel_sha / "payload"
        runtime = product / "runtime"
        manifest = runtime / "runtime-manifest.json"
        native_library = (
            runtime / "lib/python3.13/site-packages/litert_lm/liblitert-lm.so"
        )
        for directory in (
            source, runs, export, cache, profile.parent, schema.parent, model.parent,
            wheel.parent, runtime, native_library.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        for path, content in (
            (profile, profile_bytes), (schema, schema_bytes), (model, model_bytes),
            (wheel, wheel_bytes), (manifest, manifest_bytes),
            (native_library, native_bytes),
        ):
            path.write_bytes(content)
        profile.chmod(0o400)
        schema.chmod(0o400)
        native_library.chmod(0o400)
        config = {
            "source_root": str(source.resolve()),
            "product_root": str(product.resolve()),
            "artifact_root": str(artifact.resolve()),
            "runs_root": str(runs.resolve()),
            "evidence_export_root": str(export.resolve()),
            "cache_root": str(cache.resolve()),
            "selected_profile_path": str(profile.resolve()),
            "selected_schema_path": str(schema.resolve()),
            "model_path": str(model.resolve()),
            "runtime_root": str(runtime.resolve()),
            "runtime_wheel": str(wheel.resolve()),
            "runtime_manifest": str(manifest.resolve()),
            "runtime_native_library": str(native_library.resolve()),
            "install_generation": 1,
            "device_abi": "test-abi-v1",
            "backend": "cpu",
            "delegate": "xnnpack",
            "cache_format_revision": storage["cache"]["format_revision"],
            "active_cache_key": "",
            "rollback_cache_keys": [],
        }
        config["active_cache_key"] = layout.cache_key(config, storage)
        return storage, config

    def test_stable_layout_and_cache_key_cover_every_required_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            storage, config = self.fixture(Path(directory))
            layout.validate_product_paths(config, storage)
            self.assertEqual(
                layout.runtime_import_root(config),
                Path(config["runtime_root"]) / "lib/python3.13/site-packages",
            )
            identity = layout.cache_identity(config, storage)
            self.assertEqual(list(identity), storage["cache"]["required_fields"])
            self.assertEqual(
                layout.cache_object_path(config),
                Path(config["cache_root"]) / "objects" / config["active_cache_key"],
            )
            for key in ("device_abi", "backend", "delegate"):
                changed = copy.deepcopy(config)
                changed[key] += "-changed"
                self.assertNotEqual(
                    layout.cache_key(changed, storage), config["active_cache_key"], key
                )
            changed_storage = copy.deepcopy(storage)
            changed_storage["cache"]["format_revision"] += "-changed"
            changed = copy.deepcopy(config)
            changed["cache_format_revision"] = changed_storage["cache"]["format_revision"]
            self.assertNotEqual(
                layout.cache_key(changed, changed_storage), config["active_cache_key"]
            )

    def test_rejects_run_local_large_inputs_scratch_and_cache_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            storage, original = self.fixture(Path(directory))
            cases = []
            changed = copy.deepcopy(original)
            changed["model_path"] = str(
                Path(original["runs_root"]) / "models" / storage["model"]["sha256"] / "model"
            )
            cases.append(changed)
            changed = copy.deepcopy(original)
            changed["model_path"] = str(
                Path(original["product_root"]) / "models" / storage["model"]["sha256"] / "model"
            )
            cases.append(changed)
            changed = copy.deepcopy(original)
            changed["source_root"] = str(Path(original["source_root"]).with_name("gate2b-scratch"))
            cases.append(changed)
            changed = copy.deepcopy(original)
            changed["active_cache_key"] = "0" * 64
            cases.append(changed)
            changed = copy.deepcopy(original)
            changed["rollback_cache_keys"] = [original["active_cache_key"]]
            cases.append(changed)
            changed = copy.deepcopy(original)
            changed["rollback_cache_keys"] = ["1" * 64, "2" * 64]
            cases.append(changed)
            for config in cases:
                with self.subTest(config=config), self.assertRaises(RunError):
                    layout.validate_product_paths(config, storage)

    def test_symlink_component_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            storage, config = self.fixture(Path(directory))
            target = Path(directory) / "real-product"
            target.mkdir()
            link = Path(directory) / "linked-product"
            link.symlink_to(target, target_is_directory=True)
            config["product_root"] = str(link.absolute())
            with self.assertRaises(RunError):
                layout.validate_product_paths(config, storage)

    def test_workspace_preflight_is_read_only_and_returns_logical_locators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "poc_llm"
            for path in (
                checkout,
                checkout.parent / "runs/poc_llm",
                checkout.parent / "evidence-export/poc_llm",
                checkout.parent / "cache/poc_llm",
            ):
                path.mkdir(parents=True, exist_ok=True)
            sha = "a" * 40

            def fake_git(command, text, timeout):
                args = command[3:]
                values = {
                    ("branch", "--show-current"): "llm\n",
                    ("rev-parse", "HEAD"): sha + "\n",
                    ("rev-parse", "refs/remotes/origin/llm"): sha + "\n",
                    ("status", "--porcelain", "--untracked-files=all"): "",
                }
                return values[tuple(args)]

            with patch.object(layout.subprocess, "check_output", side_effect=fake_git):
                result = layout.verify_workspace(checkout, sha)
            self.assertFalse(result["model_loaded"])
            self.assertFalse(result["writes_performed"])
            serialized = json.dumps(result)
            self.assertNotIn(str(checkout), serialized)
            self.assertEqual(len(result["data_roots"]), 3)

    def test_workspace_preflight_rejects_non_full_git_sha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "poc_llm"
            checkout.mkdir()
            for invalid in (
                "a" * 39,
                "a" * 41,
                "A" * 40,
                "g" * 40,
                "0" * 64,
                "refs/heads/llm",
            ):
                with self.subTest(invalid=invalid), self.assertRaises(RunError):
                    layout.verify_workspace(checkout, invalid)

    def test_native_library_digest_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            storage, config = self.fixture(Path(directory))
            native_library = Path(config["runtime_native_library"])
            native_library.chmod(0o600)
            native_library.write_bytes(b"changed native bytes")
            native_library.chmod(0o400)
            with self.assertRaises(RunError):
                layout.validate_product_paths(config, storage)

    def test_runtime_import_root_rejects_flat_or_unrelated_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            layout, "SCRATCH_PARTS", {"m4b-test-runs"}
        ):
            storage, original = self.fixture(Path(directory))
            for relative in (
                "litert_lm/liblitert-lm.so",
                "lib/python3.13/site-packages/other/liblitert-lm.so",
            ):
                changed = copy.deepcopy(original)
                changed["runtime_native_library"] = str(
                    Path(changed["runtime_root"]) / relative
                )
                with self.subTest(relative=relative), self.assertRaises(RunError):
                    layout.runtime_import_root(changed)


if __name__ == "__main__":
    unittest.main()
