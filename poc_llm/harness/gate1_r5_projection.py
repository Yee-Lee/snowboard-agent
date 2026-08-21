#!/usr/bin/env python3
"""R5 platform projection authentication; it never creates hardware evidence."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = ("ubuntu-x86_64", "pi-debian13-aarch64")

class IdentityError(ValueError): pass
def load(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def command_digest(argv: list[str]) -> str: return hashlib.sha256(json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
def resolve(item: dict[str, Any], label: str) -> Path:
    path = Path(item["path"])
    if not path.is_absolute(): path = ROOT / path
    path = path.resolve()
    if not path.is_file() or digest(path) != item["sha256"]: raise IdentityError(f"{label} artifact identity mismatch")
    return path
def locked(lock: dict[str, Any]) -> dict[str, Path]:
    if lock.get("packet_id") != "G1-X86-PI-COMPAT-005": raise IdentityError("R5 lock packet identity mismatch")
    return {name: resolve(item, f"locked {name}") for name, item in lock["artifacts"].items()}
def projection(manifest_path: Path, lock_path: Path, platform_id: str) -> dict[str, Any]:
    if platform_id not in PLATFORMS: raise IdentityError("runner selected an unapproved platform")
    lock = load(lock_path); paths = locked(lock)
    manifest = load(manifest_path); jsonschema.validate(manifest, load(paths["candidate_schema"]))
    configs = manifest["configs"]
    if set(configs) != set(PLATFORMS): raise IdentityError("candidate config platform set is not exact")
    if configs[PLATFORMS[0]]["sha256"] == configs[PLATFORMS[1]]["sha256"]: raise IdentityError("non-identical platform configs reuse a checksum")
    acquisition_path = resolve(manifest["acquisition_manifest"], "acquisition manifest")
    acquisition = load(acquisition_path); jsonschema.validate(acquisition, load(paths["acquisition_schema"]))
    for key in ("candidate_id", "pairing_revision", "logical_runtime"):
        if acquisition[key] != manifest[key]: raise IdentityError("candidate/acquisition manifest drift")
    item = acquisition["platforms"].get(platform_id)
    if item is None: raise IdentityError("selected acquisition platform missing")
    for key in ("runtime_artifact", "dependency_bundle", "adapter_binding_bundle", "deployed_model"):
        resolve(item[key], f"{platform_id} {key}")
    if command_digest(item["install_argv"]) != item["install_argv_sha256"]: raise IdentityError("offline install argv identity mismatch")
    command = manifest["commands"][platform_id]
    if command_digest(command["argv"]) != command["sha256"]: raise IdentityError("runtime command identity mismatch")
    config_path = resolve(configs[platform_id], f"{platform_id} strict config")
    config = load(config_path); jsonschema.validate(config, load(paths["strict_config_schema"]))
    expected = {"candidate_id":manifest["candidate_id"], "pairing_revision":manifest["pairing_revision"], "platform":platform_id, "runtime_path":item["runtime_artifact"]["path"], "model_path":item["deployed_model"]["path"], "runtime_sha256":item["runtime_artifact"]["sha256"], "model_sha256":manifest["model"]["sha256"]}
    if any(config.get(key) != value for key, value in expected.items()): raise IdentityError("strict config/acquisition projection mismatch")
    if item["deployed_model"]["sha256"] != manifest["model"]["sha256"]: raise IdentityError("platform model is not the shared logical model")
    return {"lock":lock,"manifest":manifest,"acquisition":acquisition,"config":config,"platform":platform_id,"manifest_sha256":digest(manifest_path),"acquisition_sha256":digest(acquisition_path),"config_sha256":digest(config_path)}
