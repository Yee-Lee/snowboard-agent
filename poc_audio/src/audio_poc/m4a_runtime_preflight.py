"""Install and import the focused Gate 1B runtime without loading a model.

This Pi-only boundary verifies the authorized inputs again, creates a fresh
virtual environment, installs only the two hashed local wheels with package
indexes disabled, and records runtime/native-library identity. It does not
extract or load a model, run inference, open an audio device, or score a
candidate.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_authorized_preflight import (
    ACK_COMMIT,
    AUTHORIZED_CANDIDATES,
    PROPOSAL_COMMIT,
    repo_root,
    verify_candidate_inputs,
)
from .validation import GIT_SHA_RE, validate_m4a_runtime_preflight


REPORT_ID = "M4A-G1B-AUTHORIZED-RUNTIME-PREFLIGHT"
RUNTIME_WHEELS = (
    "sherpa_onnx_core-1.13.5-py3-none-manylinux2014_aarch64.whl",
    "sherpa_onnx-1.13.5-cp313-cp313-manylinux2014_aarch64.whl",
)


def install_command(runtime_python: Path, wheel_paths: list[Path]) -> list[str]:
    return [
        str(runtime_python),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        *(str(path) for path in wheel_paths),
    ]


def target_platform() -> dict[str, str]:
    model_path = Path("/proc/device-tree/model")
    model = (
        model_path.read_bytes().replace(b"\x00", b"").decode("utf-8", "replace")
        if model_path.is_file()
        else "unavailable"
    )
    return {
        "machine": platform.machine(),
        "python": platform.python_version(),
        "model": model,
        "kernel": platform.release(),
    }


def assert_target(target: dict[str, str]) -> None:
    if target["machine"] != "aarch64":
        raise ValueError("runtime preflight requires aarch64")
    if sys.version_info[:2] != (3, 13):
        raise ValueError("runtime preflight requires Python 3.13")
    if not target["model"].startswith("Raspberry Pi 5"):
        raise ValueError("runtime preflight requires Raspberry Pi 5")


def offline_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_CONFIG_FILE": os.devnull,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    return environment


def import_probe(runtime_python: Path, environment: dict[str, str]) -> dict[str, Any]:
    probe = r'''
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sherpa_onnx

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

package_root = Path(sherpa_onnx.__file__).resolve().parent
native = []
for pattern in ("lib/*.so*", "../sherpa_onnx.libs/*.so*"):
    for path in sorted(package_root.glob(pattern)):
        resolved = path.resolve()
        native.append({
            "filename": resolved.name,
            "size_bytes": resolved.stat().st_size,
            "sha256": digest(resolved),
        })
result = {
    "packages": {
        "sherpa-onnx": importlib.metadata.version("sherpa-onnx"),
        "sherpa-onnx-core": importlib.metadata.version("sherpa-onnx-core"),
    },
    "module_file": sherpa_onnx.__file__,
    "api": {
        "OfflineRecognizer": hasattr(sherpa_onnx, "OfflineRecognizer"),
        "OfflineTts": hasattr(sherpa_onnx, "OfflineTts"),
    },
    "native_libraries": native,
}
print("M4A_PROBE=" + json.dumps(result, sort_keys=True))
'''
    completed = subprocess.run(
        [str(runtime_python), "-I", "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    line = next(
        (item for item in completed.stdout.splitlines() if item.startswith("M4A_PROBE=")),
        None,
    )
    if line is None:
        raise RuntimeError("runtime import probe did not return identity")
    result = json.loads(line.removeprefix("M4A_PROBE="))
    if result["packages"] != {"sherpa-onnx": "1.13.5", "sherpa-onnx-core": "1.13.5"}:
        raise RuntimeError("runtime package versions do not match authorization")
    if result["api"] != {"OfflineRecognizer": True, "OfflineTts": True}:
        raise RuntimeError("authorized ASR/TTS APIs are unavailable")
    if not result["native_libraries"]:
        raise RuntimeError("runtime native libraries are unavailable")
    return result


def audio_device_owner_count() -> int:
    devices = sorted(glob.glob("/dev/snd/*"))
    if not devices:
        return 0
    completed = subprocess.run(
        ["fuser", *devices], capture_output=True, text=True, check=False
    )
    return 1 if completed.returncode == 0 else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError("output must be a new path")
    if args.runtime_dir.exists():
        raise RuntimeError("runtime directory must be a new path")
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise RuntimeError("source SHA must be a full lowercase Git SHA")
    target = target_platform()
    assert_target(target)

    document = json.loads(
        (repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text(
            encoding="utf-8"
        )
    )
    verified_by_name = {}
    for candidate_id in sorted(AUTHORIZED_CANDIDATES):
        for artifact in verify_candidate_inputs(document, candidate_id, args.artifact_dir):
            verified_by_name[artifact.filename] = artifact.to_dict()
    wheel_paths = [args.artifact_dir / "sources" / name for name in RUNTIME_WHEELS]
    if any(path.name not in verified_by_name for path in wheel_paths):
        raise RuntimeError("authorized runtime wheel is absent from verified inputs")

    environment = offline_environment()
    args.runtime_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "venv", str(args.runtime_dir)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    runtime_python = args.runtime_dir / "bin/python"
    command = install_command(runtime_python, wheel_paths)
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    identity = import_probe(runtime_python, environment)
    owners = audio_device_owner_count()
    report = {
        "schema_version": "1.0",
        "report_id": REPORT_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "core_gate1b_ack_commit": ACK_COMMIT,
        "poc_gate1b_proposal_commit": PROPOSAL_COMMIT,
        "candidate_ids": sorted(AUTHORIZED_CANDIDATES),
        "network_policy": "offline_from_hashed_inputs",
        "platform": target,
        "verified_artifacts": [verified_by_name[name] for name in sorted(verified_by_name)],
        "install": {
            "index_disabled": True,
            "dependencies_disabled": True,
            "wheel_filenames": list(RUNTIME_WHEELS),
            "command": [
                "<runtime-python>", "-m", "pip", "install", "--no-index",
                "--no-deps", *RUNTIME_WHEELS,
            ],
        },
        "runtime_identity": identity,
        "execution_status": "RUNTIME_IMPORT_PASS_NOT_INFERRED",
        "cleanup": {
            "child_processes": 0,
            "threads": 0,
            "iterators": 0,
            "streams": 0,
            "device_owners": owners,
            "clean": owners == 0,
        },
    }
    validate_m4a_runtime_preflight(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if owners:
        raise RuntimeError("audio device owner appeared during runtime preflight")
    print(f"authorized runtime preflight passed: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
