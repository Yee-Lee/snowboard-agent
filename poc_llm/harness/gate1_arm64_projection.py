#!/usr/bin/env python3
"""ARM64 WIP projection authentication; it never creates candidate evidence."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
PACKET_ID = "G1-ARM64-PRESCREEN-WIP-001"
PLATFORM = "ubuntu-aarch64"

class IdentityError(ValueError):
    pass

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command_digest(argv: list[str]) -> str:
    value = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()

def resolve(item: dict[str, Any], label: str) -> Path:
    path = Path(item["path"])
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.is_file() or digest(path) != item["sha256"]:
        raise IdentityError(f"{label} artifact identity mismatch")
    return path

def locked(lock: dict[str, Any]) -> dict[str, Path]:
    if lock.get("packet_id") != PACKET_ID:
        raise IdentityError("ARM64 lock packet identity mismatch")
    return {name: resolve(item, f"locked {name}") for name, item in lock["artifacts"].items()}

def projection(manifest_path: Path, lock_path: Path, platform_id: str = PLATFORM) -> dict[str, Any]:
    if platform_id != PLATFORM:
        raise IdentityError("runner selected an unapproved ARM64 platform")
    paths = locked(load(lock_path))
    manifest = load(manifest_path)
    jsonschema.validate(manifest, load(paths["candidate_schema"]))
    acquisition_path = resolve(manifest["acquisition_manifest"], "acquisition manifest")
    acquisition = load(acquisition_path)
    jsonschema.validate(acquisition, load(paths["acquisition_schema"]))
    for key in ("candidate_id", "pairing_revision", "logical_runtime"):
        if acquisition[key] != manifest[key]:
            raise IdentityError("candidate/acquisition manifest drift")
    native = acquisition["platforms"][PLATFORM]
    for key in ("runtime_artifact", "dependency_bundle", "adapter_binding_bundle", "deployed_model"):
        resolve(native[key], f"{PLATFORM} {key}")
    if command_digest(native["install_argv"]) != native["install_argv_sha256"]:
        raise IdentityError("offline install argv identity mismatch")
    command = manifest["commands"][PLATFORM]
    if command_digest(command["argv"]) != command["sha256"]:
        raise IdentityError("runtime command identity mismatch")
    config_path = resolve(manifest["configs"][PLATFORM], f"{PLATFORM} strict config")
    config = load(config_path)
    jsonschema.validate(config, load(paths["strict_config_schema"]))
    expected = {
        "candidate_id": manifest["candidate_id"],
        "pairing_revision": manifest["pairing_revision"],
        "platform": PLATFORM,
        "runtime_path": native["runtime_artifact"]["path"],
        "model_path": native["deployed_model"]["path"],
        "runtime_sha256": native["runtime_artifact"]["sha256"],
        "model_sha256": manifest["model"]["sha256"],
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise IdentityError("strict config/acquisition projection mismatch")
    if native["deployed_model"]["sha256"] != manifest["model"]["sha256"]:
        raise IdentityError("platform model is not the shared logical model")
    return {
        "lock": load(lock_path), "manifest": manifest, "acquisition": acquisition,
        "config": config, "platform": PLATFORM, "manifest_sha256": digest(manifest_path),
        "acquisition_sha256": digest(acquisition_path), "config_sha256": digest(config_path),
    }
