"""Pi-only offline build closure for the ACK-002 whisper.cpp recovery row.

The runner compiles and inspects the bounded persistent POC worker but never
loads a model or runs inference. It must run from a clean, network-disabled Pi
checkout after the controlled artifacts have passed the ACK-002 preflight.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m4a_whispercpp_preflight import (
    FALLBACK_ID,
    PRIMARY_ID,
    create_preflight_report,
    repo_root,
    resolve_controlled_path,
    sha256_file,
)


CMAKE_FLAGS = {
    "GGML_NATIVE": "OFF",
    "GGML_BLAS": "OFF",
    "GGML_CUDA": "OFF",
    "GGML_VULKAN": "OFF",
    "GGML_OPENCL": "OFF",
    "GGML_RPC": "OFF",
    "GGML_OPENMP": "OFF",
    "GGML_METAL": "OFF",
    "GGML_SYCL": "OFF",
    "GGML_KOMPUTE": "OFF",
    "GGML_CCACHE": "OFF",
    "WHISPER_CURL": "OFF",
    "WHISPER_BUILD_SERVER": "OFF",
    "WHISPER_COMMON_FFMPEG": "OFF",
    "WHISPER_SDL2": "OFF",
    "WHISPER_BUILD_TESTS": "OFF",
    "WHISPER_BUILD_EXAMPLES": "OFF",
    "WHISPER_USE_SYSTEM_GGML": "OFF",
    "WHISPER_COREML": "OFF",
    "WHISPER_OPENVINO": "OFF",
    "WHISPER_MKL": "OFF",
}
PROHIBITED_CACHE_TRUE = {
    "GGML_BLAS", "GGML_CUDA", "GGML_VULKAN", "GGML_OPENCL", "GGML_RPC", "GGML_OPENMP",
    "GGML_METAL", "GGML_SYCL", "GGML_KOMPUTE",
    "WHISPER_CURL", "WHISPER_BUILD_SERVER", "WHISPER_COMMON_FFMPEG",
    "WHISPER_FFMPEG", "WHISPER_SDL2", "WHISPER_BUILD_TESTS", "WHISPER_BUILD_EXAMPLES",
    "WHISPER_USE_SYSTEM_GGML", "WHISPER_COREML", "WHISPER_OPENVINO", "WHISPER_MKL",
}
PROHIBITED_DYNAMIC_NAMES = (
    "python", "openblas", "libblas", "cuda", "vulkan", "opencl", "libcurl",
    "libgomp", "libomp", "avcodec", "avformat", "avutil", "swresample", "sdl2",
    "libasound", "portaudio",
)
CALLER_NETNS_FD_ENV = "AUDIO_POC_CALLER_NETNS_FD"


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    return result.stdout.strip()


def assert_pi_target() -> dict[str, str]:
    machine = platform.machine()
    model_path = Path("/proc/device-tree/model")
    model = model_path.read_bytes().rstrip(b"\x00").decode("utf-8", errors="replace") \
        if model_path.is_file() else ""
    os_release = platform.freedesktop_os_release()
    if machine != "aarch64" or "Raspberry Pi 5" not in model:
        raise RuntimeError("build closure requires Raspberry Pi 5 on aarch64")
    if os_release.get("ID") != "debian" or os_release.get("VERSION_ID") != "13":
        raise RuntimeError("build closure requires Debian 13")
    return {
        "machine": machine,
        "hardware_model": model,
        "os_pretty_name": os_release.get("PRETTY_NAME", ""),
        "kernel": platform.release(),
    }


def validate_namespace_separation(
    current_target: str,
    current_inode: int,
    caller_target: str,
    caller_inode: int,
) -> None:
    if not current_target.startswith("net:[") or not caller_target.startswith("net:["):
        raise RuntimeError("offline execution requires network namespace file descriptors")
    if current_target == caller_target or current_inode == caller_inode:
        raise RuntimeError("offline execution requires an isolated network namespace")


def assert_network_isolated() -> None:
    current_namespace = Path("/proc/self/ns/net")
    caller_fd_text = os.environ.get(CALLER_NETNS_FD_ENV, "")
    if not caller_fd_text.isdecimal():
        raise RuntimeError("offline execution requires the caller network namespace handle")
    caller_fd = int(caller_fd_text)
    try:
        current_target = os.readlink(current_namespace)
        current_inode = current_namespace.stat().st_ino
        caller_target = os.readlink(f"/proc/self/fd/{caller_fd}")
        caller_inode = os.fstat(caller_fd).st_ino
    except (OSError, PermissionError) as error:
        raise RuntimeError(
            "offline execution cannot inspect the caller network namespace handle"
        ) from error
    validate_namespace_separation(
        current_target, current_inode, caller_target, caller_inode
    )
    route = Path("/proc/net/route")
    if route.is_file():
        for line in route.read_text(encoding="ascii").splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 2 and fields[0] != "lo" and fields[1] == "00000000":
                raise RuntimeError("offline build requires removal of the IPv4 default route")
    route6 = Path("/proc/net/ipv6_route")
    if route6.is_file():
        for line in route6.read_text(encoding="ascii").splitlines():
            fields = line.split()
            if len(fields) >= 10 and fields[0] == "0" * 32 and fields[1] == "00" and fields[-1] != "lo":
                raise RuntimeError("offline build requires removal of the IPv6 default route")
    network_root = Path("/sys/class/net")
    if network_root.is_dir():
        for interface in network_root.iterdir():
            if interface.name == "lo":
                continue
            operstate = interface / "operstate"
            if operstate.is_file() and operstate.read_text(encoding="ascii").strip() == "up":
                raise RuntimeError(
                    f"offline build requires disabling network interface: {interface.name}"
                )


def safe_extract_source(archive: Path, destination: Path) -> Path:
    if destination.exists():
        raise RuntimeError("source extraction directory must be new")
    destination.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            parts = Path(member.name).parts
            if not parts or member.name.startswith("/") or ".." in parts:
                raise RuntimeError("source archive contains an unsafe path")
            if not (member.isfile() or member.isdir()):
                raise RuntimeError("source archive contains a non-file entry")
        bundle.extractall(destination, filter="data")
    roots = {Path(member.name).parts[0] for member in members if Path(member.name).parts}
    source_dir = destination
    if not (source_dir / "CMakeLists.txt").is_file() and len(roots) == 1:
        source_dir = destination / next(iter(roots))
    if not (source_dir / "CMakeLists.txt").is_file() or not (source_dir / "LICENSE").is_file():
        raise RuntimeError("source archive lacks CMakeLists.txt or LICENSE")
    return source_dir


def configure_command(wrapper_source_dir: Path, source_dir: Path, build_dir: Path) -> list[str]:
    command = ["cmake", "-S", str(wrapper_source_dir), "-B", str(build_dir),
               f"-DWHISPER_SOURCE_DIR={source_dir}", "-DCMAKE_BUILD_TYPE=Release",
               "-DBUILD_SHARED_LIBS=OFF"]
    command.extend(f"-D{name}={value}" for name, value in CMAKE_FLAGS.items())
    return command


def parse_cmake_cache(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith(("#", "//")) or "=" not in line:
            continue
        key_type, value = line.split("=", 1)
        key = key_type.split(":", 1)[0]
        values[key] = value
    return values


def validate_cmake_cache(values: dict[str, str]) -> None:
    for name, expected in CMAKE_FLAGS.items():
        if values.get(name) != expected:
            raise RuntimeError(f"CMake cache does not preserve {name}={expected}")
    for name in PROHIBITED_CACHE_TRUE:
        if values.get(name, "OFF").upper() in {"1", "ON", "TRUE", "YES", "Y"}:
            raise RuntimeError(f"CMake cache enables prohibited feature: {name}")


def validate_dynamic_dependencies(listing: str) -> None:
    lowered = listing.lower()
    for name in PROHIBITED_DYNAMIC_NAMES:
        if name in lowered:
            raise RuntimeError(f"binary links a prohibited runtime dependency: {name}")


def build_report(
    manifest: dict[str, Any], artifact_dir: Path, work_dir: Path, source_sha: str,
    candidate_id: str, q8_result: dict[str, Any] | None,
) -> dict[str, Any]:
    platform_report = assert_pi_target()
    assert_network_isolated()
    if work_dir.resolve().is_relative_to(repo_root().resolve()):
        raise RuntimeError("build work directory must remain outside the POC repository")
    if work_dir.exists():
        raise RuntimeError("build work directory must be new")
    if shutil.which("cmake") is None or shutil.which("c++") is None or shutil.which("ldd") is None:
        raise RuntimeError("cmake, C++ compiler and ldd are required")

    artifact_report = create_preflight_report(
        manifest, candidate_id, artifact_dir, source_sha, q8_result
    )
    source = manifest["engine_source"]
    source_archive = resolve_controlled_path(
        manifest, source["controlled_locator"], source["filename"], artifact_dir
    )
    source_dir = safe_extract_source(source_archive, work_dir / "source")
    build_dir = work_dir / "build"
    wrapper_source_dir = repo_root() / "poc_audio/native/whispercpp_worker"
    configure = configure_command(wrapper_source_dir, source_dir, build_dir)
    build = ["cmake", "--build", str(build_dir), "--target", "m4a-whispercpp-worker", "-j", "4"]
    subprocess.run(configure, check=True, env={**os.environ, "CMAKE_DISABLE_FIND_PACKAGE_CURL": "TRUE"})
    subprocess.run(build, check=True)
    assert_network_isolated()

    cache = parse_cmake_cache(build_dir / "CMakeCache.txt")
    validate_cmake_cache(cache)
    binary = build_dir / "bin/m4a-whispercpp-worker"
    if not binary.is_file():
        raise RuntimeError("persistent whisper.cpp worker is missing after build")
    dynamic_listing = command_output(["ldd", str(binary)])
    validate_dynamic_dependencies(dynamic_listing)
    return {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-ASR-RECOVERY-OFFLINE-BUILD",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": source_sha,
        "candidate_id": candidate_id,
        "artifact_preflight": artifact_report,
        "platform": platform_report,
        "toolchain": {
            "cmake": command_output(["cmake", "--version"]),
            "cxx": command_output(["c++", "--version"]),
        },
        "commands": {"configure": configure, "build": build},
        "wrapper_source": [
            {
                "relative_path": "poc_audio/native/whispercpp_worker/CMakeLists.txt",
                "sha256": sha256_file(wrapper_source_dir / "CMakeLists.txt"),
            },
            {
                "relative_path": "poc_audio/native/whispercpp_worker/worker.cpp",
                "sha256": sha256_file(wrapper_source_dir / "worker.cpp"),
            },
        ],
        "cmake_cache": {name: cache[name] for name in CMAKE_FLAGS},
        "binary": {
            "relative_path": binary.relative_to(work_dir).as_posix(),
            "size_bytes": binary.stat().st_size,
            "sha256": sha256_file(binary),
            "dynamic_dependencies": dynamic_listing.splitlines(),
        },
        "network_evidence": "ISOLATED_NETWORK_NAMESPACE_NO_ROUTE_OR_ACTIVE_INTERFACE_BEFORE_AND_AFTER_BUILD",
        "execution_status": "BUILD_PASS_MODEL_NOT_LOADED_INFERENCE_NOT_RUN",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", choices=(PRIMARY_ID, FALLBACK_ID), default=PRIMARY_ID)
    parser.add_argument("--q8-result", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError("output must be a new path")
    manifest = json.loads(
        (repo_root() / "poc_audio/manifests/m4a_asr_recovery_ack002.json").read_text(
            encoding="utf-8"
        )
    )
    q8_result = json.loads(args.q8_result.read_text(encoding="utf-8")) \
        if args.q8_result is not None else None
    report = build_report(
        manifest, args.artifact_dir, args.work_dir, args.source_sha,
        args.candidate, q8_result,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ACK-002 offline build closure passed; model not loaded: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
