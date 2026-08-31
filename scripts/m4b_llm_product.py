#!/usr/bin/env python3
"""Install and preflight the checksum-locked M4b LiteRT-LM product."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sbd.cognition.litert_lm.lock import (  # noqa: E402
    EXPECTED_RUNTIME,
    LLMArtifactLock,
    LLMLockError,
    RuntimeClosure,
)
from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler  # noqa: E402


class ProductFailure(RuntimeError):
    """A sanitized product preparation failure."""


BASE_PYTHON = Path("/usr/bin/python3.13")
PYTHON_PACKAGES = tuple(sorted((
    "python3.13-minimal",
    "libpython3.13-minimal",
    "python3.13",
    "libpython3.13-stdlib",
    "python3.13-venv",
)))
EXPECTED_PYTHON_ABI = {
    "implementation": "CPython",
    "version": "3.13.5",
    "soabi": "cpython-313-aarch64-linux-gnu",
    "multiarch": "aarch64-linux-gnu",
    "abiflags": "",
    "pointer_bits": 64,
    "byteorder": "little",
    "stdlib": "/usr/lib/python3.13",
    "platstdlib": "/usr/lib/python3.13",
    "lib_dynload": "/usr/lib/python3.13/lib-dynload",
}


@dataclass(frozen=True, slots=True)
class PythonPackageAttestation:
    name: str
    status: str
    version: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "version": self.version}


@dataclass(frozen=True, slots=True)
class PythonABIAttestation:
    base_executable: str
    base_executable_sha256: str
    implementation: str
    version: str
    sys_version: str
    soabi: str
    multiarch: str
    abiflags: str
    pointer_bits: int
    byteorder: str
    stdlib: str
    platstdlib: str
    lib_dynload: str
    glibc_version: str
    packages: tuple[PythonPackageAttestation, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "base_executable": self.base_executable,
            "base_executable_sha256": self.base_executable_sha256,
            "implementation": self.implementation,
            "version": self.version,
            "sys_version": self.sys_version,
            "soabi": self.soabi,
            "multiarch": self.multiarch,
            "abiflags": self.abiflags,
            "pointer_bits": self.pointer_bits,
            "byteorder": self.byteorder,
            "stdlib": self.stdlib,
            "platstdlib": self.platstdlib,
            "lib_dynload": self.lib_dynload,
            "glibc_version": self.glibc_version,
            "packages": [item.as_dict() for item in self.packages],
        }

    @property
    def sha256(self) -> str:
        payload = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_mapping(cls, value: object) -> "PythonABIAttestation":
        scalar_keys = {
            "base_executable", "base_executable_sha256", "implementation", "version",
            "sys_version", "soabi", "multiarch", "abiflags", "pointer_bits",
            "byteorder", "stdlib", "platstdlib", "lib_dynload", "glibc_version",
        }
        if type(value) is not dict or set(value) != scalar_keys | {"packages"}:
            raise ProductFailure("Python ABI attestation is invalid")
        packages_value = value["packages"]
        if type(packages_value) is not list:
            raise ProductFailure("Python ABI attestation is invalid")
        packages: list[PythonPackageAttestation] = []
        for item in packages_value:
            if (
                type(item) is not dict
                or set(item) != {"name", "status", "version"}
                or any(type(item[key]) is not str for key in item)
            ):
                raise ProductFailure("Python ABI attestation is invalid")
            packages.append(PythonPackageAttestation(**item))
        string_keys = scalar_keys - {"pointer_bits"}
        if any(type(value[key]) is not str for key in string_keys) or type(value["pointer_bits"]) is not int:
            raise ProductFailure("Python ABI attestation is invalid")
        return cls(
            **{key: value[key] for key in scalar_keys},
            packages=tuple(packages),
        )


@dataclass(frozen=True, slots=True)
class InstallInventory:
    files: Mapping[str, Mapping[str, object]]
    python_abi: PythonABIAttestation
    python_abi_sha256: str
    inventory_sha256: str


PROTECTED_PATHS = (
    "src", "tests", "scripts", "requirements", "config.example.yaml", "pyproject.toml",
    ".github/workflows/candidate-portable.yml",
)


def _clean_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ProductFailure("controlled input is missing, unreadable, or unsafe") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ProductFailure("controlled input is not a regular file")
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _read_regular_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ProductFailure("controlled input is missing, unreadable, or unsafe") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ProductFailure("controlled input is not a regular file")
        blocks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            blocks.append(block)
        return b"".join(blocks)
    finally:
        os.close(descriptor)


def validate_python_abi(value: PythonABIAttestation) -> None:
    """Validate the fixed target ABI while retaining run-specific identity fields."""
    value = PythonABIAttestation.from_mapping(value.as_dict())
    observed = value.as_dict()
    for key, expected in EXPECTED_PYTHON_ABI.items():
        if observed[key] != expected:
            raise ProductFailure("target Python ABI identity mismatch")
    if (
        value.base_executable != str(BASE_PYTHON)
        or not re.fullmatch(r"[0-9a-f]{64}", value.base_executable_sha256)
        or not value.sys_version.startswith("3.13.5 ")
        or not re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", value.glibc_version)
    ):
        raise ProductFailure("target Python ABI identity mismatch")
    if tuple(item.name for item in value.packages) != PYTHON_PACKAGES:
        raise ProductFailure("target Python package set mismatch")
    versions = {item.version for item in value.packages}
    if (
        any(item.status != "install ok installed" for item in value.packages)
        or len(versions) != 1
        or not re.fullmatch(r"3\.13\.5-.+", next(iter(versions), ""))
    ):
        raise ProductFailure("target Python package identity mismatch")


def verify_python_abi(
    expected: PythonABIAttestation,
    actual: PythonABIAttestation,
) -> None:
    """Fail closed when any run-bound ABI field drifts."""
    validate_python_abi(expected)
    validate_python_abi(actual)
    if expected.as_dict() != actual.as_dict() or expected.sha256 != actual.sha256:
        raise ProductFailure("target Python ABI attestation drift")


def capture_python_abi(
    base_python: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> PythonABIAttestation:
    """Capture the exact target-owned CPython and Debian package ABI identity."""
    if base_python != BASE_PYTHON:
        raise ProductFailure("base interpreter identity mismatch")
    try:
        metadata = os.lstat(base_python)
    except OSError as error:
        raise ProductFailure("base interpreter is missing or unsafe") from error
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != 0:
        raise ProductFailure("base interpreter is missing or unsafe")
    probe_code = (
        "import json,platform,struct,sys,sysconfig;"
        "print(json.dumps({"
        "'implementation':platform.python_implementation(),"
        "'version':platform.python_version(),"
        "'sys_version':sys.version,"
        "'soabi':sysconfig.get_config_var('SOABI'),"
        "'multiarch':sysconfig.get_config_var('MULTIARCH'),"
        "'abiflags':sys.abiflags,"
        "'pointer_bits':struct.calcsize('P')*8,"
        "'byteorder':sys.byteorder,"
        "'stdlib':sysconfig.get_path('stdlib'),"
        "'platstdlib':sysconfig.get_path('platstdlib'),"
        "'lib_dynload':sysconfig.get_path('platstdlib')+'/lib-dynload',"
        "'glibc_version':platform.libc_ver()[1]"
        "},sort_keys=True))"
    )
    try:
        probe = runner(
            [str(base_python), "-I", "-B", "-c", probe_code],
            capture_output=True,
            text=True,
            check=False,
            env=_clean_environment(),
        )
        if probe.returncode != 0:
            raise ProductFailure("target Python ABI probe failed")
        values = json.loads(probe.stdout)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ProductFailure("target Python ABI probe failed") from error
    probe_keys = set(EXPECTED_PYTHON_ABI) | {"sys_version", "glibc_version"}
    if type(values) is not dict or set(values) != probe_keys:
        raise ProductFailure("target Python ABI probe failed")
    packages: list[PythonPackageAttestation] = []
    for name in PYTHON_PACKAGES:
        try:
            result = runner(
                ["/usr/bin/dpkg-query", "-W", "-f=${Status}\\t${Version}\\n", name],
                capture_output=True,
                text=True,
                check=False,
                env=_clean_environment(),
            )
        except OSError as error:
            raise ProductFailure("target Python package probe failed") from error
        fields = result.stdout.rstrip("\n").split("\t") if result.returncode == 0 else []
        if len(fields) != 2:
            raise ProductFailure("target Python package probe failed")
        packages.append(PythonPackageAttestation(name, fields[0], fields[1]))
    attestation = PythonABIAttestation(
        base_executable=str(base_python),
        base_executable_sha256=_digest(base_python),
        packages=tuple(packages),
        **values,
    )
    validate_python_abi(attestation)
    return attestation


def _verify_file(path: Path, *, size: int, sha256: str, label: str) -> None:
    try:
        actual_size = path.stat(follow_symlinks=False).st_size
    except OSError as error:
        raise ProductFailure(f"{label} is missing or unsafe") from error
    if path.is_symlink() or not path.is_file() or actual_size != size or _digest(path) != sha256:
        raise ProductFailure(f"{label} identity mismatch")


def _load_install_inventory(path: Path) -> InstallInventory:
    try:
        raw_bytes = _read_regular_bytes(path)
        inventory = json.loads(raw_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProductFailure("installed product inventory is invalid") from error
    if (
        type(inventory) is not dict
        or set(inventory) != {
            "schema_version", "python_abi_attestation",
            "python_abi_attestation_sha256", "files",
        }
        or inventory["schema_version"] != 1
        or type(inventory["files"]) is not list
        or type(inventory["python_abi_attestation_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", inventory["python_abi_attestation_sha256"])
    ):
        raise ProductFailure("installed product inventory is invalid")
    attestation = PythonABIAttestation.from_mapping(inventory["python_abi_attestation"])
    validate_python_abi(attestation)
    if attestation.sha256 != inventory["python_abi_attestation_sha256"]:
        raise ProductFailure("installed product ABI attestation checksum mismatch")
    expected: dict[str, dict[str, object]] = {}
    for row in inventory["files"]:
        if type(row) is not dict or set(row) != {"relative_path", "size_bytes", "sha256"}:
            raise ProductFailure("installed product inventory is invalid")
        relative_path = row["relative_path"]
        if (
            type(relative_path) is not str
            or not relative_path
            or PurePosixPath(relative_path).is_absolute()
            or ".." in PurePosixPath(relative_path).parts
            or relative_path in expected
            or type(row["size_bytes"]) is not int
            or row["size_bytes"] < 0
            or type(row["sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        ):
            raise ProductFailure("installed product inventory is invalid")
        expected[relative_path] = row
    return InstallInventory(
        expected,
        attestation,
        attestation.sha256,
        hashlib.sha256(raw_bytes).hexdigest(),
    )


def _load(lock_path: Path, manifest_path: Path, notice_path: Path) -> tuple[LLMArtifactLock, RuntimeClosure]:
    try:
        lock = LLMArtifactLock.load(lock_path)
        raw = json.loads(_read_regular_bytes(lock_path))
        closure = RuntimeClosure.load(
            manifest_path,
            expected_digest=raw["runtime_closure"]["manifest_sha256"],
        )
        expected_notice = raw["licenses"]["notice_sha256"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, LLMLockError) as error:
        raise ProductFailure("product lock or runtime manifest is invalid") from error
    if _digest(notice_path) != expected_notice:
        raise ProductFailure("third-party notice identity mismatch")
    return lock, closure


def _extract_wheel(wheel: Path, destination: Path, closure: RuntimeClosure) -> None:
    expected = {item.relative_path: item for item in closure.files}
    try:
        with zipfile.ZipFile(wheel) as archive:
            files: dict[str, zipfile.ZipInfo] = {}
            for info in archive.infolist():
                name = info.filename.rstrip("/")
                if not name:
                    continue
                path = PurePosixPath(name)
                mode = info.external_attr >> 16
                if path.is_absolute() or ".." in path.parts or (mode & 0o170000) == 0o120000:
                    raise ProductFailure("runtime wheel contains an unsafe entry")
                if info.is_dir():
                    continue
                if name in files:
                    raise ProductFailure("runtime wheel contains a duplicate entry")
                files[name] = info
            if set(files) != set(expected):
                raise ProductFailure("runtime wheel inventory mismatch")
            destination.mkdir(parents=True, mode=0o700)
            for name in sorted(files):
                target = destination.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(files[name]) as source, target.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024 * 1024)
    except (OSError, zipfile.BadZipFile) as error:
        raise ProductFailure("runtime wheel extraction failed") from error
    try:
        closure.verify_install(destination)
    except LLMLockError as error:
        raise ProductFailure("extracted runtime identity mismatch") from error


def _verify_venv(
    install_root: Path,
    runtime_python: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    expected_python = install_root / "bin/python"
    if (
        runtime_python != expected_python
        or not runtime_python.is_absolute()
        or install_root.is_symlink()
        or not install_root.is_dir()
    ):
        raise ProductFailure("runtime interpreter escaped installed product")
    try:
        metadata = os.lstat(runtime_python)
    except OSError as error:
        raise ProductFailure("runtime interpreter is missing or unsafe") from error
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ProductFailure("runtime interpreter is missing or unsafe")
    pyvenv = install_root / "pyvenv.cfg"
    try:
        pyvenv_metadata = os.lstat(pyvenv)
        if not stat.S_ISREG(pyvenv_metadata.st_mode) or stat.S_ISLNK(pyvenv_metadata.st_mode):
            raise ProductFailure("isolated runtime configuration is invalid")
        lines = pyvenv.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ProductFailure("isolated runtime configuration is invalid") from error
    config: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        key, separator, value = line.partition("=")
        key = key.strip().lower()
        if not separator or not key or key in config:
            raise ProductFailure("isolated runtime configuration is invalid")
        config[key] = value.strip()
    if (
        config.get("home") != str(BASE_PYTHON.parent)
        or config.get("executable") != str(BASE_PYTHON)
        or config.get("include-system-site-packages", "").lower() != "false"
        or config.get("version") != "3.13.5"
    ):
        raise ProductFailure("isolated runtime configuration mismatch")
    probe_code = (
        "import importlib.util,json,pathlib,site,sys,sysconfig;"
        "spec=importlib.util.find_spec('litert_lm');"
        "print(json.dumps({"
        "'implementation':sys.implementation.name,"
        "'version':'.'.join(map(str,sys.version_info[:3])),"
        "'prefix':sys.prefix,"
        "'base_prefix':sys.base_prefix,"
        "'enable_user_site':site.ENABLE_USER_SITE,"
        "'paths':sys.path,"
        "'stdlib':sysconfig.get_path('stdlib'),"
        "'platstdlib':sysconfig.get_path('platstdlib'),"
        "'json_path':__import__('json').__file__,"
        "'extension_path':__import__('_json').__file__,"
        "'module_origin':None if spec is None else spec.origin"
        "},sort_keys=True))"
    )
    try:
        probe = runner(
            [str(runtime_python), "-I", "-B", "-c", probe_code],
            capture_output=True,
            text=True,
            check=False,
            env=_clean_environment(),
        )
        identity = json.loads(probe.stdout)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ProductFailure("runtime interpreter isolation probe failed") from error
    expected_keys = {
        "implementation", "version", "prefix", "base_prefix", "enable_user_site",
        "paths", "stdlib", "platstdlib", "json_path", "extension_path",
        "module_origin",
    }
    product_site = install_root / "lib/python3.13/site-packages"
    string_fields = {
        "implementation", "version", "prefix", "base_prefix", "stdlib",
        "platstdlib", "json_path", "extension_path", "module_origin",
    }
    if (
        probe.returncode != 0
        or type(identity) is not dict
        or set(identity) != expected_keys
        or any(type(identity[name]) is not str for name in string_fields)
        or identity["implementation"] != "cpython"
        or identity["version"] != "3.13.5"
        or Path(identity["prefix"]) != install_root
        or Path(identity["base_prefix"]) != Path("/usr")
        or identity["enable_user_site"] is not False
        or identity["stdlib"] != EXPECTED_PYTHON_ABI["stdlib"]
        or identity["platstdlib"] != EXPECTED_PYTHON_ABI["platstdlib"]
        or type(identity["paths"]) is not list
        or type(identity["module_origin"]) is not str
        or not Path(identity["module_origin"]).is_relative_to(product_site)
        or type(identity["json_path"]) is not str
        or not Path(identity["json_path"]).is_relative_to(Path(str(EXPECTED_PYTHON_ABI["stdlib"])))
        or type(identity["extension_path"]) is not str
        or not Path(identity["extension_path"]).is_relative_to(Path(str(EXPECTED_PYTHON_ABI["lib_dynload"])))
    ):
        raise ProductFailure("runtime interpreter isolation mismatch")
    for item in identity["paths"]:
        if type(item) is not str:
            raise ProductFailure("runtime interpreter isolation mismatch")
        normalized = item.lower()
        if ("site-packages" in normalized or "dist-packages" in normalized) and not Path(item).is_relative_to(product_site):
            raise ProductFailure("runtime interpreter isolation mismatch")


def install(
    *,
    lock_path: Path,
    manifest_path: Path,
    notice_path: Path,
    wheel_path: Path,
    runtime_python: Path,
    output: Path,
    capture_abi: Callable[[Path], PythonABIAttestation] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ProductFailure("install output already exists")
    lock, closure = _load(lock_path, manifest_path, notice_path)
    _verify_file(
        wheel_path,
        size=int(lock.runtime["wheel_size_bytes"]),
        sha256=str(lock.runtime["wheel_sha256"]),
        label="runtime wheel",
    )
    python_abi = (capture_abi or capture_python_abi)(runtime_python)
    validate_python_abi(python_abi)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        created = runner(
            [str(runtime_python), "-I", "-B", "-m", "venv", "--copies", "--without-pip", str(staging)],
            capture_output=True, text=True, check=False,
            env=_clean_environment(),
        )
        if created.returncode != 0:
            raise ProductFailure("isolated runtime creation failed")
        for activation in (staging / "bin").glob("[Aa]ctivate*"):
            activation.unlink()
        for path in tuple(staging.rglob("*")):
            if path.is_symlink():
                path.unlink()
        site_packages = staging / "lib/python3.13/site-packages"
        _extract_wheel(wheel_path, site_packages, closure)
        shutil.copyfile(lock_path, staging / "llm-artifacts.json", follow_symlinks=False)
        shutil.copyfile(manifest_path, staging / "llm-runtime-rpi-cp313.json", follow_symlinks=False)
        shutil.copyfile(notice_path, staging / "THIRD_PARTY_NOTICES.md", follow_symlinks=False)
        _verify_venv(staging, staging / "bin/python", runner=runner)
        rows = []
        for path in sorted(staging.rglob("*")):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ProductFailure("isolated runtime contains an unsafe entry")
            if path.is_file():
                rows.append({
                    "relative_path": path.relative_to(staging).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _digest(path),
                })
        (staging / "install-inventory.json").write_text(
            json.dumps({
                "schema_version": 1,
                "python_abi_attestation": python_abi.as_dict(),
                "python_abi_attestation_sha256": python_abi.sha256,
                "files": rows,
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.rename(staging, output)
    except BaseException as error:
        try:
            shutil.rmtree(staging)
        except FileNotFoundError:
            pass
        except OSError as cleanup:
            raise ProductFailure("install staging cleanup failed") from cleanup
        if staging.exists() or staging.is_symlink():
            raise ProductFailure("install staging cleanup failed") from error
        raise
    return {
        "status": "Pass",
        "candidate_id": lock.identity.candidate_id,
        "runtime_manifest_sha256": closure.digest,
        "runtime_file_count": len(closure.files),
        "install_file_count": len(rows) + 1,
        "python_abi_attestation_sha256": python_abi.sha256,
    }


def verify_installed_python_abi(
    *,
    install_root: Path,
    runtime_python: Path,
    capture_abi: Callable[[Path], PythonABIAttestation] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> InstallInventory:
    """Re-capture and bind a deployed venv to its protected install attestation."""
    inventory = _load_install_inventory(install_root / "install-inventory.json")
    actual = (capture_abi or capture_python_abi)(BASE_PYTHON)
    verify_python_abi(inventory.python_abi, actual)
    _verify_venv(install_root, runtime_python, runner=runner)
    return inventory


def preflight(
    *,
    lock_path: Path,
    manifest_path: Path,
    notice_path: Path,
    install_root: Path,
    model_path: Path,
    product_config_path: Path,
    runtime_python: Path,
    candidate_sha: str,
    repo_root: Path,
    capture_abi: Callable[[Path], PythonABIAttestation] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    install_root = install_root.absolute()
    runtime_python = runtime_python.absolute()
    lock, closure = _load(lock_path, manifest_path, notice_path)
    try:
        closure.verify_install(install_root / "lib/python3.13/site-packages")
        lock.verify_config_paths(type("Paths", (), {
            "model_path": model_path,
            "product_config_path": product_config_path,
        })())
    except (LLMLockError, OSError) as error:
        raise ProductFailure("installed product identity mismatch") from error
    tracked = {
        "llm-artifacts.json": _digest(lock_path),
        "llm-runtime-rpi-cp313.json": _digest(manifest_path),
        "THIRD_PARTY_NOTICES.md": _digest(notice_path),
    }
    for name, digest in tracked.items():
        installed = install_root / name
        if _digest(installed) != digest:
            raise ProductFailure("installed metadata identity mismatch")
    inventory_path = install_root / "install-inventory.json"
    inventory = verify_installed_python_abi(
        install_root=install_root,
        runtime_python=runtime_python,
        capture_abi=capture_abi,
        runner=runner,
    )
    expected_inventory = inventory.files
    actual_inventory = {
        path.relative_to(install_root).as_posix(): path
        for path in install_root.rglob("*")
        if path.is_file() and path != inventory_path
    }
    unsafe = [
        path for path in install_root.rglob("*")
        if path.is_symlink() or not (path.is_file() or path.is_dir())
    ]
    if install_root.is_symlink() or unsafe or set(actual_inventory) != set(expected_inventory):
        raise ProductFailure("installed product inventory mismatch")
    for name, path in actual_inventory.items():
        row = expected_inventory[name]
        if (
            path.stat().st_size != row["size_bytes"]
            or _digest(path) != row["sha256"]
        ):
            raise ProductFailure("installed product inventory identity mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
        raise ProductFailure("candidate SHA identity is invalid")
    try:
        machine = platform.machine()
        model = Path("/proc/device-tree/model").read_text(encoding="ascii").rstrip("\x00")
        os_release = Path("/etc/os-release").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ProductFailure("target platform identity is unavailable") from error
    if machine != "aarch64" or "Raspberry Pi 5" not in model or 'VERSION_ID="13"' not in os_release:
        raise ProductFailure("target platform identity mismatch")
    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--", *PROTECTED_PATHS],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ProductFailure("candidate repository identity is unavailable") from error
    if head != candidate_sha or dirty:
        raise ProductFailure("candidate SHA or protected-path state mismatch")
    try:
        ProcLLMResourceSampler().sample(child_pid=os.getpid(), child_pgid=os.getpgrp())
    except (OSError, RuntimeError, ValueError) as error:
        raise ProductFailure("target resource sampler capability is unavailable") from error
    return {
        "status": "Pass",
        "candidate_id": lock.identity.candidate_id,
        "pairing_revision": lock.identity.pairing_revision,
        "artifact_lock_sha256": lock.digest,
        "runtime_manifest_sha256": closure.digest,
        "runtime_file_count": len(closure.files),
        "install_file_count": len(expected_inventory) + 1,
        "install_inventory_sha256": inventory.inventory_sha256,
        "model_sha256": lock.model["sha256"],
        "product_config_sha256": lock.product_profile["config_sha256"],
        "candidate_sha": candidate_sha,
        "platform": "pi-debian13-aarch64",
        "python": "CPython 3.13.5",
        "python_abi_attestation_sha256": inventory.python_abi_sha256,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--lock", type=Path, required=True)
    common.add_argument("--manifest", type=Path, required=True)
    common.add_argument("--notices", type=Path, required=True)
    install_parser = sub.add_parser("install", parents=[common])
    install_parser.add_argument("--wheel", type=Path, required=True)
    install_parser.add_argument("--runtime-python", type=Path, required=True)
    install_parser.add_argument("--output", type=Path, required=True)
    preflight_parser = sub.add_parser("preflight", parents=[common])
    preflight_parser.add_argument("--install-root", type=Path, required=True)
    preflight_parser.add_argument("--model", type=Path, required=True)
    preflight_parser.add_argument("--product-config", type=Path, required=True)
    preflight_parser.add_argument("--runtime-python", type=Path, required=True)
    preflight_parser.add_argument("--candidate-sha", required=True)
    preflight_parser.add_argument("--repo", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install(
                lock_path=args.lock,
                manifest_path=args.manifest,
                notice_path=args.notices,
                wheel_path=args.wheel,
                runtime_python=args.runtime_python,
                output=args.output,
            )
        else:
            result = preflight(
                lock_path=args.lock,
                manifest_path=args.manifest,
                notice_path=args.notices,
                install_root=args.install_root,
                model_path=args.model,
                product_config_path=args.product_config,
                runtime_python=args.runtime_python,
                candidate_sha=args.candidate_sha,
                repo_root=args.repo,
            )
    except ProductFailure as error:
        print(json.dumps({"status": "Fail", "reason": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
