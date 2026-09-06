"""Fail-closed storage bindings for Audio Phase 3 runners."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OBJECT_MARKER = ".audio-poc-object.json"
PRODUCT_MARKER = ".audio-poc-product.json"


@dataclass(frozen=True, slots=True)
class ProductModel:
    path: Path
    source_sha256: str
    object_id: str


def _resolved_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"{label} escapes its assigned root")
    return resolved


def _reject_symlink_components(path: Path, root: Path, label: str) -> None:
    root_lexical = Path(os.path.abspath(root))
    path_lexical = Path(os.path.abspath(path))
    if not path_lexical.is_relative_to(root_lexical):
        raise ValueError(f"{label} is outside the verified product root")
    relative = path_lexical.relative_to(root_lexical)
    current = root_lexical
    if current.is_symlink():
        raise ValueError(f"{label} contains a symlink component")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} contains a symlink component")


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_read_only_tree(path: Path, label: str) -> None:
    paths = (path, *path.rglob("*")) if path.is_dir() else (path,)
    for item in paths:
        if item.is_symlink():
            raise ValueError(f"{label} must not contain symlinks")
        if stat.S_IMODE(item.stat().st_mode) & 0o222:
            raise ValueError(f"{label} must be read-only")


def validate_storage_roots(
    *, work_dir: Path, evidence_log: Path, output: Path,
    run_root: Path, evidence_root: Path, cache_root: Path, product_root: Path,
    immutable_inputs: list[Path],
) -> dict[str, str]:
    """Bind mutable outputs to assigned roots and reject run-owned inputs."""

    supplied_roots = [run_root, evidence_root, cache_root, product_root]
    if any(root.is_symlink() for root in supplied_roots):
        raise ValueError("assigned storage roots must not be symlinks")
    roots = [
        run_root.resolve(), evidence_root.resolve(), cache_root.resolve(),
        product_root.resolve(),
    ]
    if len(set(roots)) != 4 or any(
        left.is_relative_to(right) or right.is_relative_to(left)
        for index, left in enumerate(roots)
        for right in roots[index + 1:]
    ):
        raise ValueError("run, evidence, cache, and product roots must be distinct")
    if not all(root.is_dir() for root in roots):
        raise ValueError("assigned storage root is unavailable")
    _resolved_within(work_dir, run_root, "work directory")
    _resolved_within(evidence_log, evidence_root, "evidence log")
    _resolved_within(output, evidence_root, "result output")
    if any(path.resolve().is_relative_to(run_root.resolve()) for path in immutable_inputs):
        raise ValueError("immutable input must not depend on a run directory")
    return validate_product_inputs(product_root, immutable_inputs)


def validate_product_inputs(
    product_root: Path, immutable_inputs: list[Path],
) -> dict[str, str]:
    """Require every install-time dependency to belong to one product root."""

    if product_root.is_symlink() or not product_root.resolve().is_dir():
        raise ValueError("verified product root is unavailable")
    marker_path = product_root / PRODUCT_MARKER
    if marker_path.is_symlink() or not marker_path.is_file():
        raise ValueError("verified product manifest is unavailable")
    if stat.S_IMODE(marker_path.stat().st_mode) & 0o222:
        raise ValueError("verified product identity marker must be read-only")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if (
        marker.get("schema_version") != "1.0"
        or marker.get("kind") != "audio_m4a_product"
        or marker.get("install_state") != "VERIFIED_IMMUTABLE"
        or not isinstance(marker.get("product_id"), str)
        or not SHA256_RE.fullmatch(str(marker.get("manifest_sha256", "")))
        or not isinstance(marker.get("manifest_path"), str)
    ):
        raise ValueError("verified product identity is invalid")
    _reject_symlink_components(marker_path, product_root, "product identity marker")
    manifest_path = product_root / marker["manifest_path"]
    _reject_symlink_components(manifest_path, product_root, "product manifest")
    if not manifest_path.is_file():
        raise ValueError("verified product manifest is unavailable")
    if stat.S_IMODE(manifest_path.stat().st_mode) & 0o222:
        raise ValueError("verified product manifest must be read-only")
    if _sha256_file(manifest_path) != marker["manifest_sha256"]:
        raise ValueError("verified product manifest checksum mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != "1.0"
        or manifest.get("product_id") != marker["product_id"]
        or not isinstance(manifest.get("dependencies"), list)
        or not isinstance(manifest.get("runtime_inventory"), list)
        or not manifest["runtime_inventory"]
        or not isinstance(manifest.get("native_inventory"), list)
        or not manifest["native_inventory"]
    ):
        raise ValueError("verified product manifest inventory is invalid")
    inventory: dict[Path, dict[str, object]] = {}
    for dependency in manifest["dependencies"]:
        relative = Path(str(dependency.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or relative in inventory:
            raise ValueError("verified product dependency path is invalid")
        dependency_path = product_root / relative
        _reject_symlink_components(dependency_path, product_root, "product dependency")
        if not dependency_path.is_file():
            raise ValueError("verified product dependency is unavailable")
        if stat.S_IMODE(dependency_path.stat().st_mode) & 0o222:
            raise ValueError("verified product dependency must be read-only")
        if dependency_path.stat().st_size != dependency.get("size_bytes"):
            raise ValueError("verified product dependency size mismatch")
        if _sha256_file(dependency_path) != dependency.get("sha256"):
            raise ValueError("verified product dependency checksum mismatch")
        inventory[relative] = dependency
    for key in ("runtime_inventory", "native_inventory"):
        if any(Path(str(item)) not in inventory for item in manifest[key]):
            raise ValueError(f"verified product {key} is incomplete")
    for path in immutable_inputs:
        _reject_symlink_components(path, product_root, "immutable input")
        resolved = path.resolve()
        if not resolved.is_relative_to(product_root.resolve()):
            raise ValueError("immutable input must belong to the verified product root")
        files = [resolved] if resolved.is_file() else [item for item in resolved.rglob("*") if item.is_file()]
        if not files:
            raise ValueError("immutable input has no inventoried bytes")
        for item in files:
            relative = item.relative_to(product_root.resolve())
            if relative not in inventory:
                raise ValueError("immutable input is absent from product inventory")
    _require_read_only_tree(product_root, "verified product")
    return {
        "product_id": marker["product_id"],
        "manifest_sha256": marker["manifest_sha256"],
    }


def verify_product_model(
    model_dir: Path, expected_source_sha256: str, product_root: Path, run_root: Path,
) -> ProductModel:
    """Verify one reusable, read-only model in the complete product root."""

    if not SHA256_RE.fullmatch(expected_source_sha256):
        raise ValueError("product-model source SHA-256 is invalid")
    _reject_symlink_components(model_dir, product_root, "product model")
    resolved = _resolved_within(model_dir, product_root, "product model")
    if resolved.is_relative_to(run_root.resolve()):
        raise ValueError("product model must not be stored under a run root")
    if not resolved.is_dir():
        raise ValueError("product model directory is unavailable")
    marker_path = resolved / OBJECT_MARKER
    if not marker_path.is_file():
        raise ValueError("product model identity marker is unavailable")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    expected_id = f"sha256:{expected_source_sha256}"
    if (
        marker.get("schema_version") != "1.0"
        or marker.get("kind") != "product_model"
        or marker.get("source_sha256") != expected_source_sha256
        or marker.get("object_id") != expected_id
    ):
        raise ValueError("product model identity mismatch")
    for path in (resolved, *resolved.rglob("*")):
        if path.is_symlink():
            raise ValueError("product model must not contain symlinks")
        if stat.S_IMODE(path.stat().st_mode) & 0o222:
            raise ValueError("product model must be read-only")
    return ProductModel(resolved, expected_source_sha256, expected_id)
