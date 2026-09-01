"""Repository-local checks for artifacts and sensitive material forbidden in Git."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


PROHIBITED_SUFFIXES = {
    ".a",
    ".bin",
    ".dll",
    ".dylib",
    ".flac",
    ".gguf",
    ".onnx",
    ".o",
    ".pt",
    ".pth",
    ".so",
    ".wav",
    ".whl",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}

PROHIBITED_PATH_PREFIXES = {
    "asr_r1/artifacts",
    "asr_r1/controlled",
    "asr_r1/evidence/raw",
    "asr_r1/evidence/runs",
    "asr_r1/fixtures/audio",
    "asr_r1/ssh",
}

SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub personal token": re.compile(rb"\bghp_[A-Za-z0-9]{30,}\b"),
}


@dataclass(frozen=True)
class SafetyFinding:
    path: str
    reason: str


def scan_repository(root: Path) -> list[SafetyFinding]:
    """Scan the visible worktree, including untracked files, but never `.git`."""

    root = root.resolve()
    findings: list[SafetyFinding] = []
    for directory, directory_names, filenames in os.walk(root, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names if name not in EXCLUDED_DIRECTORY_NAMES
        )
        base = Path(directory)
        for filename in sorted(filenames):
            path = base / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                findings.append(SafetyFinding(relative, "symlinks are not allowed in governed inputs"))
                continue
            if relative == ".env" or relative.endswith("/.env"):
                findings.append(SafetyFinding(relative, "operator environment file"))
            if any(
                relative == prefix or relative.startswith(f"{prefix}/")
                for prefix in PROHIBITED_PATH_PREFIXES
            ):
                findings.append(SafetyFinding(relative, "controlled or raw-data path"))
            if path.suffix.lower() in PROHIBITED_SUFFIXES:
                findings.append(SafetyFinding(relative, "prohibited model, binary, or audio suffix"))
            try:
                payload = path.read_bytes()
            except OSError as exc:
                findings.append(SafetyFinding(relative, f"unreadable file: {exc}"))
                continue
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(payload):
                    findings.append(SafetyFinding(relative, f"possible {label}"))
    return sorted(set(findings), key=lambda item: (item.path, item.reason))
