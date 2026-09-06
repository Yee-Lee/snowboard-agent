import json
import hashlib
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "poc_audio/src"))

from audio_poc.m4_storage import (  # noqa: E402
    OBJECT_MARKER,
    PRODUCT_MARKER,
    validate_storage_roots,
    verify_product_model,
)
from audio_poc.m4_formal import parser as formal_parser  # noqa: E402


SHA = "a" * 64


class M4StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root / "runs"
        self.evidence = self.root / "evidence"
        self.cache = self.root / "cache"
        self.product = self.root / "product"
        for path in (self.run, self.evidence, self.cache, self.product):
            path.mkdir()
        self.runtime = self.product / "runtime/python"
        self.native = self.product / "native/libtest.so"
        self.runtime.parent.mkdir()
        self.native.parent.mkdir()
        self.runtime.write_bytes(b"runtime")
        self.native.write_bytes(b"native")
        self.runtime.chmod(0o444)
        self.native.chmod(0o444)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def model(self, sha: str = SHA) -> Path:
        model = self.product / "models" / sha / "model"
        model.mkdir(parents=True)
        (model / "weights.bin").write_bytes(b"small-fixture")
        (model / OBJECT_MARKER).write_text(json.dumps({
            "schema_version": "1.0",
            "kind": "product_model",
            "source_sha256": sha,
            "object_id": f"sha256:{sha}",
        }))
        for path in model.rglob("*"):
            path.chmod(0o444)
        model.chmod(0o555)
        self.seal_product([*model.rglob("*")])
        return model

    def seal_product(self, extra: list[Path] | None = None) -> None:
        paths = [self.runtime, self.native, *(extra or [])]
        dependencies = []
        for path in paths:
            if path.is_file():
                payload = path.read_bytes()
                dependencies.append({
                    "path": str(path.relative_to(self.product)),
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                })
        manifest = {
            "schema_version": "1.0",
            "product_id": "TEST-M4A-PRODUCT",
            "dependencies": dependencies,
            "runtime_inventory": [str(self.runtime.relative_to(self.product))],
            "native_inventory": [str(self.native.relative_to(self.product))],
        }
        manifest_path = self.product / "product-manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True))
        marker = {
            "schema_version": "1.0",
            "kind": "audio_m4a_product",
            "install_state": "VERIFIED_IMMUTABLE",
            "product_id": "TEST-M4A-PRODUCT",
            "manifest_path": "product-manifest.json",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        }
        marker_path = self.product / PRODUCT_MARKER
        marker_path.write_text(json.dumps(marker))
        for path in self.product.rglob("*"):
            path.chmod(0o555 if path.is_dir() else 0o444)
        self.product.chmod(0o555)

    def test_distinct_roots_and_run_independent_inputs(self) -> None:
        model = self.model()
        validate_storage_roots(
            work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
            output=self.evidence / "result.json", run_root=self.run,
            evidence_root=self.evidence, cache_root=self.cache,
            product_root=self.product,
            immutable_inputs=[model],
        )
        first = verify_product_model(model, SHA, self.product, self.run)
        second = verify_product_model(model, SHA, self.product, self.run)
        self.assertEqual(first.object_id, second.object_id)
        self.assertFalse(any(self.run.rglob("weights.bin")))

    def test_wrong_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            verify_product_model(self.model(), "b" * 64, self.product, self.run)

    def test_mutable_input_fails_closed(self) -> None:
        model = self.model()
        (model / "weights.bin").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "read-only"):
            verify_product_model(model, SHA, self.product, self.run)

    def test_run_dependency_and_root_alias_fail_closed(self) -> None:
        self.seal_product()
        run_model = self.run / "copied-model"
        run_model.mkdir()
        with self.assertRaisesRegex(ValueError, "run directory"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product,
                immutable_inputs=[run_model],
            )
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.run / "raw.json",
                output=self.run / "result.json", run_root=self.run,
                evidence_root=self.run, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[],
            )

    def test_missing_assigned_root_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unavailable"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.root / "missing",
                product_root=self.product,
                immutable_inputs=[],
            )

    def test_nested_roots_fail_closed(self) -> None:
        nested_cache = self.run / "cache"
        nested_cache.mkdir()
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=nested_cache,
                product_root=self.product, immutable_inputs=[],
            )

    def test_assigned_root_symlink_fails_closed(self) -> None:
        product_alias = self.root / "product-alias"
        product_alias.symlink_to(self.product, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not be symlinks"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=product_alias, immutable_inputs=[],
            )

    def test_model_directory_symlink_fails_closed(self) -> None:
        model = self.model()
        self.product.chmod(0o755)
        alias = self.product / "model-alias"
        alias.symlink_to(model, target_is_directory=True)
        self.product.chmod(0o555)
        with self.assertRaisesRegex(ValueError, "symlink component"):
            verify_product_model(alias, SHA, self.product, self.run)

    def test_immutable_input_symlink_component_fails_closed(self) -> None:
        real = self.product / "real"
        real.mkdir()
        (real / "runtime").write_bytes(b"small-runtime")
        (real / "runtime").chmod(0o444)
        self.seal_product([real / "runtime"])
        self.product.chmod(0o755)
        alias = self.product / "alias"
        alias.symlink_to(real, target_is_directory=True)
        self.product.chmod(0o555)
        with self.assertRaisesRegex(ValueError, "symlink component"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[alias / "runtime"],
            )

    def test_cache_backed_immutable_input_fails_closed(self) -> None:
        self.seal_product()
        archive = self.cache / "download.tar"
        archive.write_bytes(b"reacquirable")
        with self.assertRaisesRegex(ValueError, "verified product root"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[archive],
            )

    def test_runtime_and_native_inventory_fail_closed(self) -> None:
        self.seal_product()
        self.runtime.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "read-only"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[self.runtime],
            )
        self.runtime.chmod(0o444)
        self.native.chmod(0o644)
        self.native.write_bytes(b"change")
        self.native.chmod(0o444)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[self.native],
            )

    def test_runtime_and_native_inventory_membership_mismatch_fails_closed(self) -> None:
        self.seal_product()
        for inventory_name in ("runtime_inventory", "native_inventory"):
            with self.subTest(inventory=inventory_name):
                self.product.chmod(0o755)
                manifest_path = self.product / "product-manifest.json"
                marker_path = self.product / PRODUCT_MARKER
                manifest_path.chmod(0o644)
                marker_path.chmod(0o644)
                manifest = json.loads(manifest_path.read_text())
                manifest[inventory_name] = ["missing/not-in-dependencies.bin"]
                manifest_path.write_text(json.dumps(manifest, sort_keys=True))
                marker = json.loads(marker_path.read_text())
                marker["manifest_sha256"] = hashlib.sha256(
                    manifest_path.read_bytes()
                ).hexdigest()
                marker_path.write_text(json.dumps(marker))
                manifest_path.chmod(0o444)
                marker_path.chmod(0o444)
                self.product.chmod(0o555)
                with self.assertRaisesRegex(ValueError, f"{inventory_name} is incomplete"):
                    validate_storage_roots(
                        work_dir=self.run / "run-01",
                        evidence_log=self.evidence / "raw.json",
                        output=self.evidence / "result.json",
                        run_root=self.run,
                        evidence_root=self.evidence,
                        cache_root=self.cache,
                        product_root=self.product,
                        immutable_inputs=[self.runtime, self.native],
                    )
                # Restore a sealed product before the second subtest.
                self.product.chmod(0o755)
                manifest_path.chmod(0o644)
                marker_path.chmod(0o644)
                self.seal_product()

    def test_writable_product_directory_fails_closed(self) -> None:
        self.seal_product()
        self.product.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "verified product must be read-only"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[self.runtime],
            )

    def test_product_manifest_digest_is_verified(self) -> None:
        self.seal_product()
        manifest = self.product / "product-manifest.json"
        manifest.chmod(0o644)
        manifest.write_text("{}")
        manifest.chmod(0o444)
        with self.assertRaisesRegex(ValueError, "manifest checksum mismatch"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[],
            )

    def test_concurrent_reuse_keeps_product_shared_and_read_only(self) -> None:
        model = self.model()
        with ThreadPoolExecutor(max_workers=4) as executor:
            objects = list(executor.map(
                lambda _: verify_product_model(model, SHA, self.product, self.run),
                range(8),
            ))
        self.assertEqual({item.object_id for item in objects}, {f"sha256:{SHA}"})
        self.assertFalse(any(self.run.iterdir()))

    def test_retained_evidence_cannot_be_written_under_run_root(self) -> None:
        self.seal_product()
        with self.assertRaisesRegex(ValueError, "evidence log escapes"):
            validate_storage_roots(
                work_dir=self.run / "run-01",
                evidence_log=self.run / "run-01/raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[],
            )

    def test_formal_cli_requires_all_storage_bindings(self) -> None:
        required = {action.dest for action in formal_parser()._actions if action.required}
        self.assertTrue({
            "run_root", "evidence_root", "cache_root", "product_root",
            "tts_model_dir", "tts_vocos",
        }.issubset(required))

    def test_invalid_product_identity_fails_closed(self) -> None:
        self.seal_product()
        marker = self.product / PRODUCT_MARKER
        marker.chmod(0o644)
        document = json.loads(marker.read_text())
        document["install_state"] = "DRAFT"
        marker.write_text(json.dumps(document))
        marker.chmod(0o444)
        with self.assertRaisesRegex(ValueError, "identity is invalid"):
            validate_storage_roots(
                work_dir=self.run / "run-01", evidence_log=self.evidence / "raw.json",
                output=self.evidence / "result.json", run_root=self.run,
                evidence_root=self.evidence, cache_root=self.cache,
                product_root=self.product, immutable_inputs=[],
            )


if __name__ == "__main__":
    unittest.main()
