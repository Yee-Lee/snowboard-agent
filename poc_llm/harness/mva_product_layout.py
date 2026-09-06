"""Fail-closed MVA product, workspace and generated-cache path identity."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from poc_llm.harness.mva_process import RunError
from poc_llm.harness.mva_surface import canonical_bytes


ROOT = Path(__file__).resolve().parents[2]
STORAGE_PATH = ROOT / "poc_llm/contracts/mva/product-storage-v1.json"

CONFIG_KEYS = {
    "source_root", "product_root", "artifact_root", "runs_root", "evidence_export_root",
    "cache_root", "selected_profile_path", "selected_schema_path", "model_path",
    "runtime_root", "runtime_wheel", "runtime_manifest", "runtime_native_library",
    "install_generation", "device_abi", "backend", "delegate",
    "cache_format_revision", "active_cache_key", "rollback_cache_keys",
}
PATH_KEYS = {
    "source_root", "product_root", "artifact_root", "runs_root", "evidence_export_root",
    "cache_root", "selected_profile_path", "selected_schema_path", "model_path",
    "runtime_root", "runtime_wheel", "runtime_manifest", "runtime_native_library",
}
HEX64 = re.compile(r"[0-9a-f]{64}")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
SCRATCH_PARTS = {"tmp", "m4b-test-runs"}


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _is_relative(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RunError("IDENTITY_DRIFT")


def load_product_storage(path: Path = STORAGE_PATH) -> dict:
    storage = json.loads(path.read_text(encoding="utf-8"))
    if set(storage) != {
        "format", "product", "selected_profile", "selected_schema", "model", "runtime", "cache",
        "logical_layout",
    } or storage["format"] != "m4b-product-storage-v1":
        raise RunError("IDENTITY_DRIFT")
    if storage["product"] != {"id": "8279e79"}:
        raise RunError("IDENTITY_DRIFT")
    for key in ("selected_profile", "selected_schema"):
        record = storage[key]
        if set(record) != {"path", "sha256"} or not HEX64.fullmatch(record["sha256"]):
            raise RunError("IDENTITY_DRIFT")
        source = ROOT / record["path"]
        if not source.is_file() or source.is_symlink() or _digest(source) != record["sha256"]:
            raise RunError("IDENTITY_DRIFT")
    model = storage["model"]
    if (set(model) != {"object_id", "sha256", "size_bytes"}
            or model["object_id"] != "sha256:" + model["sha256"]
            or not HEX64.fullmatch(model["sha256"])
            or not isinstance(model["size_bytes"], int) or isinstance(model["size_bytes"], bool)
            or model["size_bytes"] < 1):
        raise RunError("IDENTITY_DRIFT")
    runtime = storage["runtime"]
    if set(runtime) != {
        "object_id", "artifact_manifest_sha256", "runtime_manifest_sha256",
        "wheel_sha256", "native_library_sha256", "api_revision", "source_revision",
    } or runtime["object_id"] != "sha256:" + runtime["runtime_manifest_sha256"]:
        raise RunError("IDENTITY_DRIFT")
    for key in ("artifact_manifest_sha256", "runtime_manifest_sha256", "wheel_sha256",
                "native_library_sha256"):
        if not HEX64.fullmatch(runtime[key]):
            raise RunError("IDENTITY_DRIFT")
    cache = storage["cache"]
    expected_cache_fields = [
        "model_sha256", "model_size_bytes", "runtime_manifest_sha256",
        "runtime_wheel_sha256", "runtime_native_library_sha256",
        "runtime_api_revision", "runtime_source_revision", "device_abi", "backend",
        "delegate", "cache_format_revision",
    ]
    if (set(cache) != {"format_revision", "key_algorithm", "required_fields"}
            or cache["key_algorithm"] != "sha256-canonical-json-v1"
            or cache["required_fields"] != expected_cache_fields):
        raise RunError("IDENTITY_DRIFT")
    if storage["logical_layout"] != {
        "source": "PI_DEV_ROOT/poc_llm",
        "runs": "PI_DEV_ROOT/runs/poc_llm",
        "evidence_export": "PI_DEV_ROOT/evidence-export/poc_llm",
        "cache": "PI_DEV_ROOT/cache/poc_llm/objects/{cache_key}",
        "selected_profile": "PI_PROD_PRODUCTS/m4b/{product_id}/profiles/product-profile.json",
        "selected_schema": "PI_PROD_PRODUCTS/m4b/{product_id}/schemas/product-profile.schema.json",
        "model": "PI_ARTIFACT_STORE/sha256/{model_sha256_prefix2}/{model_sha256}/payload",
        "runtime_wheel": "PI_ARTIFACT_STORE/sha256/{wheel_sha256_prefix2}/{wheel_sha256}/payload",
        "runtime": "PI_PROD_PRODUCTS/m4b/{product_id}/runtime",
        "runtime_native_library": (
            "PI_PROD_PRODUCTS/m4b/{product_id}/runtime/{relative_library_path}"
        ),
    }:
        raise RunError("IDENTITY_DRIFT")
    return storage


def cache_identity(config: dict, storage: dict) -> dict:
    return {
        "model_sha256": storage["model"]["sha256"],
        "model_size_bytes": storage["model"]["size_bytes"],
        "runtime_manifest_sha256": storage["runtime"]["runtime_manifest_sha256"],
        "runtime_wheel_sha256": storage["runtime"]["wheel_sha256"],
        "runtime_native_library_sha256": storage["runtime"]["native_library_sha256"],
        "runtime_api_revision": storage["runtime"]["api_revision"],
        "runtime_source_revision": storage["runtime"]["source_revision"],
        "device_abi": config["device_abi"],
        "backend": config["backend"],
        "delegate": config["delegate"],
        "cache_format_revision": config["cache_format_revision"],
    }


def cache_key(config: dict, storage: dict) -> str:
    return hashlib.sha256(canonical_bytes(cache_identity(config, storage))).hexdigest()


def cache_object_path(config: dict) -> Path:
    return Path(config["cache_root"]) / "objects" / config["active_cache_key"]


def validate_product_paths(
    config: dict, storage: dict, *, checkout_root: Path | None = None,
) -> None:
    if set(config) != CONFIG_KEYS:
        raise RunError("IDENTITY_DRIFT")
    if (not isinstance(config["install_generation"], int)
            or isinstance(config["install_generation"], bool)
            or config["install_generation"] < 1):
        raise RunError("IDENTITY_DRIFT")
    for key in ("device_abi", "backend", "delegate", "cache_format_revision"):
        if not isinstance(config[key], str) or not config[key] or len(config[key]) > 128:
            raise RunError("IDENTITY_DRIFT")
    if config["cache_format_revision"] != storage["cache"]["format_revision"]:
        raise RunError("IDENTITY_DRIFT")
    if (not isinstance(config["rollback_cache_keys"], list)
            or any(not isinstance(item, str) or not HEX64.fullmatch(item)
                   for item in config["rollback_cache_keys"])
            or len(config["rollback_cache_keys"]) > 1
            or len(set(config["rollback_cache_keys"])) != len(config["rollback_cache_keys"])):
        raise RunError("IDENTITY_DRIFT")

    paths = {}
    for key in PATH_KEYS:
        value = Path(config[key])
        if not value.is_absolute() or value.resolve(strict=False) != value:
            raise RunError("IDENTITY_DRIFT")
        _reject_symlink_components(value)
        if any(part in SCRATCH_PARTS or part.startswith("gate2b-") for part in value.parts):
            raise RunError("IDENTITY_DRIFT")
        paths[key] = value

    source = paths["source_root"]
    dev_root = source.parent
    if (source.name != "poc_llm"
            or paths["runs_root"] != dev_root / "runs/poc_llm"
            or paths["evidence_export_root"] != dev_root / "evidence-export/poc_llm"
            or paths["cache_root"] != dev_root / "cache/poc_llm"):
        raise RunError("IDENTITY_DRIFT")
    if checkout_root is not None and source != checkout_root.resolve():
        raise RunError("IDENTITY_DRIFT")

    product = paths["product_root"]
    artifact = paths["artifact_root"]
    runtime = paths["runtime_root"]
    selected_profile = paths["selected_profile_path"]
    selected_schema = paths["selected_schema_path"]
    model = paths["model_path"]
    wheel = paths["runtime_wheel"]
    manifest = paths["runtime_manifest"]
    native_library = paths["runtime_native_library"]
    if (_is_relative(product, dev_root) or _is_relative(dev_root, product)
            or _is_relative(artifact, dev_root) or _is_relative(dev_root, artifact)
            or _is_relative(product, artifact) or _is_relative(artifact, product)
            or not _is_relative(runtime, product)
            or not _is_relative(selected_profile, product)
            or not _is_relative(selected_schema, product)
            or not _is_relative(model, artifact) or not _is_relative(wheel, artifact)
            or not _is_relative(manifest, runtime)
            or not _is_relative(native_library, runtime)):
        raise RunError("IDENTITY_DRIFT")
    forbidden_large_roots = (source, paths["runs_root"], paths["evidence_export_root"],
                             paths["cache_root"], runtime)
    if any(_is_relative(model, root) or _is_relative(wheel, root)
           for root in forbidden_large_roots):
        raise RunError("IDENTITY_DRIFT")

    profile_sha = storage["selected_profile"]["sha256"]
    schema_sha = storage["selected_schema"]["sha256"]
    model_sha = storage["model"]["sha256"]
    wheel_sha = storage["runtime"]["wheel_sha256"]
    runtime_sha = storage["runtime"]["runtime_manifest_sha256"]
    if (product.name != storage["product"]["id"]
            or selected_profile != product / "profiles/product-profile.json"
            or selected_schema != product / "schemas/product-profile.schema.json"
            or model != artifact / "sha256" / model_sha[:2] / model_sha / "payload"
            or wheel != artifact / "sha256" / wheel_sha[:2] / wheel_sha / "payload"
            or runtime != product / "runtime"):
        raise RunError("IDENTITY_DRIFT")
    if (not selected_profile.is_file() or selected_profile.is_symlink()
            or _digest(selected_profile) != profile_sha
            or selected_profile.stat().st_mode & 0o222
            or not selected_schema.is_file() or selected_schema.is_symlink()
            or _digest(selected_schema) != schema_sha
            or selected_schema.stat().st_mode & 0o222
            or not model.is_file() or model.is_symlink()
            or model.stat().st_size != storage["model"]["size_bytes"]):
        raise RunError("IDENTITY_DRIFT")

    if (not native_library.is_file() or native_library.is_symlink()
            or native_library.stat().st_mode & 0o222
            or _digest(native_library) != storage["runtime"]["native_library_sha256"]):
        raise RunError("IDENTITY_DRIFT")

    expected_key = cache_key(config, storage)
    if (config["active_cache_key"] != expected_key
            or expected_key in config["rollback_cache_keys"]):
        raise RunError("IDENTITY_DRIFT")
    cache_path = cache_object_path(config)
    if any(_is_relative(cache_path, root) for root in (paths["runs_root"], runtime, model.parent)):
        raise RunError("IDENTITY_DRIFT")


def verify_workspace(checkout_root: Path, expected_sha: str) -> dict:
    """Read-only verification of the Phase 2 source and assigned data roots."""
    if not GIT_SHA_RE.fullmatch(expected_sha):
        raise RunError("PREFLIGHT_BLOCKED")
    checkout = checkout_root.resolve()
    if checkout.name != "poc_llm" or checkout.is_symlink():
        raise RunError("PREFLIGHT_BLOCKED")

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(checkout), *args], text=True, timeout=10,
        ).strip()

    if (git("branch", "--show-current") != "llm"
            or git("rev-parse", "HEAD") != expected_sha
            or git("rev-parse", "refs/remotes/origin/llm") != expected_sha
            or git("status", "--porcelain", "--untracked-files=all")):
        raise RunError("PREFLIGHT_BLOCKED")
    roots = {
        "runs": checkout.parent / "runs/poc_llm",
        "evidence_export": checkout.parent / "evidence-export/poc_llm",
        "cache": checkout.parent / "cache/poc_llm",
    }
    if any(not path.is_dir() or path.is_symlink() or not os.access(path, os.W_OK)
           for path in roots.values()):
        raise RunError("PREFLIGHT_BLOCKED")
    return {
        "format": "mva-workspace-preflight-v1",
        "source": {"locator": "PI_DEV_ROOT/poc_llm", "branch": "llm", "sha": expected_sha,
                   "tracked_clean": True, "untracked_count": 0},
        "data_roots": [
            {"locator": "PI_DEV_ROOT/runs/poc_llm", "writable_access": True},
            {"locator": "PI_DEV_ROOT/evidence-export/poc_llm", "writable_access": True},
            {"locator": "PI_DEV_ROOT/cache/poc_llm", "writable_access": True},
        ],
        "model_loaded": False,
        "writes_performed": False,
    }
