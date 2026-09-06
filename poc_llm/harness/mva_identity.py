"""Initial full verification, then same-install metadata checks outside READY."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import zipfile

from poc_llm.harness.pi_artifact_auth import authenticate_model, stat_identity, streaming_digest, verify_model_receipt
from poc_llm.harness.mva_surface import canonical_bytes
from poc_llm.harness.mva_process import RunError
from poc_llm.harness.mva_product_layout import (
    STORAGE_PATH as PRODUCT_STORAGE_PATH,
    cache_identity,
    cache_key,
    load_product_storage,
    runtime_import_root,
    validate_product_paths,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "poc_llm/contracts/mva/mva-profile-001.json"


def load_config(path: Path, *, checkout_root: Path | None = None) -> dict:
    config = json.loads(path.read_text())
    validate_product_paths(config, load_product_storage(), checkout_root=checkout_root)
    return config


def _runtime_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RunError("IDENTITY_DRIFT")
        if path.is_file():
            files.append(path)
    if not files:
        raise RunError("IDENTITY_DRIFT")
    return files


def prepare_receipt(config: dict) -> dict:
    profile = json.loads(PROFILE_PATH.read_text())
    storage = load_product_storage()
    validate_product_paths(config, storage)
    model = Path(config["model_path"])
    wheel = Path(config["runtime_wheel"])
    runtime = Path(config["runtime_root"])
    import_root = runtime_import_root(config)
    package_root = import_root / "litert_lm"
    runtime_manifest = Path(config["runtime_manifest"])
    native_library = Path(config["runtime_native_library"])
    if streaming_digest(runtime_manifest, timeout_s=120) != storage["runtime"]["runtime_manifest_sha256"]:
        raise RunError("IDENTITY_DRIFT")
    if streaming_digest(wheel, timeout_s=120) != profile["candidate"]["runtime_wheel_sha256"]:
        raise RunError("IDENTITY_DRIFT")
    wheel_before = stat_identity(wheel)
    if not stat.S_ISREG(wheel_before["mode"]) or wheel_before["mode"] & 0o222:
        raise RunError("IDENTITY_DRIFT")
    # Bind installed LiteRT package bytes to the selected wheel, not merely its label.
    with zipfile.ZipFile(wheel) as archive:
        expected = {name for name in archive.namelist() if name.startswith("litert_lm/") and not name.endswith("/")}
        actual = {str(path.relative_to(import_root)) for path in package_root.rglob("*") if path.is_file()}
        if not expected or expected != actual:
            raise RunError("IDENTITY_DRIFT")
        for name in expected:
            if hashlib.sha256(archive.read(name)).hexdigest() != streaming_digest(import_root / name, timeout_s=120):
                raise RunError("IDENTITY_DRIFT")
    files = {}
    for path in _runtime_files(runtime):
        before = stat_identity(path)
        if before["mode"] & 0o222 or not stat.S_ISREG(before["mode"]):
            raise RunError("IDENTITY_DRIFT")
        digest = streaming_digest(path, timeout_s=120)
        if before != stat_identity(path):
            raise RunError("IDENTITY_DRIFT")
        files[str(path.relative_to(runtime))] = {"sha256": digest, "stat": before}
    native_before = stat_identity(native_library)
    native_digest = streaming_digest(native_library, timeout_s=120)
    if (native_digest != storage["runtime"]["native_library_sha256"]
            or native_before != stat_identity(native_library)):
        raise RunError("IDENTITY_DRIFT")
    return {
        "format": "mva-install-receipt-v2", "config_sha256": hashlib.sha256(canonical_bytes(config)).hexdigest(),
        "install_generation": config["install_generation"], "runtime_files": files,
        "model": authenticate_model(model, profile["candidate"]["model_sha256"], model.stat().st_size),
        "wheel_stat": wheel_before, "wheel_sha256": profile["candidate"]["runtime_wheel_sha256"],
        "native_library": {
            "relative_path": str(native_library.relative_to(runtime)),
            "sha256": native_digest,
            "stat": native_before,
        },
        "product_storage_sha256": hashlib.sha256(PRODUCT_STORAGE_PATH.read_bytes()).hexdigest(),
        "storage_identity": {
            "selected_profile_sha256": storage["selected_profile"]["sha256"],
            "model_object_id": storage["model"]["object_id"],
            "runtime_object_id": storage["runtime"]["object_id"],
            "runtime_manifest_sha256": storage["runtime"]["runtime_manifest_sha256"],
            "cache_key": cache_key(config, storage),
            "cache_identity": cache_identity(config, storage),
        },
    }


def verify_receipt(config: dict, receipt: dict, expected_digest: str) -> None:
    if hashlib.sha256(canonical_bytes(receipt)).hexdigest() != expected_digest:
        raise RunError("IDENTITY_DRIFT")
    profile = json.loads(PROFILE_PATH.read_text())
    storage = load_product_storage()
    validate_product_paths(config, storage)
    runtime_import_root(config)
    expected_storage_identity = {
        "selected_profile_sha256": storage["selected_profile"]["sha256"],
        "model_object_id": storage["model"]["object_id"],
        "runtime_object_id": storage["runtime"]["object_id"],
        "runtime_manifest_sha256": storage["runtime"]["runtime_manifest_sha256"],
        "cache_key": cache_key(config, storage),
        "cache_identity": cache_identity(config, storage),
    }
    native_library = Path(config["runtime_native_library"])
    expected_native = {
        "relative_path": str(native_library.relative_to(Path(config["runtime_root"]))),
        "sha256": storage["runtime"]["native_library_sha256"],
        "stat": stat_identity(native_library),
    }
    if (receipt["format"] != "mva-install-receipt-v2"
            or receipt["config_sha256"] != hashlib.sha256(canonical_bytes(config)).hexdigest()
            or receipt["install_generation"] != config["install_generation"]
            or receipt["wheel_sha256"] != profile["candidate"]["runtime_wheel_sha256"]
            or receipt["wheel_stat"] != stat_identity(Path(config["runtime_wheel"]))
            or receipt["product_storage_sha256"] != hashlib.sha256(PRODUCT_STORAGE_PATH.read_bytes()).hexdigest()
            or receipt["storage_identity"] != expected_storage_identity
            or receipt["native_library"] != expected_native
            or streaming_digest(native_library, timeout_s=120)
                != storage["runtime"]["native_library_sha256"]
            or streaming_digest(Path(config["runtime_manifest"]), timeout_s=120)
                != storage["runtime"]["runtime_manifest_sha256"]):
        raise RunError("IDENTITY_DRIFT")
    verify_model_receipt(receipt["model"], Path(config["model_path"]), profile["candidate"]["model_sha256"])
    runtime = Path(config["runtime_root"])
    files = {str(path.relative_to(runtime)): stat_identity(path) for path in _runtime_files(runtime)}
    if files != {name: record["stat"] for name, record in receipt["runtime_files"].items()}:
        raise RunError("IDENTITY_DRIFT")
