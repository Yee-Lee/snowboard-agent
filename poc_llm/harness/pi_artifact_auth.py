"""One-pass artifact authentication for physical-Pi execution packets.

Large model files are hashed once before any measured child startup.  Subsequent
child launches validate the immutable receipt and filesystem identity without
re-reading the complete model.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import time
from typing import Any


class ArtifactAuthenticationError(ValueError):
    pass


def streaming_digest(path: Path, *, timeout_s: float | None = None) -> str:
    value = hashlib.sha256()
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            if deadline is not None and time.monotonic() > deadline:
                raise ArtifactAuthenticationError("artifact authentication deadline exceeded")
            value.update(chunk)
    return value.hexdigest()


def stat_identity(path: Path) -> dict[str, int]:
    value = path.stat()
    return {
        "device": value.st_dev,
        "inode": value.st_ino,
        "mode": value.st_mode,
        "size_bytes": value.st_size,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
    }


def authenticate_model(
    path: Path,
    expected_sha256: str,
    expected_size_bytes: int,
    *,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Hash a model exactly once and bind the digest to stable filesystem metadata."""
    if not path.is_absolute() or path.resolve() != path or not path.is_file():
        raise ArtifactAuthenticationError("model path is not an absolute regular file")
    before = stat_identity(path)
    if (
        not stat.S_ISREG(before["mode"])
        or before["size_bytes"] != expected_size_bytes
        or before["mode"] & 0o222
    ):
        raise ArtifactAuthenticationError("model file type, size or read-only mode mismatch")
    started = time.monotonic()
    actual_sha256 = streaming_digest(path, timeout_s=timeout_s)
    duration_ms = round((time.monotonic() - started) * 1000, 3)
    after = stat_identity(path)
    if before != after:
        raise ArtifactAuthenticationError("model changed during authentication")
    if actual_sha256 != expected_sha256:
        raise ArtifactAuthenticationError("model SHA-256 mismatch")
    return {
        "path": str(path),
        "sha256": actual_sha256,
        "size_bytes": expected_size_bytes,
        "stat": after,
        "authentication_duration_ms": duration_ms,
    }


def verify_model_receipt(record: dict[str, Any], path: Path, expected_sha256: str) -> None:
    """Validate a prior one-pass receipt without reading the model contents again."""
    if (
        not path.is_absolute()
        or path.resolve() != path
        or record.get("path") != str(path)
        or record.get("sha256") != expected_sha256
        or record.get("size_bytes") != record.get("stat", {}).get("size_bytes")
        or stat_identity(path) != record.get("stat")
    ):
        raise ArtifactAuthenticationError("model authentication receipt no longer matches artifact")
