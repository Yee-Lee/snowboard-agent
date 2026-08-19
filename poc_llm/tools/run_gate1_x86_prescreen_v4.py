#!/usr/bin/env python3
"""Revision 004 x86 entrypoint around the frozen portable runner core."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
from pathlib import Path
import sys
from typing import Any

import jsonschema


PACKET_ID = "G1-X86-PI-COMPAT-004"
ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "poc_llm/tools/run_gate1_prescreen.py"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_artifact(item: dict[str, Any], label: str) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or digest(path) != item["sha256"]:
        raise ValueError(f"{label} artifact identity mismatch")
    return path


def locked_paths(lock: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key, item in lock["artifacts"].items():
        paths[key] = resolve_artifact(item, f"locked {key}")
    return paths


def load_core() -> Any:
    spec = importlib.util.spec_from_file_location("gate1_runner_core_v3", CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("portable runner core cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unavailable_report(core: Any, args: argparse.Namespace, error: Exception) -> dict[str, Any]:
    namespace = argparse.Namespace(run_id=args.run_id, platform="ubuntu-x86_64")
    report = core.empty_report(namespace)
    report["packet_id"] = PACKET_ID
    report["violations"].append(str(error))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    core = load_core()
    core.PACKET_ID = PACKET_ID
    core.ARCH = {"ubuntu-x86_64": "x86_64"}
    report: dict[str, Any]
    exit_code = 2
    try:
        lock = load(args.lock)
        paths = locked_paths(lock)
        manifest = load(args.candidate_manifest)
        jsonschema.validate(manifest, load(paths["candidate_schema"]))
        acquisition_path = resolve_artifact(manifest["acquisition_manifest"], "acquisition manifest")
        acquisition = load(acquisition_path)
        jsonschema.validate(acquisition, load(paths["acquisition_schema"]))
        if (
            acquisition["candidate_id"] != manifest["candidate_id"]
            or acquisition["pairing_revision"] != manifest["pairing_revision"]
            or acquisition["logical_runtime"] != manifest["logical_runtime"]
        ):
            raise ValueError("candidate/acquisition logical identity mismatch")
        platform_artifacts = acquisition["platforms"]["ubuntu-x86_64"]
        runtime_path = resolve_artifact(platform_artifacts["runtime_artifact"], "x86 runtime")
        resolve_artifact(platform_artifacts["dependency_bundle"], "x86 dependency bundle")
        if manifest["runtime"] != {
            "name": manifest["runtime"]["name"],
            "version": manifest["runtime"]["version"],
            "path": platform_artifacts["runtime_artifact"]["path"],
            "sha256": platform_artifacts["runtime_artifact"]["sha256"],
        }:
            raise ValueError("candidate x86 runtime does not match acquisition manifest")
        if str(runtime_path.relative_to(ROOT)) not in manifest["commands"]["ubuntu-x86_64"]["argv"]:
            raise ValueError("x86 command is not bound to acquired runtime")

        original_argv = sys.argv
        captured = StringIO()
        try:
            sys.argv = [
                str(CORE_PATH), "--platform", "ubuntu-x86_64", "--run-id", args.run_id,
                "--candidate-manifest", str(args.candidate_manifest), "--lock", str(args.lock),
                "--raw-dir", str(args.raw_dir),
            ]
            with redirect_stdout(captured):
                exit_code = core.main()
        finally:
            sys.argv = original_argv
        report = json.loads(captured.getvalue())
        report["identity"].update({
            "acquisition_manifest_sha256": digest(acquisition_path),
            "logical_runtime_source_sha256": manifest["logical_runtime"]["source_sha256"],
            "dependency_bundle_sha256": platform_artifacts["dependency_bundle"]["sha256"],
            "acquisition_schema_sha256": lock["artifacts"]["acquisition_schema"]["sha256"],
            "runner_core_sha256": lock["artifacts"]["runner_core"]["sha256"],
            "x86_result_schema_sha256": lock["artifacts"]["x86_result_schema"]["sha256"],
            "pi_result_schema_sha256": lock["artifacts"]["pi_result_schema"]["sha256"],
        })
        jsonschema.validate(report, load(paths["x86_result_schema"]))
    except (json.JSONDecodeError, jsonschema.ValidationError, OSError, KeyError, TypeError, ValueError) as error:
        report = unavailable_report(core, args, error)
        report["identity"].update({
            "acquisition_manifest_sha256":"UNAVAILABLE",
            "logical_runtime_source_sha256":"UNAVAILABLE",
            "dependency_bundle_sha256":"UNAVAILABLE",
            "acquisition_schema_sha256":"UNAVAILABLE",
            "runner_core_sha256":"UNAVAILABLE",
            "x86_result_schema_sha256":"UNAVAILABLE",
            "pi_result_schema_sha256":"UNAVAILABLE",
        })
        exit_code = 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
