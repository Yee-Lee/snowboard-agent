#!/usr/bin/env python3
"""One-pass authenticated installer for the pinned ARM64 API wheel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_member(member: zipfile.ZipInfo) -> None:
    path = PurePosixPath(member.filename)
    if (
        not member.filename
        or member.filename.startswith("/")
        or "\\" in member.filename
        or ".." in path.parts
    ):
        raise ValueError("wheel contains unsafe member path")
    mode = member.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise ValueError("wheel contains symlink member")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "installer_id": "G1-ARM64-WHEEL-INSTALLER-002",
        "result": "FAIL",
    }
    created_target = False
    try:
        if args.target.exists():
            raise ValueError("install target is dirty")
        if not args.target.is_absolute():
            raise ValueError("install target is not absolute")
        if not args.wheel.is_file() or digest(args.wheel) != args.wheel_sha256:
            raise ValueError("wheel identity mismatch")
        with zipfile.ZipFile(args.wheel) as archive:
            for member in archive.infolist():
                validate_member(member)
            args.target.mkdir(parents=True)
            created_target = True
            archive.extractall(args.target)
        report["result"] = "PASS"
        report["wheel_sha256"] = args.wheel_sha256
    except Exception as error:
        if created_target:
            shutil.rmtree(args.target, ignore_errors=True)
        report["violation"] = str(error)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
