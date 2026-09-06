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

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "poc_llm/contracts/mva/mva-profile-001.json"


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if set(config) != {"model_path", "runtime_root", "runtime_wheel", "install_generation"}:
        raise RunError("IDENTITY_DRIFT")
    if not isinstance(config["install_generation"], int) or isinstance(config["install_generation"], bool) or config["install_generation"] < 1:
        raise RunError("IDENTITY_DRIFT")
    for key in ("model_path", "runtime_root", "runtime_wheel"):
        value = Path(config[key])
        if not value.is_absolute() or value.resolve() != value:
            raise RunError("IDENTITY_DRIFT")
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
    model = Path(config["model_path"])
    wheel = Path(config["runtime_wheel"])
    runtime = Path(config["runtime_root"])
    if streaming_digest(wheel, timeout_s=120) != profile["candidate"]["runtime_wheel_sha256"]:
        raise RunError("IDENTITY_DRIFT")
    # Bind installed LiteRT package bytes to the selected wheel, not merely its label.
    with zipfile.ZipFile(wheel) as archive:
        expected = {name for name in archive.namelist() if name.startswith("litert_lm/") and not name.endswith("/")}
        actual = {str(path.relative_to(runtime)) for path in (runtime / "litert_lm").rglob("*") if path.is_file()}
        if not expected or expected != actual:
            raise RunError("IDENTITY_DRIFT")
        for name in expected:
            if hashlib.sha256(archive.read(name)).hexdigest() != streaming_digest(runtime / name, timeout_s=120):
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
    return {
        "format": "mva-install-receipt-v1", "config_sha256": hashlib.sha256(canonical_bytes(config)).hexdigest(),
        "install_generation": config["install_generation"], "runtime_files": files,
        "model": authenticate_model(model, profile["candidate"]["model_sha256"], model.stat().st_size),
        "wheel_stat": stat_identity(wheel), "wheel_sha256": profile["candidate"]["runtime_wheel_sha256"],
    }


def verify_receipt(config: dict, receipt: dict, expected_digest: str) -> None:
    if hashlib.sha256(canonical_bytes(receipt)).hexdigest() != expected_digest:
        raise RunError("IDENTITY_DRIFT")
    profile = json.loads(PROFILE_PATH.read_text())
    if (receipt["format"] != "mva-install-receipt-v1"
            or receipt["config_sha256"] != hashlib.sha256(canonical_bytes(config)).hexdigest()
            or receipt["install_generation"] != config["install_generation"]
            or receipt["wheel_sha256"] != profile["candidate"]["runtime_wheel_sha256"]
            or receipt["wheel_stat"] != stat_identity(Path(config["runtime_wheel"]))):
        raise RunError("IDENTITY_DRIFT")
    verify_model_receipt(receipt["model"], Path(config["model_path"]), profile["candidate"]["model_sha256"])
    runtime = Path(config["runtime_root"])
    files = {str(path.relative_to(runtime)): stat_identity(path) for path in _runtime_files(runtime)}
    if files != {name: record["stat"] for name, record in receipt["runtime_files"].items()}:
        raise RunError("IDENTITY_DRIFT")
