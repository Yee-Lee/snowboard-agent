#!/usr/bin/env python3
"""List or stream ready private Audio evidence without staging an archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import sys
import tarfile
from pathlib import Path, PurePosixPath


BUNDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def require_owner_only(path: Path, label: str) -> None:
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"{label} must be owner-only")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_ready(root: Path) -> list[tuple[Path, dict]]:
    ready = root
    if ready.is_symlink() or not ready.is_dir():
        raise ValueError("private evidence ready root is unavailable")
    require_owner_only(ready, "private evidence ready root")
    bundles = []
    for path in sorted(ready.glob("*.private.json")):
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError("ready manifest must be a mode-private regular file")
        document = json.loads(path.read_text(encoding="utf-8"))
        bundle_id = document.get("bundle_id")
        if (
            document.get("schema_version") != "1.0"
            or document.get("status") != "READY"
            or not isinstance(bundle_id, str)
            or not BUNDLE_RE.fullmatch(bundle_id)
        ):
            raise ValueError("ready manifest identity is invalid")
        bundles.append((path, document))
    if len({item[1]["bundle_id"] for item in bundles}) != len(bundles):
        raise ValueError("duplicate ready bundle ID")
    return bundles


def verified_entries(manifest_path: Path, document: dict) -> list[tuple[str, Path, int, str]]:
    entries = []
    names: set[str] = set()
    for item in document.get("payload", []):
        name = str(item.get("archive_name", ""))
        pure = PurePosixPath(name)
        if (
            pure.is_absolute() or not pure.parts or ".." in pure.parts
            or name in {"manifest.private.json", "SHA256SUMS"} or name in names
        ):
            raise ValueError("unsafe or duplicate archive name")
        names.add(name)
        source = PurePosixPath(str(item.get("source", "")))
        if source.is_absolute() or not source.parts or ".." in source.parts:
            raise ValueError("private evidence source is unsafe")
        path = manifest_path.parent.joinpath(*source.parts)
        current = manifest_path.parent
        if any((current := current / part).is_symlink() for part in source.parts):
            raise ValueError("private evidence source contains a symlink")
        if not path.is_file():
            raise ValueError("private evidence payload must be a regular file")
        if path.resolve().parent != manifest_path.parent.resolve() and not path.resolve().is_relative_to(manifest_path.parent.resolve()):
            raise ValueError("private evidence payload escapes its bundle root")
        current = path.parent
        while current != manifest_path.parent:
            require_owner_only(current, "private evidence payload directory")
            current = current.parent
        require_owner_only(path, "private evidence payload")
        size = int(item.get("size_bytes", -1))
        digest = str(item.get("sha256", ""))
        if path.stat().st_size != size or sha256_file(path) != digest:
            raise ValueError("private evidence payload identity mismatch")
        entries.append((name, path, size, digest))
    if not entries:
        raise ValueError("ready bundle contains no payload")
    return entries


def list_ready(root: Path) -> dict:
    rows = []
    for path, document in load_ready(root):
        entries = verified_entries(path, document)
        rows.append({
            "bundle_id": document["bundle_id"],
            "estimated_bytes": sum(item[2] for item in entries),
        })
    return {"schema_version": 1, "bundles": rows}


def stream_bundle(root: Path, bundle_id: str, output) -> None:
    matches = [(path, doc) for path, doc in load_ready(root) if doc["bundle_id"] == bundle_id]
    if len(matches) != 1:
        raise ValueError("ready bundle ID is unavailable")
    manifest_path, document = matches[0]
    entries = verified_entries(manifest_path, document)
    manifest_bytes = manifest_path.read_bytes()
    archive_entries = [(f"payload/{name}", path, size, digest) for name, path, size, digest in entries]
    sums = (
        f"{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.private.json\n"
        + "".join(f"{digest}  {name}\n" for name, _, _, digest in archive_entries)
    ).encode()
    with tarfile.open(fileobj=output, mode="w|gz") as archive:
        for name, payload in (("manifest.private.json", manifest_bytes), ("SHA256SUMS", sums)):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(payload))
        for name, path, size, _ in archive_entries:
            info = tarfile.TarInfo(name)
            info.size = size
            info.mode = 0o600
            with path.open("rb") as source:
                archive.addfile(info, source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list-ready")
    listing.add_argument("--ready-root", type=Path, required=True)
    stream = sub.add_parser("stream")
    stream.add_argument("--ready-root", type=Path, required=True)
    stream.add_argument("--bundle-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "list-ready":
            print(json.dumps(list_ready(args.ready_root), sort_keys=True))
        else:
            stream_bundle(args.ready_root, args.bundle_id, sys.stdout.buffer)
            print(f"streamed private evidence bundle: {args.bundle_id}", file=sys.stderr)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"private evidence export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
