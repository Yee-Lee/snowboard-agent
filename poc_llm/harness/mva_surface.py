"""Non-recursive MVA source manifest; not an execution approval or API proof.

The implementation commit belongs in the eventual execution receipt, never in
this manifest. The manifest does not hash itself or any result/receipt files.
All local imports and all MVA source/schema/test files must be inventoried.
"""

from __future__ import annotations

import hashlib
import ast
import json
from pathlib import Path, PurePosixPath


SURFACE_FILES = (
    "docs/pm_handoff/REQUEST-LLM-POC-M4B-MVA-MEASURE-001.md",
    "poc_llm/contracts/mva/machine-sample-v1.schema.json",
    "poc_llm/contracts/mva/manual-sample-v1.schema.json",
    "poc_llm/contracts/mva/mva-profile-001.json",
    "poc_llm/contracts/mva/product-storage-v1.json",
    "poc_llm/contracts/mva/semantic-output-v1.schema.json",
    "poc_llm/contracts/mva/session-facts-v1.schema.json",
    "poc_llm/contracts/mva/system-prompt-v1.txt",
    "poc_llm/contracts/mva/user-turn-template-v1.txt",
    "poc_llm/contracts/mva/wire-frame-v1.schema.json",
    "poc_llm/fixtures/mva/public-catalog-001.json",
    "poc_llm/harness/mva_contract.py",
    "poc_llm/harness/mva_controller.py",
    "poc_llm/harness/mva_evidence.py",
    "poc_llm/harness/mva_identity.py",
    "poc_llm/harness/mva_litert_backend.py",
    "poc_llm/harness/mva_process.py",
    "poc_llm/harness/mva_product_layout.py",
    "poc_llm/harness/mva_resources.py",
    "poc_llm/harness/mva_surface.py",
    "poc_llm/harness/mva_worker.py",
    "poc_llm/harness/pi_artifact_auth.py",
    "poc_llm/requirements-gate1.lock",
    "poc_llm/requirements-mva-workstation.lock",
    "poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md",
    "poc_llm/tests/mva/test_mva_contract.py",
    "poc_llm/tests/mva/test_mva_controller.py",
    "poc_llm/tests/mva/test_mva_identity.py",
    "poc_llm/tests/mva/test_mva_litert_backend.py",
    "poc_llm/tests/mva/test_mva_product_layout.py",
    "poc_llm/tests/mva/test_mva_surface.py",
    "poc_llm/tools/run_mva.py",
)


class SurfaceError(ValueError):
    """Fail closed without embedding filesystem contents or private paths."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _source_file(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or ".." in relative.parts
            or str(relative) != name or "\\" in name):
        raise SurfaceError("invalid surface path")
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise SurfaceError("surface symlinks are forbidden")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise SurfaceError("surface input missing or outside checkout")
    return path


def build_manifest(root: Path) -> dict:
    """Hash the explicit source inventory, including this builder's exact bytes."""
    if len(set(SURFACE_FILES)) != len(SURFACE_FILES):
        raise SurfaceError("duplicate surface input")
    for pattern in ("poc_llm/harness/mva_*.py", "poc_llm/tests/mva/*", "poc_llm/contracts/mva/*",
                    "poc_llm/fixtures/mva/*", "poc_llm/tools/*mva*.py"):
        if any(str(path.relative_to(root)) not in SURFACE_FILES for path in root.glob(pattern) if path.is_file()):
            raise SurfaceError("uninventoried MVA input")
    for name in SURFACE_FILES:
        path = _source_file(root, name)
        if path.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module, *(node.module + "." + alias.name for alias in node.names)]
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            for module in modules:
                relative = module.replace(".", "/") + ".py"
                if module.startswith("poc_llm.") and (root / relative).is_file() and relative not in SURFACE_FILES:
                    raise SurfaceError("uninventoried local import")
    files = {
        name: hashlib.sha256(_source_file(root, name).read_bytes()).hexdigest()
        for name in sorted(SURFACE_FILES)
    }
    return {
        "format": "m4b-mva-source-surface-v1",
        "baseline_id": "M4B-MVA-001",
        "readiness": "replacement_attempt_002_requires_exact_sha_formal_pi_proof",
        "files": files,
    }


def surface_digest(manifest: dict) -> str:
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def verify_manifest(root: Path, manifest: dict, expected_digest: str) -> None:
    """Require both trusted digest and exact inventory; no subset verification."""
    if not isinstance(manifest, dict):
        raise SurfaceError("invalid surface manifest")
    if surface_digest(manifest) != expected_digest:
        raise SurfaceError("surface digest mismatch")
    if manifest != build_manifest(root):
        raise SurfaceError("surface inventory or content mismatch")
