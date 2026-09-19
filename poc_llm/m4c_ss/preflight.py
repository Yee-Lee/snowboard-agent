"""Fail-closed read-only target identity checks for the future authorized Pi run."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
from typing import Any


class TargetPreflightError(RuntimeError):
    pass


def require_target_platform() -> dict[str, Any]:
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        raise TargetPreflightError("TARGET_PLATFORM_MISMATCH")
    model_path = Path("/proc/device-tree/model")
    if not model_path.is_file() or "Raspberry Pi 5" not in model_path.read_text().strip("\0\n"):
        raise TargetPreflightError("TARGET_BOARD_MISMATCH")
    os_release = platform.freedesktop_os_release()
    if os_release.get("ID") != "debian" or os_release.get("VERSION_ID") != "13":
        raise TargetPreflightError("TARGET_OS_MISMATCH")
    if platform.python_version() != "3.13.5":
        raise TargetPreflightError("TARGET_PYTHON_MISMATCH")
    return {
        "board": "Raspberry Pi 5",
        "os": "Debian 13",
        "architecture": "aarch64",
        "python": "3.13.5",
    }


def require_network_offline(sys_class_net: Path = Path("/sys/class/net")) -> None:
    for interface in sys_class_net.iterdir():
        if interface.name == "lo":
            continue
        if (interface / "operstate").read_text().strip() == "up":
            raise TargetPreflightError("NETWORK_NOT_OFFLINE")


def require_clean_checkout(root: Path, expected_sha: str) -> None:
    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), *arguments], text=True,
        ).strip()

    if git("rev-parse", "HEAD") != expected_sha or git("status", "--porcelain"):
        raise TargetPreflightError("CHECKOUT_IDENTITY_DRIFT")


def verify_artifact(path: Path, expected_sha256: str, expected_bytes: int | None = None) -> dict[str, Any]:
    if not path.is_absolute():
        raise TargetPreflightError("ARTIFACT_PATH_INVALID")
    # ``Path.resolve()`` erases the evidence that an input was a symlink.  Walk
    # the supplied path first so a receipt cannot redirect a verified artifact
    # through either a symlinked file or directory.
    current = Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current /= part
            if stat.S_ISLNK(current.lstat().st_mode):
                raise TargetPreflightError("ARTIFACT_PATH_INVALID")
    except FileNotFoundError:
        raise TargetPreflightError("ARTIFACT_MISSING")
    resolved = path.resolve()
    descriptor: int | None = None
    digest = hashlib.sha256()
    try:
        descriptor = os.open(
            resolved,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise TargetPreflightError("ARTIFACT_MISSING")
        size = metadata.st_size
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    except OSError:
        raise TargetPreflightError("ARTIFACT_MISSING") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if expected_bytes is not None and size != expected_bytes:
        raise TargetPreflightError("ARTIFACT_SIZE_MISMATCH")
    if digest.hexdigest() != expected_sha256:
        raise TargetPreflightError("ARTIFACT_DIGEST_MISMATCH")
    return {"bytes": size, "sha256": expected_sha256}


def verify_private_receipt(receipt_path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    try:
        receipt = json.loads(receipt_path.read_text())
        artifacts = receipt["artifacts"]
        microphone = receipt["measurement_microphone"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise TargetPreflightError("PRIVATE_RECEIPT_INVALID") from error
    expected = {
        "runtime_wheel": (profile["llm"]["runtime_wheel_sha256"], None),
        "native_library": (profile["llm"]["native_library_sha256"], None),
        "model": (profile["llm"]["model_sha256"], profile["llm"]["model_bytes"]),
        "tts_archive": (profile["tts"]["archive_sha256"], None),
        "tts_vocoder": (profile["tts"]["vocoder_sha256"], None),
        "tts_wrapper_wheel": (profile["tts"]["wrapper_wheel_sha256"], None),
        "tts_core_wheel": (profile["tts"]["core_wheel_sha256"], None),
    }
    observed: dict[str, Any] = {}
    for name, (digest, size) in expected.items():
        item = artifacts.get(name)
        if not isinstance(item, dict) or type(item.get("path")) is not str:
            raise TargetPreflightError("PRIVATE_RECEIPT_INVALID")
        observed[name] = verify_artifact(Path(item["path"]), digest, size)
    if (
        microphone.get("transport") != "usb"
        or type(microphone.get("alsa_card_id")) is not str
        or not microphone["alsa_card_id"]
        or type(microphone.get("capture_device")) is not str
        or not microphone["capture_device"]
    ):
        raise TargetPreflightError("USB_MICROPHONE_IDENTITY_INVALID")
    return {
        "artifacts": observed,
        "measurement_microphone": {
            "transport": "usb",
            "alsa_card_id": microphone["alsa_card_id"],
            "capture_device": microphone["capture_device"],
        },
    }


def verify_usb_microphone_inventory(alsa_card_id: str) -> None:
    try:
        result = subprocess.run(
            ["arecord", "-l"], capture_output=True, text=True,
            timeout=10, check=False,
            env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TargetPreflightError("USB_MICROPHONE_PROBE_FAILED") from error
    if result.returncode != 0 or alsa_card_id not in result.stdout:
        raise TargetPreflightError("USB_MICROPHONE_NOT_PRESENT")


def preflight_environment(
    *,
    root: Path,
    implementation_sha: str,
    receipt_path: Path,
    profile_path: Path,
) -> dict[str, Any]:
    platform_facts = require_target_platform()
    require_network_offline()
    require_clean_checkout(root, implementation_sha)
    profile = json.loads(profile_path.read_text())
    receipt = verify_private_receipt(receipt_path, profile)
    verify_usb_microphone_inventory(receipt["measurement_microphone"]["alsa_card_id"])
    return {
        "status": "IDENTITY_VERIFIED_NOT_MEASURED",
        "platform": platform_facts,
        "artifact_sha256": {
            name: item["sha256"] for name, item in receipt["artifacts"].items()
        },
        "measurement_microphone": receipt["measurement_microphone"],
        "network_offline": True,
    }
