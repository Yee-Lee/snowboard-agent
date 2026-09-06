#!/usr/bin/env python3
"""Stream ready private-evidence bundles from a Pi into a local verified inbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Sequence


BUNDLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
SHA256 = re.compile(r"[0-9a-f]{64}")
TEAM_EXPORT = {
    "audio": (
        "snowboard-agent-dev/audio/poc_audio/tools/export_private_evidence.py",
        "snowboard-agent-dev/evidence-export/audio",
    ),
    "llm": (
        "snowboard-agent-dev/poc_llm/poc_llm/tools/export_private_evidence.py",
        "snowboard-agent-dev/evidence-export/poc_llm",
    ),
}


class DownloadError(RuntimeError):
    pass


def _ssh_command(target: str, team: str, action: str, bundle_id: str | None = None) -> list[str]:
    tool, ready_root = TEAM_EXPORT[team]
    command = ["ssh", target, "python3", tool, action, "--ready-root", ready_root]
    if bundle_id is not None:
        command.extend(("--bundle-id", bundle_id))
    return command


def _ready_bundles(target: str, team: str, timeout: int) -> list[str]:
    try:
        result = subprocess.run(
            _ssh_command(target, team, "list-ready"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DownloadError("could not query the remote ready list") from error
    if result.returncode != 0:
        raise DownloadError("remote ready-list command failed")
    try:
        value = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DownloadError("remote ready list is not valid JSON") from error
    if not isinstance(value, dict) or set(value) != {"schema_version", "bundles"}:
        raise DownloadError("remote ready list has an unexpected schema")
    if value["schema_version"] != 1 or not isinstance(value["bundles"], list):
        raise DownloadError("remote ready list has an unsupported schema")
    bundle_ids: list[str] = []
    for record in value["bundles"]:
        if (
            not isinstance(record, dict)
            or set(record) != {"bundle_id", "estimated_bytes"}
            or not isinstance(record["bundle_id"], str)
            or not BUNDLE_ID.fullmatch(record["bundle_id"])
            or type(record["estimated_bytes"]) is not int
            or record["estimated_bytes"] < 0
        ):
            raise DownloadError("remote ready list contains an invalid record")
        bundle_ids.append(record["bundle_id"])
    if len(bundle_ids) != len(set(bundle_ids)):
        raise DownloadError("remote ready list contains duplicate bundle IDs")
    return bundle_ids


def _hash_stream(source: BinaryIO) -> tuple[str, bytes | None]:
    digest = hashlib.sha256()
    captured = bytearray()
    capture = True
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)
        if capture:
            captured.extend(block)
            if len(captured) > 8 * 1024 * 1024:
                capture = False
                captured.clear()
    return digest.hexdigest(), bytes(captured) if capture else None


def _safe_archive_name(raw: str) -> str:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or ".." in path.parts or raw != path.as_posix():
        raise DownloadError("archive contains an unsafe entry name")
    return path.as_posix()


def verify_archive(path: Path, expected_bundle_id: str) -> dict[str, object]:
    """Verify a bundle without extracting it or printing private content."""

    actual: dict[str, str] = {}
    captured: dict[str, bytes] = {}
    names: set[str] = set()
    try:
        with tarfile.open(path, mode="r|gz") as archive:
            for member in archive:
                name = _safe_archive_name(member.name)
                if name in names:
                    raise DownloadError("archive contains a duplicate entry")
                names.add(name)
                if member.isdir():
                    continue
                if not member.isfile():
                    raise DownloadError("archive contains a non-regular entry")
                source = archive.extractfile(member)
                if source is None:
                    raise DownloadError("archive entry is unreadable")
                digest, content = _hash_stream(source)
                actual[name] = digest
                if name in {"manifest.private.json", "SHA256SUMS"}:
                    if content is None:
                        raise DownloadError("archive metadata is too large")
                    captured[name] = content
    except (tarfile.TarError, OSError) as error:
        raise DownloadError("archive is unreadable") from error

    if set(captured) != {"manifest.private.json", "SHA256SUMS"}:
        raise DownloadError("archive metadata is incomplete")
    try:
        manifest = json.loads(captured["manifest.private.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DownloadError("private manifest is invalid") from error
    if not isinstance(manifest, dict) or manifest.get("bundle_id") != expected_bundle_id:
        raise DownloadError("private manifest bundle ID does not match")

    declared: dict[str, str] = {}
    try:
        lines = captured["SHA256SUMS"].decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise DownloadError("checksum manifest is invalid") from error
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            raise DownloadError("checksum manifest contains an invalid row")
        name = _safe_archive_name(match.group(2))
        if name == "SHA256SUMS" or name in declared:
            raise DownloadError("checksum manifest contains a duplicate or self-entry")
        declared[name] = match.group(1)
    expected_names = set(actual) - {"SHA256SUMS"}
    if set(declared) != expected_names:
        raise DownloadError("checksum manifest does not cover the archive")
    if any(actual[name] != digest for name, digest in declared.items()):
        raise DownloadError("archive payload checksum mismatch")

    archive_digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            archive_digest.update(block)
    return {
        "bundle_id": expected_bundle_id,
        "archive_sha256": archive_digest.hexdigest(),
        "archive_bytes": size,
        "entry_count": len(actual),
    }


def _download_one(target: str, team: str, bundle_id: str, destination: Path, timeout: int) -> Path:
    incoming = destination / "incoming"
    verified = destination / "verified"
    incoming.mkdir(parents=True, exist_ok=True, mode=0o700)
    verified.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    os.chmod(incoming, 0o700)
    os.chmod(verified, 0o700)

    filename = f"{team}-{bundle_id}.private.tgz"
    partial = incoming / f"{filename}.part"
    final = verified / filename
    receipt_path = verified / f"{filename}.receipt.json"
    if partial.exists() or final.exists() or receipt_path.exists():
        raise DownloadError(f"local bundle already exists: {team}/{bundle_id}")
    try:
        with partial.open("xb") as output:
            os.chmod(partial, 0o600)
            result = subprocess.run(
                _ssh_command(target, team, "stream", bundle_id),
                stdout=output,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
        if result.returncode != 0:
            raise DownloadError(f"remote stream failed: {team}/{bundle_id}")
        receipt = verify_archive(partial, bundle_id)
        receipt.update(
            {
                "schema_version": 1,
                "team": team,
                "source_locator": f"PI_EVIDENCE_EXPORT/{team}/{bundle_id}",
                "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        os.replace(partial, final)
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        os.chmod(final, 0o600)
        os.chmod(receipt_path, 0o600)
        return final
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DownloadError(f"download failed: {team}/{bundle_id}") from error
    finally:
        if partial.exists():
            partial.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-target", required=True, help="local-only SSH target")
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--team", choices=tuple(TEAM_EXPORT), action="append")
    parser.add_argument("--bundle-id", action="append")
    parser.add_argument("--list-timeout", type=int, default=30)
    parser.add_argument("--stream-timeout", type=int, default=7200)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    teams = args.team or list(TEAM_EXPORT)
    try:
        selected = set(args.bundle_id or ())
        if any(not BUNDLE_ID.fullmatch(value) for value in selected):
            raise DownloadError("bundle ID is invalid")
        work: list[tuple[str, str]] = []
        for team in teams:
            ready = _ready_bundles(args.ssh_target, team, args.list_timeout)
            work.extend((team, bundle_id) for bundle_id in ready if not selected or bundle_id in selected)
        if selected - {bundle_id for _, bundle_id in work}:
            raise DownloadError("a requested bundle is not ready")
        if not work:
            print("No ready bundles.")
            return 0
        for team, bundle_id in work:
            result = _download_one(
                args.ssh_target, team, bundle_id, args.destination, args.stream_timeout,
            )
            print(f"Verified {team}/{bundle_id}: {result.name}")
    except DownloadError as error:
        print(f"download failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
