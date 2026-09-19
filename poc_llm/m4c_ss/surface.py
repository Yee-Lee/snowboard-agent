"""Explicit non-recursive execution surface for M4C-SS."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath


SURFACE_FILES = (
    "docs/milestone/m4c_streaming_speak.md",
    "docs/pm_handoff/REQUEST-LLM-POC-M4C-STREAMING-SPEAK-001.md",
    "poc_llm/contracts/m4c_ss/m4c-ss-profile-001.json",
    "poc_llm/contracts/m4c_ss/sanitized-sample-v1.schema.json",
    "poc_llm/fixtures/gate2/accepted-audio-entry-001.json",
    "poc_llm/fixtures/m4c_ss/public-catalog-001.json",
    "poc_llm/m4c_ss/__init__.py",
    "poc_llm/m4c_ss/acoustic.py",
    "poc_llm/m4c_ss/controller.py",
    "poc_llm/m4c_ss/deterministic.py",
    "poc_llm/m4c_ss/evidence.py",
    "poc_llm/m4c_ss/mapping.py",
    "poc_llm/m4c_ss/operation.py",
    "poc_llm/m4c_ss/pipeline.py",
    "poc_llm/m4c_ss/plan.py",
    "poc_llm/m4c_ss/preflight.py",
    "poc_llm/m4c_ss/s2.py",
    "poc_llm/m4c_ss/surface.py",
    "poc_llm/m4c_ss/target_backend.py",
    "poc_llm/m4c_ss/target_source.py",
    "poc_llm/tests/m4c_ss/M4C-SS-POC-PACKET-001.md",
    "poc_llm/tests/m4c_ss/__init__.py",
    "poc_llm/tests/m4c_ss/test_controller.py",
    "poc_llm/tests/m4c_ss/test_deterministic_cli.py",
    "poc_llm/tests/m4c_ss/test_evidence_contracts.py",
    "poc_llm/tests/m4c_ss/test_mapping_plan_acoustic.py",
    "poc_llm/tests/m4c_ss/test_operation.py",
    "poc_llm/tests/m4c_ss/test_pipeline_s2.py",
    "poc_llm/tests/m4c_ss/test_preflight_surface.py",
    "poc_llm/tests/m4c_ss/test_target_backend.py",
    "poc_llm/tests/m4c_ss/test_target_source.py",
    "poc_llm/tools/run_m4c_ss.py",
)


class SurfaceError(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _file(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or ".." in relative.parts or str(relative) != name:
        raise SurfaceError("INVALID_SURFACE_PATH")
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise SurfaceError("SURFACE_INPUT_INVALID")
    return path


def build_manifest(root: Path) -> dict[str, object]:
    if len(SURFACE_FILES) != len(set(SURFACE_FILES)):
        raise SurfaceError("DUPLICATE_SURFACE_INPUT")
    discovered = {
        str(path.relative_to(root))
        for pattern in ("poc_llm/m4c_ss/*.py", "poc_llm/tests/m4c_ss/*",
                        "poc_llm/contracts/m4c_ss/*", "poc_llm/fixtures/m4c_ss/*",
                        "poc_llm/tools/*m4c_ss*.py")
        for path in root.glob(pattern)
        if path.is_file() and not path.name.endswith("surface-lock-v1.json")
    }
    if not discovered.issubset(SURFACE_FILES):
        raise SurfaceError("UNINVENTORIED_M4C_SS_INPUT")
    for name in SURFACE_FILES:
        path = _file(root, name)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                candidate = module.replace(".", "/") + ".py"
                if module.startswith("poc_llm.m4c_ss") and candidate not in SURFACE_FILES:
                    raise SurfaceError("UNINVENTORIED_LOCAL_IMPORT")
    return {
        "format": "m4c-ss-source-surface-v1",
        "baseline_id": "M4C-SS-001",
        "files": {
            name: hashlib.sha256(_file(root, name).read_bytes()).hexdigest()
            for name in sorted(SURFACE_FILES)
        },
    }


def surface_digest(manifest: dict[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def verify_manifest(root: Path, manifest: dict[str, object], expected_digest: str) -> None:
    if surface_digest(manifest) != expected_digest or manifest != build_manifest(root):
        raise SurfaceError("SURFACE_IDENTITY_DRIFT")
