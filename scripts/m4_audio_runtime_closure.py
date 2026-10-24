#!/usr/bin/env python3
"""Create and verify the M4a Audio offline runtime closure.

Wheel artifacts remain outside Core Git.  This tool only records their immutable
identity and rejects a runtime that resolves anything outside its isolated venv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class ClosureError(RuntimeError):
    """The runtime closure is incomplete or does not match its manifest."""


SCHEMA = "sbd.m4a.runtime-closure.v1"
_ALLOWED_BOOTSTRAP_DISTRIBUTIONS = {"pip"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClosureError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ClosureError(f"{label} must be a JSON object")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ClosureError(f"{label} must be a non-empty string")
    return value


def _manifest_packages(manifest: dict[str, Any]) -> list[dict[str, str | int]]:
    if manifest.get("schema") != SCHEMA:
        raise ClosureError(f"unsupported manifest schema: {manifest.get('schema')!r}")
    raw = manifest.get("packages")
    if not isinstance(raw, list) or not raw:
        raise ClosureError("manifest packages must be a non-empty list")
    packages: list[dict[str, str | int]] = []
    names: set[str] = set()
    filenames: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ClosureError(f"packages[{index}] must be an object")
        package = {
            "distribution": _require_string(item.get("distribution"), f"packages[{index}].distribution"),
            "version": _require_string(item.get("version"), f"packages[{index}].version"),
            "filename": _require_string(item.get("filename"), f"packages[{index}].filename"),
            "sha256": _require_string(item.get("sha256"), f"packages[{index}].sha256"),
            "source_locator": _require_string(item.get("source_locator"), f"packages[{index}].source_locator"),
            "license_reference": _require_string(item.get("license_reference"), f"packages[{index}].license_reference"),
            "import_name": _require_string(item.get("import_name"), f"packages[{index}].import_name"),
        }
        size = item.get("size")
        if type(size) is not int or size < 1:
            raise ClosureError(f"packages[{index}].size must be a positive integer")
        package["size"] = size
        if len(package["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in package["sha256"]):
            raise ClosureError(f"packages[{index}].sha256 must be lowercase SHA-256")
        name = package["distribution"].lower()
        if name in names or package["filename"] in filenames:
            raise ClosureError("manifest package distributions and filenames must be unique")
        names.add(name)
        filenames.add(package["filename"])
        packages.append(package)
    return packages


def verify_wheel_directory(wheel_dir: Path, packages: list[dict[str, str | int]]) -> None:
    if not wheel_dir.is_dir():
        raise ClosureError(f"wheel directory does not exist: {wheel_dir}")
    expected = {str(package["filename"]) for package in packages}
    actual = {path.name for path in wheel_dir.glob("*.whl")}
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        raise ClosureError(f"wheel inventory mismatch: missing={missing}, extra={extra}")
    for package in packages:
        wheel = wheel_dir / str(package["filename"])
        if wheel.stat().st_size != package["size"]:
            raise ClosureError(f"wheel size mismatch: {wheel.name}")
        if _sha256(wheel) != package["sha256"]:
            raise ClosureError(f"wheel checksum mismatch: {wheel.name}")


def _venv_config(venv: Path) -> dict[str, str]:
    config = venv / "pyvenv.cfg"
    if not config.is_file():
        raise ClosureError(f"missing venv config: {config}")
    values: dict[str, str] = {}
    for line in config.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    if values.get("include-system-site-packages", "").lower() != "false":
        raise ClosureError("venv must set include-system-site-packages = false")
    return values


def _run_json(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> Any:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if completed.returncode != 0:
        raise ClosureError(f"command failed ({' '.join(command)}): {completed.stderr.strip()}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ClosureError(f"command did not return JSON: {' '.join(command)}") from exc


def _verify_installed_packages(venv_python: Path, packages: list[dict[str, str | int]]) -> None:
    installed = _run_json([str(venv_python), "-m", "pip", "list", "--format=json"])
    if not isinstance(installed, list):
        raise ClosureError("pip list did not return a list")
    actual = {item["name"].lower(): item["version"] for item in installed if isinstance(item, dict)}
    expected = {str(item["distribution"]).lower(): str(item["version"]) for item in packages}
    extras = set(actual) - set(expected) - _ALLOWED_BOOTSTRAP_DISTRIBUTIONS
    missing = set(expected) - set(actual)
    mismatched = sorted(
        name for name in expected.keys() & actual.keys() if expected[name] != actual[name]
    )
    if missing or extras or mismatched:
        raise ClosureError(
            "installed package mismatch: "
            f"missing={sorted(missing)}, extra={sorted(extras)}, version={mismatched}"
        )


def _verify_core_imports(
    venv_python: Path,
    core_repo: Path,
    packages: list[dict[str, str | int]],
    config: Path,
) -> None:
    imports = [str(item["import_name"]) for item in packages]
    code = """
import importlib, json, sys
from pathlib import Path
from sbd.core.audio import make_audio_input, make_audio_output
from sbd.core.config import load_config

imports = json.loads(sys.argv[1])
locations = {}
for name in imports:
    module = importlib.import_module(name)
    locations[name] = str(Path(module.__file__).resolve())
config = load_config(local_path=Path(sys.argv[2]), environ={})
if config.core.audio.driver != "alsa":
    raise RuntimeError("Core closure config must select core.audio.driver=alsa")
make_audio_input(config.core.audio)
make_audio_output(config.core.audio)
print(json.dumps({"prefix": sys.prefix, "base_prefix": sys.base_prefix, "locations": locations}))
"""
    environment = {**os.environ, "PYTHONPATH": str(core_repo / "src")}
    result = _run_json(
        [str(venv_python), "-c", code, json.dumps(imports), str(config)],
        cwd=core_repo,
        env=environment,
    )
    prefix = Path(_require_string(result.get("prefix"), "runtime prefix")).resolve()
    if prefix != venv_python.parent.parent.resolve() or result.get("base_prefix") == result.get("prefix"):
        raise ClosureError("imports did not run through the isolated venv")
    locations = result.get("locations")
    if not isinstance(locations, dict):
        raise ClosureError("runtime import locations are missing")
    for name, location in locations.items():
        if not Path(_require_string(location, f"import location {name}")).is_relative_to(prefix):
            raise ClosureError(f"system-resolved package import: {name}")


def _verify_runtime_imports(venv_python: Path, packages: list[dict[str, str | int]]) -> None:
    imports = [str(item["import_name"]) for item in packages]
    code = """
import importlib, json, sys
from pathlib import Path

locations = {}
for name in json.loads(sys.argv[1]):
    module = importlib.import_module(name)
    locations[name] = str(Path(module.__file__).resolve())
print(json.dumps({"prefix": sys.prefix, "base_prefix": sys.base_prefix, "locations": locations}))
"""
    result = _run_json([str(venv_python), "-c", code, json.dumps(imports)])
    prefix = Path(_require_string(result.get("prefix"), "runtime prefix")).resolve()
    if prefix != venv_python.parent.parent.resolve() or result.get("base_prefix") == result.get("prefix"):
        raise ClosureError("imports did not run through the isolated venv")
    locations = result.get("locations")
    if not isinstance(locations, dict):
        raise ClosureError("runtime import locations are missing")
    for name, location in locations.items():
        if not Path(_require_string(location, f"import location {name}")).is_relative_to(prefix):
            raise ClosureError(f"system-resolved package import: {name}")


def create_manifest(args: argparse.Namespace) -> dict[str, object]:
    packages: list[dict[str, object]] = []
    for raw in args.package:
        fields = raw.split("|", 5)
        if len(fields) != 6:
            raise ClosureError("--package must be filename|distribution|version|source_locator|license_reference|import_name")
        filename, distribution, version, source_locator, license_reference, import_name = fields
        wheel = args.wheel_dir / filename
        if not wheel.is_file():
            raise ClosureError(f"wheel does not exist: {wheel}")
        packages.append({
            "filename": filename,
            "distribution": distribution,
            "version": version,
            "source_locator": source_locator,
            "license_reference": license_reference,
            "import_name": import_name,
            "size": wheel.stat().st_size,
            "sha256": _sha256(wheel),
        })
    manifest = {
        "schema": SCHEMA,
        "runtime": _require_string(args.runtime, "runtime"),
        "interpreter": {"path": str(args.interpreter.resolve()), "version": args.python_version},
        "packages": packages,
    }
    _manifest_packages(manifest)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "CREATED", "manifest": str(args.output), "sha256": _sha256(args.output)}


def preflight(args: argparse.Namespace) -> dict[str, str]:
    manifest = _read_json(args.manifest, "manifest")
    packages = _manifest_packages(manifest)
    _venv_config(args.venv)
    verify_wheel_directory(args.wheel_dir, packages)
    venv_python = args.venv / "bin" / "python"
    if not venv_python.is_file():
        raise ClosureError(f"missing venv interpreter: {venv_python}")
    interpreter = manifest.get("interpreter")
    if not isinstance(interpreter, dict):
        raise ClosureError("manifest interpreter is required")
    expected_version = _require_string(interpreter.get("version"), "interpreter.version")
    actual_version = _run_json([str(venv_python), "-c", "import json, sys; print(json.dumps(sys.version.split()[0]))"])
    if actual_version != expected_version:
        raise ClosureError(f"interpreter version mismatch: expected={expected_version}, actual={actual_version}")
    _verify_installed_packages(venv_python, packages)
    if args.core_repo is None:
        _verify_runtime_imports(venv_python, packages)
        return {"status": "PASS", "manifest_sha256": _sha256(args.manifest)}
    if args.core_sha is None or args.config is None:
        raise ClosureError("controller preflight requires --core-sha and --config")
    actual_sha = subprocess.check_output(["git", "-C", str(args.core_repo), "rev-parse", "HEAD"], text=True).strip()
    if actual_sha != args.core_sha:
        raise ClosureError(f"Core SHA mismatch: expected={args.core_sha}, actual={actual_sha}")
    _verify_core_imports(venv_python, args.core_repo, packages, args.config)
    return {"status": "PASS", "core_sha": actual_sha, "manifest_sha256": _sha256(args.manifest)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    manifest_parser = command.add_parser("create-manifest")
    manifest_parser.add_argument("--runtime", required=True)
    manifest_parser.add_argument("--wheel-dir", type=Path, required=True)
    manifest_parser.add_argument("--interpreter", type=Path, required=True)
    manifest_parser.add_argument("--python-version", required=True)
    manifest_parser.add_argument("--output", type=Path, required=True)
    manifest_parser.add_argument("--package", action="append", default=[], required=True)
    preflight_parser = command.add_parser("preflight")
    preflight_parser.add_argument("--manifest", type=Path, required=True)
    preflight_parser.add_argument("--wheel-dir", type=Path, required=True)
    preflight_parser.add_argument("--venv", type=Path, required=True)
    preflight_parser.add_argument("--core-repo", type=Path)
    preflight_parser.add_argument("--core-sha")
    preflight_parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        result = create_manifest(args) if args.command == "create-manifest" else preflight(args)
    except ClosureError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
