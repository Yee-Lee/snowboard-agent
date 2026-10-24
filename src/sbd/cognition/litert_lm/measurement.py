"""Private, dual-review-authorized laboratory entry; never product thresholds."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from sbd.cognition.llm import LLMFatalError
from sbd.cognition.litert_lm.lock import validate_product_profile, _unique_object

AUTH_FIELDS = frozenset({"schema_version", "harness_sha256", "candidate_sha", "profile_sha256", "target_identity"})
PV_FIELDS = frozenset({"schema_version", "harness_sha256", "content_sha256",
                       "profile_sha256", "target_identity"})
MEASUREMENT_SAFETY_FLOOR_BYTES = 512 * 1024**2
_ROOT = Path(__file__).resolve().parents[4]
_SEAL = object()


class MeasurementAuthorizationError(LLMFatalError):
    def __init__(self):
        super().__init__("M4B_MEASUREMENT_AUTHORIZATION_INVALID")


def validate_authorization(value: object, expected: Mapping[str, object]) -> dict[str, object]:
    """Validate exact Designer/Tester evidence approvals, not a cryptographic signature."""
    try:
        def matches(observed):
            return (type(observed) is dict and set(observed) == set(expected)
                    and all(type(observed[key]) is type(item) and observed[key] == item
                            for key, item in expected.items()))
        if (type(value) is not dict or set(value) != {"authorized_tuple", "approvals"}
                or set(expected) != AUTH_FIELDS or not matches(value["authorized_tuple"])
                or type(expected["schema_version"]) is not int or expected["schema_version"] != 1
                or expected["target_identity"] != "pi5-4gb-debian13-aarch64-cp3135"):
            raise ValueError
        for name, length in (("candidate_sha", 40), ("harness_sha256", 64), ("profile_sha256", 64)):
            if type(expected[name]) is not str or re.fullmatch(r"[0-9a-f]{%d}" % length, expected[name]) is None:
                raise ValueError
        approvals = value["approvals"]
        if type(approvals) is not list or len(approvals) != 2:
            raise ValueError
        roles = set()
        for item in approvals:
            if (type(item) is not dict or set(item) != {"role", "reviewer", "approved_at", "decision", "authorized_tuple"}
                    or item["role"] not in {"Designer", "Tester"} or item["role"] in roles
                    or item["decision"] != "Approved" or not matches(item["authorized_tuple"])
                    or type(item["reviewer"]) is not str or not item["reviewer"].strip()):
                raise ValueError
            instant = datetime.fromisoformat(item["approved_at"].replace("Z", "+00:00"))
            if instant.utcoffset() is None:
                raise ValueError
            roles.add(item["role"])
        return dict(expected)
    except Exception:
        raise MeasurementAuthorizationError() from None


def _read_authorization(path: Path) -> object:
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 65536:
            raise ValueError
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        return json.loads(raw, object_pairs_hook=_unique_object)
    except Exception:
        raise MeasurementAuthorizationError() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def protected_content(root: Path = _ROOT) -> tuple[tuple[str, str], ...]:
    """Return the exact pending protected bytes, including intended new files."""
    try:
        result = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached",
            "--others", "--exclude-standard", "--", "src", "scripts", "tests",
            "requirements", "config.example.yaml", "pyproject.toml", "uv.lock"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=15, check=True)
        names = sorted({name for name in result.stdout.decode("utf-8").split("\0") if name})
        if not names:
            raise ValueError
        rows = []
        for name in names:
            path = root / name
            if path.is_symlink():
                raise ValueError
            if not path.exists():
                rows.append((name, "deleted"))
            elif not path.is_file():
                raise ValueError
            else:
                rows.append((name, hashlib.sha256(path.read_bytes()).hexdigest()))
        return tuple(rows)
    except Exception:
        raise MeasurementAuthorizationError() from None


def protected_content_digest(root: Path = _ROOT) -> str:
    rows = protected_content(root)
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _verify_context(expected: Mapping[str, object], *, allow_dirty: bool = False) -> None:
    try:
        def git(*args):
            result = subprocess.run(["git", "-C", str(_ROOT), *args], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=True)
            return result.stdout.decode("ascii").strip()
        pv = set(expected) == PV_FIELDS
        if pv:
            if protected_content_digest(_ROOT) != expected["content_sha256"]:
                raise ValueError
        else:
            if git("rev-parse", "HEAD") != expected["candidate_sha"]:
                raise ValueError
            if not allow_dirty and git("status", "--porcelain", "--untracked-files=all"):
                raise ValueError
        harness = _ROOT / ("scripts/run-m4b-pv.py" if pv else "scripts/m4b_measurement.py")
        if harness.is_symlink() or hashlib.sha256(harness.read_bytes()).hexdigest() != expected["harness_sha256"]:
            raise ValueError
        if (sys.platform != "linux" or platform.machine() != "aarch64"
                or platform.python_implementation() != "CPython" or platform.python_version() != "3.13.5"):
            raise ValueError
        system = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
        if system.get("ID", "").strip('"') != "debian" or system.get("VERSION_ID", "").strip('"') != "13":
            raise ValueError
        if b"Raspberry Pi 5" not in Path("/proc/device-tree/model").read_bytes():
            raise ValueError
        memory = Path("/proc/meminfo").read_text()
        matched = re.search(r"^MemTotal:\s+(\d+) kB$", memory, re.MULTILINE)
        if matched is None or not 3 * 1024**3 <= int(matched[1]) * 1024 <= 4 * 1024**3:
            raise ValueError
    except Exception:
        raise MeasurementAuthorizationError() from None


class MeasurementGrant:
    __slots__ = ("_path", "_expected", "_seal", "_diagnostic", "_diagnostic_directory",
                 "_pv")

    def __init__(self, *args, **kwargs):
        raise MeasurementAuthorizationError()

    @classmethod
    def load(cls, authorization_path: Path, *, expected_tuple: Mapping[str, object], profile: Mapping[str, object]):
        grant = object.__new__(cls)
        grant._path = Path(authorization_path).absolute()
        grant._expected = MappingProxyType(dict(expected_tuple))
        grant._seal = _SEAL
        grant._diagnostic = False
        grant._diagnostic_directory = None
        grant._pv = False
        grant.authorize_profile(profile)
        return grant

    @classmethod
    def user_diagnostic(cls, *, expected_tuple: Mapping[str, object], profile: Mapping[str, object],
                        diagnostic_directory: Path):
        """Explicit pre-commit Pi convergence; never formal evidence or a release grant."""
        grant = object.__new__(cls)
        grant._path = None
        grant._expected = MappingProxyType(dict(expected_tuple))
        grant._seal = _SEAL
        grant._diagnostic = True
        grant._pv = False
        try:
            directory = Path(diagnostic_directory).resolve(strict=True)
            if (not directory.is_dir() or directory.is_relative_to(_ROOT)
                    or stat.S_IMODE(directory.stat().st_mode) & 0o077):
                raise ValueError
        except Exception:
            raise MeasurementAuthorizationError() from None
        grant._diagnostic_directory = directory
        grant.authorize_profile(profile)
        return grant

    @classmethod
    def pv(cls, *, expected_tuple: Mapping[str, object], profile: Mapping[str, object],
           private_directory: Path):
        """Automatically attested single-PV entry with no role approval artifact."""
        grant = object.__new__(cls)
        grant._path = None
        grant._expected = MappingProxyType(dict(expected_tuple))
        grant._seal = _SEAL
        grant._diagnostic = False
        grant._pv = True
        try:
            directory = Path(private_directory).resolve(strict=True)
            if (not directory.is_dir() or directory.is_relative_to(_ROOT)
                    or stat.S_IMODE(directory.stat().st_mode) & 0o077):
                raise ValueError
        except Exception:
            raise MeasurementAuthorizationError() from None
        grant._diagnostic_directory = directory
        grant.authorize_profile(profile)
        return grant

    def authorize_profile(self, profile: Mapping[str, object]) -> None:
        try:
            if self._seal is not _SEAL:
                raise ValueError
            validated = validate_product_profile(dict(profile), allow_measurement=True)
            if validated["profile_stage"] != "measurement" or validated["profile_sha256"] != self._expected["profile_sha256"]:
                raise ValueError
            if self._pv:
                if set(self._expected) != PV_FIELDS:
                    raise ValueError
                for name in ("harness_sha256", "content_sha256", "profile_sha256"):
                    if type(self._expected[name]) is not str or re.fullmatch(r"[0-9a-f]{64}", self._expected[name]) is None:
                        raise ValueError
                if (self._expected["schema_version"] != 1
                        or self._expected["target_identity"] != "pi5-4gb-debian13-aarch64-cp3135"):
                    raise ValueError
                _verify_context(self._expected)
            elif self._diagnostic:
                _verify_context(self._expected, allow_dirty=True)
            else:
                validate_authorization(_read_authorization(self._path), self._expected)
                _verify_context(self._expected)
        except Exception:
            raise MeasurementAuthorizationError() from None

    def child_arguments(self) -> list[str]:
        if self._pv:
            return ["--measurement-pv", "--measurement-private-directory",
                    str(self._diagnostic_directory), "--measurement-expected",
                    json.dumps(dict(self._expected), sort_keys=True, separators=(",", ":"))]
        if self._diagnostic:
            return ["--measurement-user-diagnostic", "--measurement-diagnostic-directory",
                    str(self._diagnostic_directory), "--measurement-expected",
                    json.dumps(dict(self._expected), sort_keys=True, separators=(",", ":"))]
        return ["--measurement-authorization", str(self._path),
                "--measurement-expected", json.dumps(dict(self._expected), sort_keys=True, separators=(",", ":"))]

    def is_user_diagnostic(self) -> bool:
        if self._seal is not _SEAL:
            raise MeasurementAuthorizationError()
        return self._diagnostic

    def check_sample(self, sample: object) -> None:
        try:
            if self._seal is not _SEAL:
                raise ValueError
            sample.validate()
            if sample.mem_available_bytes < MEASUREMENT_SAFETY_FLOOR_BYTES:
                raise ValueError
        except Exception:
            raise LLMFatalError("M4B_MEASUREMENT_STOP") from None
