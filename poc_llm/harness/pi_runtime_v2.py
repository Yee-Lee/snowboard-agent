"""Append-only Pi runtime helpers for one-pass artifact authentication."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import TextIO

from jsonschema import Draft202012Validator

from poc_llm.harness.pi_artifact_auth import streaming_digest
from poc_llm.harness.pi_runtime import PiPacketFailure, read_frame

ROOT = Path(__file__).resolve().parents[2]


def native_library_preflight_v2(path: Path, expected_sha256: str) -> dict[str, str]:
    """Authenticate the installed native library once without a whole-file allocation."""
    if not path.is_file() or streaming_digest(path) != expected_sha256:
        raise PiPacketFailure("installed native library identity mismatch")
    header = subprocess.run(
        ["readelf", "-h", str(path)], text=True, capture_output=True, check=False,
    )
    if (
        header.returncode != 0
        or "Class:" not in header.stdout
        or "ELF64" not in header.stdout
        or "Machine:" not in header.stdout
        or "AArch64" not in header.stdout
    ):
        raise PiPacketFailure("installed native library ELF identity mismatch")
    linkage = subprocess.run(
        ["ldd", str(path)], text=True, capture_output=True, check=False,
    )
    if linkage.returncode != 0 or "not found" in linkage.stdout:
        raise PiPacketFailure("installed native library linkage mismatch")
    return {
        "native_library_sha256": expected_sha256,
        "elf_machine": "AArch64",
        "linkage": "resolved",
    }


def launch_authenticated(
    *,
    config: Path,
    config_sha256: str,
    config_schema: Path,
    protocol_schema: Path,
    prompt_schema: Path,
    response_schema: Path,
    artifact_receipt: Path,
    artifact_receipt_schema: Path,
    install_root: Path,
    stderr: TextIO,
) -> subprocess.Popen[str]:
    argv = [
        "env", f"PYTHONPATH={install_root}", "python3",
        "poc_llm/harness/litert_lm_pi_child_adapter_v2.py",
        "--config", str(config), "--config-sha256", config_sha256,
        "--config-schema", str(config_schema),
        "--config-schema-sha256", streaming_digest(config_schema),
        "--protocol-schema", str(protocol_schema),
        "--protocol-schema-sha256", streaming_digest(protocol_schema),
        "--prompt-schema", str(prompt_schema),
        "--prompt-schema-sha256", streaming_digest(prompt_schema),
        "--response-schema", str(response_schema),
        "--response-schema-sha256", streaming_digest(response_schema),
        "--artifact-receipt", str(artifact_receipt),
        "--artifact-receipt-sha256", streaming_digest(artifact_receipt),
        "--artifact-receipt-schema", str(artifact_receipt_schema),
        "--artifact-receipt-schema-sha256", streaming_digest(artifact_receipt_schema),
    ]
    return subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=True,
        start_new_session=True,
        env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )


def require_ready_v2(
    process: subprocess.Popen[str],
    validator: Draft202012Validator,
    config: dict[str, object],
    config_sha256: str,
) -> None:
    if process.stdout is None:
        raise PiPacketFailure("candidate stdout unavailable")
    ready = read_frame(process.stdout, int(config["ready_timeout_ms"]) / 1000, validator)
    expected = {
        "candidate_id": config["candidate_id"],
        "pairing_revision": config["pairing_revision"],
        "platform": config["platform"],
        "runtime_sha256": config["runtime_sha256"],
        "model_sha256": config["model_sha256"],
        "config_sha256": config_sha256,
    }
    if ready.get("type") != "READY" or ready.get("identity") != expected:
        raise PiPacketFailure("READY identity mismatch")
