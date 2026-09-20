"""Tracked-content identity for pre-commit M4-ERR verification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


DEFAULT_SCOPES = (
    "src",
    "scripts",
    "tests",
    "requirements",
    "docs/implement/ch_m4_error_handling.md",
    "docs/test_spec/test_spec_M4_ERR.md",
    "config.example.yaml",
    "pyproject.toml",
)


def tracked_content(
    root: Path,
    *,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    pending_new_paths: tuple[str, ...] = (),
) -> tuple[tuple[str, str], ...]:
    """Return deterministic tracked bytes plus explicitly declared pending files."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--", *scopes],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=True,
    )
    names = {name for name in result.stdout.decode("utf-8").split("\0") if name}
    for name in pending_new_paths:
        if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("pending path must be a relative repository path")
        names.add(name)
    if not names:
        raise ValueError("tracked content set is empty")

    rows: list[tuple[str, str]] = []
    for name in sorted(names):
        path = root / name
        if path.is_symlink():
            raise ValueError("candidate content must not contain symlinks")
        if not path.exists():
            rows.append((name, "deleted"))
        elif not path.is_file():
            raise ValueError("candidate content path must be a regular file")
        else:
            rows.append((name, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(rows)


def tracked_content_digest(
    root: Path,
    *,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    pending_new_paths: tuple[str, ...] = (),
) -> str:
    encoded = json.dumps(
        tracked_content(root, scopes=scopes, pending_new_paths=pending_new_paths),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
