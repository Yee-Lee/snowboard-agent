#!/usr/bin/env python3
"""List and stream explicitly ready private evidence without staging an archive."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile


BUNDLE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
FORMAT = "llm-private-evidence-ready-v1"
RESERVED_NAMES = {"manifest.private.json", "SHA256SUMS"}


class ExportError(Exception):
    pass


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ExportError("source is not a regular file")
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
        after = os.fstat(source.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise ExportError("source changed during verification")
    return value.hexdigest()


def _relative_name(value: object, *, payload: bool) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ExportError("invalid relative name")
    name = PurePosixPath(value)
    if name.is_absolute() or any(part in {"", ".", ".."} for part in name.parts):
        raise ExportError("unsafe relative name")
    if payload and (not name.parts or name.parts[0] != "payload"):
        raise ExportError("archive payload name must be below payload/")
    return value


def _reject_symlink_components(path: Path, boundary: Path) -> None:
    current = boundary
    for part in path.relative_to(boundary).parts:
        current /= part
        if current.is_symlink():
            raise ExportError("symlink source is forbidden")


def _load(ready_root: Path, bundle_id: str) -> tuple[bytes, list[tuple[str, Path, dict]], bytes]:
    if not BUNDLE_ID_RE.fullmatch(bundle_id):
        raise ExportError("invalid bundle id")
    bundle_root = ready_root / bundle_id
    try:
        bundle_stat = bundle_root.lstat()
    except FileNotFoundError as error:
        raise ExportError("bundle not found") from error
    if not stat.S_ISDIR(bundle_stat.st_mode) or bundle_root.is_symlink():
        raise ExportError("bundle root must be a real directory")
    manifest_path = bundle_root / "manifest.private.json"
    try:
        manifest_stat = manifest_path.lstat()
    except FileNotFoundError as error:
        raise ExportError("ready manifest not found") from error
    if (not stat.S_ISREG(manifest_stat.st_mode) or manifest_path.is_symlink()
            or manifest_stat.st_mode & 0o077):
        raise ExportError("ready manifest must be a mode-private regular file")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExportError("invalid ready manifest") from error
    if (set(manifest) != {"format", "bundle_id", "ready", "entries"}
            or manifest["format"] != FORMAT or manifest["bundle_id"] != bundle_id
            or manifest["ready"] is not True or not isinstance(manifest["entries"], list)
            or not manifest["entries"]):
        raise ExportError("invalid ready manifest")

    rows: list[tuple[str, Path, dict]] = []
    names = set(RESERVED_NAMES)
    for record in manifest["entries"]:
        if (not isinstance(record, dict)
                or set(record) != {"archive_name", "source", "size_bytes", "sha256"}):
            raise ExportError("invalid payload entry")
        archive_name = _relative_name(record["archive_name"], payload=True)
        source_name = _relative_name(record["source"], payload=False)
        if archive_name in names:
            raise ExportError("duplicate archive name")
        names.add(archive_name)
        if (not isinstance(record["size_bytes"], int)
                or isinstance(record["size_bytes"], bool) or record["size_bytes"] < 0
                or not isinstance(record["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
            raise ExportError("invalid payload identity")
        source = bundle_root.joinpath(*PurePosixPath(source_name).parts)
        _reject_symlink_components(source, bundle_root)
        try:
            source_stat = source.lstat()
        except FileNotFoundError as error:
            raise ExportError("payload source missing") from error
        if not stat.S_ISREG(source_stat.st_mode):
            raise ExportError("payload source is not a regular file")
        if source_stat.st_size != record["size_bytes"] or _digest(source) != record["sha256"]:
            raise ExportError("payload identity mismatch")
        rows.append((archive_name, source, record))
    sums = (
        f"{hashlib.sha256(manifest_bytes).hexdigest()}  manifest.private.json\n"
        + "".join(f'{record["sha256"]}  {name}\n' for name, _, record in rows)
    ).encode()
    return manifest_bytes, rows, sums


def _summary(ready_root: Path, bundle_id: str) -> dict:
    manifest_bytes, rows, sums = _load(ready_root, bundle_id)
    return {"bundle_id": bundle_id,
            "estimated_bytes": len(manifest_bytes) + len(sums)
            + sum(record["size_bytes"] for _, _, record in rows)}


def list_ready(ready_root: Path) -> dict:
    if not ready_root.is_dir() or ready_root.is_symlink():
        raise ExportError("ready root must be a real directory")
    bundle_ids = sorted(
        path.name for path in ready_root.iterdir() if path.is_dir() and not path.is_symlink()
    )
    return {"schema_version": 1,
            "bundles": [_summary(ready_root, bundle_id) for bundle_id in bundle_ids]}


def _tar_info(name: str, size: int, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def stream(ready_root: Path, bundle_id: str, output) -> None:
    manifest_bytes, rows, sums = _load(ready_root, bundle_id)
    directories = sorted(
        {str(parent) for name, _, _ in rows for parent in PurePosixPath(name).parents
         if str(parent) not in {".", ""}},
        key=lambda name: (len(PurePosixPath(name).parts), name),
    )
    with tarfile.open(fileobj=output, mode="w|gz", format=tarfile.PAX_FORMAT) as archive:
        archive.addfile(_tar_info("manifest.private.json", len(manifest_bytes), 0o600),
                        io.BytesIO(manifest_bytes))
        archive.addfile(_tar_info("SHA256SUMS", len(sums), 0o600), io.BytesIO(sums))
        for name in directories:
            info = _tar_info(name, 0, 0o700)
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
        for name, source_path, record in rows:
            with source_path.open("rb") as source:
                current = os.fstat(source.fileno())
                expected = source_path.lstat()
                if (not stat.S_ISREG(current.st_mode)
                        or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
                        != (expected.st_dev, expected.st_ino, expected.st_size, expected.st_mtime_ns)):
                    raise ExportError("payload changed before streaming")
                archive.addfile(_tar_info(name, record["size_bytes"], 0o600), source)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    list_parser = commands.add_parser("list-ready")
    list_parser.add_argument("--ready-root", required=True)
    stream_parser = commands.add_parser("stream")
    stream_parser.add_argument("--ready-root", required=True)
    stream_parser.add_argument("--bundle-id", required=True)
    args = parser.parse_args(argv)
    try:
        ready_root = Path(args.ready_root).resolve()
        if args.command == "list-ready":
            print(json.dumps(list_ready(ready_root), sort_keys=True, separators=(",", ":")))
        else:
            stream(ready_root, args.bundle_id, sys.stdout.buffer)
            print(f"streamed bundle {args.bundle_id}", file=sys.stderr)
    except (ExportError, OSError, tarfile.TarError) as error:
        print(f"private evidence export refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
