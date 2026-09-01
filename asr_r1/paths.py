"""Fail-closed resolution for repository-owned resource paths."""

from __future__ import annotations

from pathlib import Path


def resolve_repo_resource(repo_root: Path, relative: str | Path) -> Path:
    """Resolve a repo-relative resource and reject absolute or escaping paths."""

    repo_root = repo_root.resolve()
    relative = Path(relative)
    if relative.is_absolute():
        raise ValueError("repository resource path must be relative")
    resolved = (repo_root / relative).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("repository resource path escapes the repository root") from exc
    return resolved
