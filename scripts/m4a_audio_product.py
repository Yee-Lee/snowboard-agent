#!/usr/bin/env python3
"""Build, install, and preflight the checksum-locked M4a Audio product."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sbd.adaptor.audio_lock import (  # noqa: E402
    ACCEPTED_AUDIO_SHA,
    WHISPER_CMAKE_OPTIONS,
    WHISPER_SOURCE_SHA256,
    AudioArtifactLock,
    AudioLockError,
)
from sbd.core.config import load_config  # noqa: E402


GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_SCHEMA = "sbd.m4a.runtime-lock.v1"
BUILD_SCHEMA = "sbd.m4a.whispercpp-build.v2"
BUILD_RESULT_SCHEMA = "sbd.m4a.whispercpp-build-result.v2"
MATCHA_CLOSURE_SCHEMA = "sbd.m4a.matcha-closure.v1"
INSTALL_SCHEMA = "sbd.m4a.product-install.v4"
PROTECTED_PATHS = ("src", "tests", "scripts", "native", "requirements", "config.example.yaml", "pyproject.toml")
VAD_NAMES = ("vad-onnxruntime", "vad-flatbuffers", "runtime-numpy", "vad-packaging", "vad-protobuf")
TTS_NAMES = ("tts-sherpa-onnx", "tts-sherpa-onnx-core", "runtime-numpy")
INSTALL_ARTIFACT_NAMES = ("silero-model", "whisper-model", "matcha-archive", "vocos-model")
MATCHA_REQUIRED_FILES = {
    "date-zh.fst", "number-zh.fst", "phone-zh.fst", "tokens.txt",
    "lexicon.txt", "model-steps-3.onnx", "espeak-ng-data/intonations",
    "espeak-ng-data/phondata", "espeak-ng-data/phondata-manifest",
    "espeak-ng-data/phonindex", "espeak-ng-data/phontab",
}
MATCHA_TREE_SHA256 = "5e4f8625f9f7d62f9a410d33571ebcd1e3e5b8b0f43f1ebda23512a79e2f3319"


class ProductFailure(RuntimeError):
    """Sanitized fail-closed product preparation error."""


@dataclass(frozen=True, slots=True)
class RuntimeLock:
    runtime: str
    interpreter: str
    arch: str
    profile: str
    baseline_source_sha: str
    wheels: tuple[dict[str, Any], ...]


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProductFailure(f"{label} is unreadable or invalid") from error
    if not isinstance(value, dict):
        raise ProductFailure(f"{label} must be an object")
    return value


def _exact(value: dict[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ProductFailure(f"{label} has missing or extra fields")


def _sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ProductFailure("controlled artifact is missing or unsafe")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_runtime(path: Path, expected_runtime: str, product: AudioArtifactLock) -> RuntimeLock:
    value = _json(path, f"{expected_runtime} runtime lock")
    _exact(value, {"schema", "runtime", "interpreter", "arch", "profile", "baseline_source_sha", "wheels"}, f"{expected_runtime} runtime lock")
    expected_profile = "silero-6.2.1-endpoint-v1" if expected_runtime == "vad" else "matcha-zh-en-default-sid-0"
    expected_source_sha = (
        "7e30209a3e901f9842f81b225f3e93d8199902b1"
        if expected_runtime == "vad"
        else "3dc7c569f31ca2cd4a20ed6f7db780327e6714c5"
    )
    if (
        value["schema"] != RUNTIME_SCHEMA
        or value["runtime"] != expected_runtime
        or value["interpreter"] != "CPython 3.13"
        or value["arch"] != "aarch64"
        or value["profile"] != expected_profile
        or value["baseline_source_sha"] != expected_source_sha
    ):
        raise ProductFailure(f"{expected_runtime} runtime identity mismatch")
    wheels = value["wheels"]
    if not isinstance(wheels, list) or not wheels:
        raise ProductFailure(f"{expected_runtime} wheels must be non-empty")
    expected_names = VAD_NAMES if expected_runtime == "vad" else TTS_NAMES
    expected_rows = [product.require(name) for name in expected_names]
    if len(wheels) != len(expected_rows):
        raise ProductFailure(f"{expected_runtime} wheel inventory mismatch")
    seen = set()
    for row, artifact in zip(wheels, expected_rows, strict=True):
        if not isinstance(row, dict):
            raise ProductFailure(f"{expected_runtime} wheel row is invalid")
        _exact(row, {"distribution", "version", "filename", "size_bytes", "sha256"}, f"{expected_runtime} wheel row")
        expected_distribution = artifact.name.removeprefix("vad-").removeprefix("tts-").replace("runtime-numpy", "numpy")
        if artifact.name == "runtime-numpy":
            expected_distribution = "numpy"
        if row != {
            "distribution": expected_distribution,
            "version": artifact.version,
            "filename": artifact.filename,
            "size_bytes": artifact.size_bytes,
            "sha256": artifact.sha256,
        }:
            raise ProductFailure(f"{expected_runtime} wheel identity mismatch")
        if row["distribution"] in seen:
            raise ProductFailure(f"{expected_runtime} wheel distribution is duplicated")
        seen.add(row["distribution"])
    return RuntimeLock(
        runtime=value["runtime"], interpreter=value["interpreter"], arch=value["arch"],
        profile=value["profile"], baseline_source_sha=value["baseline_source_sha"],
        wheels=tuple(wheels),
    )


def _assert_offline() -> None:
    devices = Path("/proc/net/dev")
    if not devices.is_file():
        raise ProductFailure("offline network state cannot be inspected")
    interfaces = []
    for line in devices.read_text(encoding="ascii").splitlines()[2:]:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name and name != "lo":
                interfaces.append(name)
    if interfaces:
        raise ProductFailure("network namespace contains a non-loopback interface")
    route = Path("/proc/net/route")
    if route.is_file() and any(
        len(fields := line.split()) >= 2 and fields[0] != "lo" and fields[1] == "00000000"
        for line in route.read_text(encoding="ascii").splitlines()[1:]
    ):
        raise ProductFailure("network namespace contains a default route")


def _safe_extract(archive: Path, destination: Path, mode: str) -> Path:
    if destination.exists():
        raise ProductFailure("extraction destination must be new")
    destination.mkdir(parents=True, mode=0o700)
    try:
        with tarfile.open(archive, mode) as bundle:
            members = bundle.getmembers()
            for member in members:
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                    raise ProductFailure("archive contains an unsafe path or entry")
            bundle.extractall(destination, members=members)
    except (tarfile.TarError, OSError) as error:
        raise ProductFailure("archive extraction failed") from error
    roots = {Path(member.name).parts[0] for member in members if Path(member.name).parts}
    return destination / next(iter(roots)) if len(roots) == 1 else destination


def _load_matcha_closure(lock_root: Path, product: AudioArtifactLock) -> dict[str, Any]:
    value = _json(lock_root / "matcha-closure.json", "Matcha closure lock")
    _exact(
        value,
        {"schema", "archive_sha256", "root_dir", "file_count", "tree_sha256", "required_files"},
        "Matcha closure lock",
    )
    if (
        value["schema"] != MATCHA_CLOSURE_SCHEMA
        or value["archive_sha256"] != product.require("matcha-archive").sha256
        or value["root_dir"] != "matcha-icefall-zh-en"
        or value["file_count"] != 362
        or value["tree_sha256"] != MATCHA_TREE_SHA256
    ):
        raise ProductFailure("Matcha closure identity mismatch")
    required = value["required_files"]
    if not isinstance(required, dict) or set(required) != MATCHA_REQUIRED_FILES:
        raise ProductFailure("Matcha required component inventory mismatch")
    for path, row in required.items():
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts or not isinstance(row, dict):
            raise ProductFailure("Matcha required component row is unsafe")
        _exact(row, {"size_bytes", "sha256"}, "Matcha required component row")
        if (
            type(row["size_bytes"]) is not int
            or row["size_bytes"] <= 0
            or not SHA256_RE.fullmatch(str(row["sha256"]))
        ):
            raise ProductFailure("Matcha required component identity is invalid")
    model = product.require("matcha-model")
    if required["model-steps-3.onnx"] != {
        "size_bytes": model.size_bytes,
        "sha256": model.sha256,
    }:
        raise ProductFailure("Matcha acoustic model differs from product lock")
    return value


def _load_notice_bundle(lock_root: Path, product: AudioArtifactLock) -> str:
    path = lock_root / "THIRD_PARTY_NOTICES.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ProductFailure("third-party notice inventory is unreadable") from error
    headings = {
        re.sub(r"[^a-z0-9 -]", "", line[3:].strip().lower()).replace(" ", "-")
        for line in text.splitlines()
        if line.startswith("## ")
    }
    references = {
        item.notice_ref.partition("#")[2]
        for item in product.artifacts
    }
    required_terms = {
        "onnx runtime", "numpy", "flatbuffers", "packaging", "protobuf",
        "whisper.cpp", "openai whisper", "sherpa-onnx-core", "matcha-tts",
        "vocos", "espeak ng", "gpl-3.0-or-later", "unicode data license",
        "date-zh.fst", "number-zh.fst", "phone-zh.fst", "lexicon.txt",
        "tokens.txt", "accepted risk",
    }
    lowered = text.lower()
    if not references <= headings or any(term not in lowered for term in required_terms):
        raise ProductFailure("third-party notice inventory is incomplete")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _matcha_tree_identity(root: Path) -> tuple[int, str, dict[str, dict[str, Any]]]:
    if not root.is_dir() or root.is_symlink():
        raise ProductFailure("Matcha model root is absent or unsafe")
    rows: list[dict[str, Any]] = []
    by_path: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ProductFailure("Matcha model tree contains an unsafe entry")
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        row = {
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        rows.append(row)
        by_path[relative] = {"size_bytes": row["size_bytes"], "sha256": row["sha256"]}
    digest = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return len(rows), digest, by_path


def _verify_matcha_tree(root: Path, closure: dict[str, Any]) -> str:
    if root.name != closure["root_dir"]:
        raise ProductFailure("Matcha archive root identity mismatch")
    count, digest, files = _matcha_tree_identity(root)
    if count != closure["file_count"] or digest != closure["tree_sha256"]:
        raise ProductFailure("Matcha extracted tree identity mismatch")
    if any(files.get(path) != expected for path, expected in closure["required_files"].items()):
        raise ProductFailure("Matcha required component checksum mismatch")
    return digest


def _load_build_lock(lock_root: Path) -> dict[str, Any]:
    value = _json(lock_root / "whispercpp-build.json", "whisper build lock")
    keys = {"schema", "engine", "version", "source_commit", "source_filename", "source_size_bytes", "source_sha256", "cmake_options", "wrapper_sources", "target_binary", "baseline_binary_sha256"}
    _exact(value, keys, "whisper build lock")
    if value["schema"] != BUILD_SCHEMA or value["engine"] != "whisper.cpp" or value["version"] != "1.9.2":
        raise ProductFailure("whisper build identity mismatch")
    if (
        value["source_commit"] != "306c88f4d1286aec1bf96e544632897886af5501"
        or value["source_filename"] != "whisper.cpp-v1.9.2.tar.gz"
        or value["source_size_bytes"] != 9613762
        or value["source_sha256"] != WHISPER_SOURCE_SHA256
        or value["target_binary"] != "whispercpp-worker"
        or value["baseline_binary_sha256"] != "64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b"
    ):
        raise ProductFailure("whisper source identity mismatch")
    options = value["cmake_options"]
    if not isinstance(options, list) or not options or len(options) != len(set(options)):
        raise ProductFailure("whisper build options are invalid")
    if options != list(WHISPER_CMAKE_OPTIONS):
        raise ProductFailure("whisper build options differ from the Accepted profile")
    prohibited = ("CUDA=ON", "BLAS=ON", "METAL=ON", "VULKAN=ON", "CURL=ON", "SERVER=ON")
    if any(any(token in option.upper() for token in prohibited) for option in options):
        raise ProductFailure("whisper build enables a prohibited backend")
    expected_sources = [
        {"path": "native/m4a_whispercpp_worker/CMakeLists.txt", "sha256": "a1da74fa0f0a2f8cf94ea178c122b81eea6a4ee50275e9d8445710b19157c1a8"},
        {"path": "native/m4a_whispercpp_worker/worker.cpp", "sha256": "d3d0db1724b5882a358a6f6ae6edd08bc71d7ce9b0ce4b43781e72c8688a51dd"},
    ]
    if value["wrapper_sources"] != expected_sources:
        raise ProductFailure("whisper wrapper source identity mismatch")
    return value


def _wrapper_sources_sha256(build_lock: dict[str, Any]) -> str:
    for row in build_lock["wrapper_sources"]:
        source = REPO_ROOT / row["path"]
        if _sha256(source) != row["sha256"]:
            raise ProductFailure("tracked whisper wrapper differs from Accepted POC source")
    return hashlib.sha256(
        json.dumps(build_lock["wrapper_sources"], separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


def build_whisper(args: argparse.Namespace) -> dict[str, Any]:
    _assert_offline()
    lock_root = args.lock_root.resolve()
    product = AudioArtifactLock.load(lock_root / "audio-artifacts.json")
    build_lock = _load_build_lock(lock_root)
    source = args.source_archive.resolve()
    product.require("whisper-source").verify(source)
    if source.name != build_lock["source_filename"] or _sha256(source) != build_lock["source_sha256"]:
        raise ProductFailure("whisper source does not match build lock")
    build_root = args.build_root.resolve()
    output = args.output.resolve()
    result_path = output.with_suffix(output.suffix + ".json")
    if build_root.exists() or output.exists() or result_path.exists():
        raise ProductFailure("build root, output, and build result must be new")
    try:
        source_root = _safe_extract(source, build_root / "source", "r:gz")
        if not (source_root / "CMakeLists.txt").is_file() or not (source_root / "LICENSE").is_file():
            raise ProductFailure("whisper source archive lacks required build/license files")
        wrapper = REPO_ROOT / "native" / "m4a_whispercpp_worker"
        if not (wrapper / "CMakeLists.txt").is_file() or not (wrapper / "worker.cpp").is_file():
            raise ProductFailure("tracked persistent worker source is absent")
        wrapper_sources_sha256 = _wrapper_sources_sha256(build_lock)
        cmake_root = build_root / "build"
        configure = [
            "cmake", "-S", str(wrapper), "-B", str(cmake_root),
            f"-DWHISPER_SOURCE_DIR={source_root}", "-DCMAKE_BUILD_TYPE=Release",
            *build_lock["cmake_options"],
        ]
        environment = _offline_environment()
        subprocess.run(
            configure, check=True, env=environment,
            text=True, capture_output=True,
        )
        subprocess.run(
            ["cmake", "--build", str(cmake_root), "--target", "m4a-whispercpp-worker", "-j", "4"],
            check=True, env=environment, text=True, capture_output=True,
        )
        built = cmake_root / "bin" / "m4a-whispercpp-worker"
        if not built.is_file():
            raise ProductFailure("persistent whisper worker was not produced")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, output)
        output.chmod(0o755)
        result = {
            "schema": BUILD_RESULT_SCHEMA,
            "source_sha256": build_lock["source_sha256"],
            "cmake_options_sha256": hashlib.sha256(json.dumps(build_lock["cmake_options"], separators=(",", ":")).encode()).hexdigest(),
            "wrapper_sources_sha256": wrapper_sources_sha256,
            "binary_filename": output.name,
            "binary_size_bytes": output.stat().st_size,
            "binary_sha256": _sha256(output),
        }
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except BaseException:
        if build_root.exists():
            shutil.rmtree(build_root)
        output.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)
        raise
    return {"status": "Pass", "operation": "build-whisper", "binary_sha256": result["binary_sha256"], "binary_size_bytes": result["binary_size_bytes"]}


def _offline_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update({
        "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CONFIG_FILE": os.devnull, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
    })
    for name in tuple(environment):
        if name.lower().endswith("_proxy"):
            environment.pop(name, None)
    return environment


def _verify_flat_inputs(root: Path, product: AudioArtifactLock, names: tuple[str, ...]) -> None:
    if not root.is_dir() or root.is_symlink():
        raise ProductFailure("controlled input root is absent or unsafe")
    expected = {product.require(name).filename for name in names} | {"m4a-whispercpp-worker", "m4a-whispercpp-worker.json"}
    actual = {path.name for path in root.iterdir()}
    if actual != expected or any(not path.is_file() or path.is_symlink() for path in root.iterdir()):
        raise ProductFailure("controlled input inventory has missing, extra, or unsafe entries")
    for name in names:
        product.require(name).verify(root / product.require(name).filename)
    result = _json(root / "m4a-whispercpp-worker.json", "whisper build result")
    _exact(result, {"schema", "source_sha256", "cmake_options_sha256", "wrapper_sources_sha256", "binary_filename", "binary_size_bytes", "binary_sha256"}, "whisper build result")
    build_lock = _load_build_lock(product.path.parent)
    options_sha = hashlib.sha256(json.dumps(build_lock["cmake_options"], separators=(",", ":")).encode()).hexdigest()
    binary = root / "m4a-whispercpp-worker"
    if (
        result["schema"] != BUILD_RESULT_SCHEMA
        or result["source_sha256"] != build_lock["source_sha256"]
        or result["cmake_options_sha256"] != options_sha
        or result["wrapper_sources_sha256"] != _wrapper_sources_sha256(build_lock)
        or result["binary_filename"] != binary.name
        or result["binary_size_bytes"] != binary.stat().st_size
        or result["binary_sha256"] != _sha256(binary)
    ):
        raise ProductFailure("whisper build result or binary mismatch")


def _install_venv(python: Path, destination: Path, wheels: list[Path], environment: dict[str, str]) -> None:
    subprocess.run(
        [str(python), "-m", "venv", "--copies", str(destination)],
        check=True, env=environment, text=True, capture_output=True,
    )
    cfg = destination / "pyvenv.cfg"
    if "include-system-site-packages = false" not in cfg.read_text(encoding="utf-8").lower():
        raise ProductFailure("created runtime permits system-site packages")
    runtime_python = destination / "bin" / "python"
    subprocess.run(
        [str(runtime_python), "-m", "pip", "install", "--no-index", "--no-deps", *(str(path) for path in wheels)],
        check=True, env=environment, text=True, capture_output=True,
    )


def _target_python_identity(python: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(
        [str(python), "-c", "import json,platform,sys;print(json.dumps({'implementation':platform.python_implementation(),'minor':f'{sys.version_info.major}.{sys.version_info.minor}','machine':platform.machine()}))"],
        text=True, capture_output=True, check=False, env=environment,
    )
    try:
        identity = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProductFailure("target interpreter identity cannot be inspected") from error
    if completed.returncode or identity != {
        "implementation": "CPython", "minor": "3.13", "machine": "aarch64",
    }:
        raise ProductFailure("target interpreter must be CPython 3.13 on aarch64")


def _verify_installed_runtime(
    python: Path,
    runtime: RuntimeLock,
    environment: dict[str, str],
) -> None:
    _target_python_identity(python, environment)
    completed = subprocess.run(
        [str(python), "-m", "pip", "list", "--format=json", "--disable-pip-version-check"],
        text=True, capture_output=True, check=False, env=environment,
    )
    try:
        rows = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProductFailure("installed runtime inventory cannot be inspected") from error
    if completed.returncode or not isinstance(rows, list):
        raise ProductFailure("installed runtime inventory is invalid")
    actual = {
        str(row.get("name", "")).lower().replace("_", "-"): str(row.get("version", ""))
        for row in rows if isinstance(row, dict)
    }
    expected = {
        str(row["distribution"]).lower().replace("_", "-"): str(row["version"])
        for row in runtime.wheels
    }
    extras = set(actual) - set(expected) - {"pip"}
    if extras or set(expected) - set(actual) or any(actual.get(name) != version for name, version in expected.items()):
        raise ProductFailure("installed runtime distribution inventory mismatch")


def install(args: argparse.Namespace) -> dict[str, Any]:
    _assert_offline()
    lock_root = args.lock_root.resolve()
    product = AudioArtifactLock.load(lock_root / "audio-artifacts.json")
    vad = _load_runtime(lock_root / "vad-rpi-cp313.json", "vad", product)
    tts = _load_runtime(lock_root / "tts-rpi-cp313.json", "tts", product)
    matcha_closure = _load_matcha_closure(lock_root, product)
    notice_sha256 = _load_notice_bundle(lock_root, product)
    input_root = args.input_root.resolve()
    names = tuple(dict.fromkeys((*VAD_NAMES, *TTS_NAMES, *INSTALL_ARTIFACT_NAMES)))
    _verify_flat_inputs(input_root, product, names)
    install_root = args.install_root.resolve()
    if install_root.exists():
        raise ProductFailure("install root must be new")
    install_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{install_root.name}.staging-", dir=install_root.parent))
    environment = _offline_environment()
    try:
        _target_python_identity(args.python.resolve(), environment)
        vad_wheels = [input_root / row["filename"] for row in vad.wheels]
        tts_wheels = [input_root / row["filename"] for row in tts.wheels]
        _install_venv(args.python.resolve(), staging / "vad", vad_wheels, environment)
        _install_venv(args.python.resolve(), staging / "tts", tts_wheels, environment)
        _verify_installed_runtime(staging / "vad" / "bin" / "python", vad, environment)
        _verify_installed_runtime(staging / "tts" / "bin" / "python", tts, environment)
        artifacts = staging / "artifacts"
        artifacts.mkdir(mode=0o700)
        for name in ("silero-model", "whisper-model", "vocos-model"):
            item = product.require(name)
            shutil.copy2(input_root / item.filename, artifacts / item.filename)
        shutil.copy2(input_root / "m4a-whispercpp-worker", artifacts / "m4a-whispercpp-worker")
        shutil.copy2(
            input_root / "m4a-whispercpp-worker.json",
            artifacts / "m4a-whispercpp-worker.json",
        )
        (artifacts / "m4a-whispercpp-worker").chmod(0o755)
        model_root = _safe_extract(input_root / product.require("matcha-archive").filename, artifacts / "matcha", "r:bz2")
        product.require("matcha-model").verify(model_root / "model-steps-3.onnx")
        matcha_tree_sha256 = _verify_matcha_tree(model_root, matcha_closure)
        notices = staging / "notices"
        notices.mkdir(mode=0o700)
        shutil.copy2(
            lock_root / "THIRD_PARTY_NOTICES.md",
            notices / "THIRD_PARTY_NOTICES.md",
        )
        inventory = {
            "schema": INSTALL_SCHEMA,
            "accepted_audio_sha": ACCEPTED_AUDIO_SHA,
            "product_lock_sha256": product.digest,
            "vad_distributions": {row["distribution"]: row["version"] for row in vad.wheels},
            "tts_distributions": {row["distribution"]: row["version"] for row in tts.wheels},
            "whisper_binary_sha256": _sha256(artifacts / "m4a-whispercpp-worker"),
            "artifact_sha256": {path.name: _sha256(path) for path in artifacts.iterdir() if path.is_file()},
            "matcha_model_sha256": _sha256(model_root / "model-steps-3.onnx"),
            "matcha_model_root": str(model_root.relative_to(staging)),
            "matcha_tree_sha256": matcha_tree_sha256,
            "notice_sha256": notice_sha256,
        }
        (staging / "install-manifest.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staging.replace(install_root)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {"status": "Pass", "operation": "install", "wheel_count": len(vad.wheels) + len(tts.wheels), "product_lock_sha256": product.digest}


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)
    if completed.returncode:
        raise ProductFailure("Core checkout identity cannot be inspected")
    return completed.stdout.strip()


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    _assert_offline()
    lock_root = args.lock_root.resolve()
    product = AudioArtifactLock.load(lock_root / "audio-artifacts.json")
    _load_runtime(lock_root / "vad-rpi-cp313.json", "vad", product)
    _load_runtime(lock_root / "tts-rpi-cp313.json", "tts", product)
    matcha_closure = _load_matcha_closure(lock_root, product)
    notice_sha256 = _load_notice_bundle(lock_root, product)
    if not GIT_SHA_RE.fullmatch(args.core_sha):
        raise ProductFailure("candidate SHA must be 40 lowercase hexadecimal characters")
    core_repo = args.core_repo.resolve()
    if _git(core_repo, "rev-parse", "HEAD") != args.core_sha:
        raise ProductFailure("Core checkout does not match candidate SHA")
    dirty = _git(core_repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *PROTECTED_PATHS)
    if dirty:
        raise ProductFailure("Core protected candidate input is dirty")
    install_root = args.install_root.resolve()
    manifest = _json(install_root / "install-manifest.json", "product install manifest")
    _exact(manifest, {"schema", "accepted_audio_sha", "product_lock_sha256", "vad_distributions", "tts_distributions", "whisper_binary_sha256", "artifact_sha256", "matcha_model_sha256", "matcha_model_root", "matcha_tree_sha256", "notice_sha256"}, "product install manifest")
    if manifest["schema"] != INSTALL_SCHEMA or manifest["accepted_audio_sha"] != ACCEPTED_AUDIO_SHA or manifest["product_lock_sha256"] != product.digest:
        raise ProductFailure("installed product identity mismatch")
    config = load_config(local_path=args.config.resolve(), dotenv_path=Path(os.devnull), environ={})
    asr = config.perception.listen.adapter
    tts = config.action.tts
    if asr.driver != "whispercpp" or tts.driver != "sherpa_matcha":
        raise ProductFailure("product config does not select both real Audio drivers")
    expected_paths = {
        "ASR runtime": (asr.runtime_python, install_root / "vad" / "bin" / "python"),
        "TTS runtime": (tts.runtime_python, install_root / "tts" / "bin" / "python"),
        "ASR worker": (asr.worker_path, install_root / "artifacts" / "m4a-whispercpp-worker"),
        "ASR model": (asr.model_path, install_root / "artifacts" / product.require("whisper-model").filename),
        "VAD model": (asr.vad_model_path, install_root / "artifacts" / product.require("silero-model").filename),
        "TTS model": (tts.model_path, install_root / manifest["matcha_model_root"]),
        "TTS vocoder": (tts.vocoder_path, install_root / "artifacts" / product.require("vocos-model").filename),
    }
    if any(actual != expected.resolve() for actual, expected in expected_paths.values()):
        raise ProductFailure("product config path does not map to the immutable install")
    product.verify_asr_config(asr)
    product.verify_tts_config(tts)
    environment = _offline_environment()
    _verify_installed_runtime(asr.runtime_python, _load_runtime(lock_root / "vad-rpi-cp313.json", "vad", product), environment)
    _verify_installed_runtime(tts.runtime_python, _load_runtime(lock_root / "tts-rpi-cp313.json", "tts", product), environment)
    artifact_files = {
        path.name: _sha256(path)
        for path in (install_root / "artifacts").iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if artifact_files != manifest["artifact_sha256"]:
        raise ProductFailure("installed artifact inventory or checksum mismatch")
    if _sha256(tts.model_path / "model-steps-3.onnx") != manifest["matcha_model_sha256"]:
        raise ProductFailure("installed Matcha model checksum mismatch")
    if (
        manifest["matcha_tree_sha256"] != matcha_closure["tree_sha256"]
        or _verify_matcha_tree(tts.model_path, matcha_closure) != manifest["matcha_tree_sha256"]
    ):
        raise ProductFailure("installed Matcha closure mismatch")
    installed_notice = install_root / "notices" / "THIRD_PARTY_NOTICES.md"
    if (
        manifest["notice_sha256"] != notice_sha256
        or _sha256(installed_notice) != notice_sha256
    ):
        raise ProductFailure("installed third-party notice inventory mismatch")
    return {
        "status": "Pass", "operation": "preflight", "candidate_sha": args.core_sha,
        "accepted_audio_sha": ACCEPTED_AUDIO_SHA, "product_lock_sha256": product.digest,
        "config_sha256": _sha256(args.config.resolve()), "wheel_count": len(manifest["vad_distributions"]) + len(manifest["tts_distributions"]),
        "install_schema": manifest["schema"],
        "whisper_binary_sha256": manifest["whisper_binary_sha256"],
        "matcha_tree_sha256": manifest["matcha_tree_sha256"],
        "notice_sha256": manifest["notice_sha256"],
        "network_attempt_count": 0,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    build = sub.add_parser("build-whisper")
    build.add_argument("--lock-root", type=Path, required=True)
    build.add_argument("--source-archive", type=Path, required=True)
    build.add_argument("--build-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--lock-root", type=Path, required=True)
    install_parser.add_argument("--input-root", type=Path, required=True)
    install_parser.add_argument("--install-root", type=Path, required=True)
    install_parser.add_argument("--python", type=Path, required=True)
    preflight_parser = sub.add_parser("preflight")
    preflight_parser.add_argument("--lock-root", type=Path, required=True)
    preflight_parser.add_argument("--install-root", type=Path, required=True)
    preflight_parser.add_argument("--core-repo", type=Path, required=True)
    preflight_parser.add_argument("--core-sha", required=True)
    preflight_parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = {"build-whisper": build_whisper, "install": install, "preflight": preflight}[args.operation](args)
    except (AudioLockError, ProductFailure, OSError, subprocess.SubprocessError) as error:
        failure = {"status": "Fail", "operation": args.operation, "error_code": type(error).__name__}
        print(json.dumps(failure, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
