#!/usr/bin/env python3
"""Fail-closed privacy checks for material that may enter Git.

The scanner never prints matched content. It reports only the path and stable rule
identifier so that its own output cannot become another disclosure channel.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


MAX_PUBLIC_BYTES = 2 * 1024 * 1024
ZERO_OID = "0" * 40

PRIVATE_SUFFIXES = {
    ".age",
    ".bin",
    ".db",
    ".flac",
    ".gz",
    ".key",
    ".litertlm",
    ".m4a",
    ".mp3",
    ".onnx",
    ".p12",
    ".pcm",
    ".pem",
    ".raw",
    ".ses",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".wav",
    ".zip",
}

PRIVATE_BASENAMES = {
    ".env",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}

TEXT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private-posix-home",
        re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/(?![<$])[^/\s'\"`]+/"),
    ),
    (
        "private-windows-home",
        re.compile(r"(?i)\b[A-Z]:\\Users\\(?![<$])[^\\\s'\"`]+\\"),
    ),
    (
        "operator-local-host",
        re.compile(r"(?i)\b[a-z_][a-z0-9_.-]*@[a-z0-9.-]+\.local\b"),
    ),
    (
        "credentialed-url",
        re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@"),
    ),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai-token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "slack-token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    ),
)

# These identities are explicitly public. The scanner does not reject ordinary
# names or email addresses; this declaration documents the approved exception.
PUBLIC_IDENTITIES = {"Yee.Lee", "yeelee.tw@gmail.com"}

PUBLIC_RECORD_FIELDS = {
    "test_id", "run_id", "candidate_sha", "artifact_sha256", "status",
    "metrics", "error_counts", "bundle_id", "user", "email",
}


def _public_record_valid(record: object) -> bool:
    if not isinstance(record, dict) or not {"test_id", "status"} <= record.keys():
        return False
    if record.keys() - PUBLIC_RECORD_FIELDS:
        return False
    for key, value in record.items():
        if key in {"metrics", "error_counts"}:
            if not isinstance(value, dict):
                return False
            for name, number in value.items():
                if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
                    return False
                if type(number) not in (int, float):
                    return False
                if isinstance(number, float) and not math.isfinite(number):
                    return False
                if key == "error_counts" and (type(number) is not int or number < 0):
                    return False
            continue
        if not isinstance(value, str):
            return False
        if key == "status":
            if value not in {"PASS", "FAIL", "REJECTED", "ACCEPTED", "SKIP", "UNKNOWN",
                             "INCONCLUSIVE", "NOT_APPLICABLE"}:
                return False
        elif key in {"candidate_sha", "artifact_sha256"}:
            length = 40 if key == "candidate_sha" else 64
            if not re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value):
                return False
        elif key in {"user", "email"}:
            expected = "Yee.Lee" if key == "user" else "yeelee.tw@gmail.com"
            if value != expected:
                return False
        elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
            return False
    return True


def _public_evidence_valid(text: str) -> bool:
    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, RecursionError):
        return False
    return (
        isinstance(value, dict)
        and value.keys() == {"schema_version", "records"}
        and type(value["schema_version"]) is int
        and value["schema_version"] == 1
        and isinstance(value["records"], list)
        and all(_public_record_valid(record) for record in value["records"])
    )


class PrivacyGateError(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    rule: str


def _git(*args: str, input_bytes: bytes | None = None) -> bytes:
    process = subprocess.run(
        ["git", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise PrivacyGateError(f"git command failed: {' '.join(args[:2])}")
    return process.stdout


def _safe_repo_path(raw: str) -> str:
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise PrivacyGateError("Git returned an unsafe repository path")
    return path.as_posix()


def _path_findings(path: str, size: int) -> set[Finding]:
    findings: set[Finding] = set()
    pure = PurePosixPath(path)
    lowered = pure.name.lower()
    if lowered in PRIVATE_BASENAMES or lowered.startswith(".env."):
        findings.add(Finding(path, "private-filename"))
    if pure.suffix.lower() in PRIVATE_SUFFIXES:
        findings.add(Finding(path, "private-file-type"))
    if size > MAX_PUBLIC_BYTES:
        findings.add(Finding(path, "public-file-size-limit"))
    return findings


def _decode_text(blob: bytes) -> str | None:
    if b"\x00" in blob:
        return None
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _content_findings(
    path: str,
    text: str,
    *,
    strict_evidence: bool,
    sentinels: Sequence[bytes],
) -> set[Finding]:
    findings: set[Finding] = set()
    for name, pattern in TEXT_RULES:
        if pattern.search(text):
            findings.add(Finding(path, name))
    if strict_evidence and not _public_evidence_valid(text):
        findings.add(Finding(path, "public-evidence-schema"))
    encoded = text.encode("utf-8")
    if any(sentinel and sentinel in encoded for sentinel in sentinels):
        findings.add(Finding(path, "private-sentinel"))
    return findings


def scan_blob(
    path: str,
    blob: bytes,
    *,
    strict_evidence: bool = False,
    sentinels: Sequence[bytes] = (),
) -> set[Finding]:
    findings = _path_findings(path, len(blob))
    decoded = _decode_text(blob)
    if decoded is None:
        findings.add(Finding(path, "binary-content"))
        return findings
    findings.update(
        _content_findings(
            path,
            decoded,
            strict_evidence=strict_evidence,
            sentinels=sentinels,
        )
    )
    return findings


def _sentinels(path: Path | None) -> tuple[bytes, ...]:
    if path is None:
        return ()
    try:
        lines = path.read_bytes().splitlines()
    except OSError as error:
        raise PrivacyGateError("sentinel file is unreadable") from error
    values = tuple(line for line in lines if line)
    if not values:
        raise PrivacyGateError("sentinel file is empty")
    return values


def scan_staged(*, strict_evidence: bool, sentinels: Sequence[bytes]) -> set[Finding]:
    names = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split(b"\0")
    paths = [_safe_repo_path(name.decode("utf-8")) for name in names if name]
    findings: set[Finding] = set()
    for path in paths:
        blob = _git("show", f":{path}")
        findings.update(
            scan_blob(
                path,
                blob,
                strict_evidence=strict_evidence,
                sentinels=sentinels,
            )
        )
    return findings


def _empty_tree() -> str:
    return _git("hash-object", "-t", "tree", "--stdin", input_bytes=b"").decode().strip()


def scan_range(
    base: str,
    head: str,
    *,
    strict_evidence: bool,
    sentinels: Sequence[bytes],
) -> set[Finding]:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", head):
        raise PrivacyGateError("head must be a full Git object ID")
    if base == ZERO_OID:
        base = _empty_tree()
    elif not re.fullmatch(r"[0-9a-fA-F]{40}", base):
        raise PrivacyGateError("base must be a full Git object ID")
    names = _git("diff", "--name-only", "--diff-filter=ACMR", "-z", base, head).split(b"\0")
    paths = [_safe_repo_path(name.decode("utf-8")) for name in names if name]
    findings: set[Finding] = set()
    for path in paths:
        blob = _git("show", f"{head}:{path}")
        findings.update(
            scan_blob(
                path,
                blob,
                strict_evidence=strict_evidence,
                sentinels=sentinels,
            )
        )
    return findings


def scan_files(
    paths: Iterable[Path],
    *,
    strict_evidence: bool,
    sentinels: Sequence[bytes],
) -> set[Finding]:
    findings: set[Finding] = set()
    for path in paths:
        if path.is_absolute():
            try:
                display_path = path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                display_path = f"<external>/{path.name}"
        else:
            display_path = path.as_posix()
        try:
            if path.is_symlink() or not path.is_file():
                findings.add(Finding(display_path, "unsafe-file-kind"))
                continue
            blob = path.read_bytes()
        except OSError:
            findings.add(Finding(display_path, "unreadable-file"))
            continue
        findings.update(
            scan_blob(
                display_path,
                blob,
                strict_evidence=strict_evidence,
                sentinels=sentinels,
            )
        )
    return findings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sentinel-file",
        type=Path,
        help="newline-delimited private canaries; values are never printed",
    )
    parser.add_argument(
        "--strict-evidence",
        action="store_true",
        help="require the public evidence JSON schema; use only for evidence exports",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan-staged", help="scan blobs currently staged in Git")
    range_parser = sub.add_parser("scan-range", help="scan content introduced by a Git range")
    range_parser.add_argument("--base", required=True)
    range_parser.add_argument("--head", required=True)
    files_parser = sub.add_parser("scan-files", help="scan complete filesystem files")
    files_parser.add_argument("paths", nargs="+", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sentinels = _sentinels(args.sentinel_file)
        if args.command == "scan-staged":
            findings = scan_staged(strict_evidence=args.strict_evidence, sentinels=sentinels)
        elif args.command == "scan-range":
            findings = scan_range(
                args.base,
                args.head,
                strict_evidence=args.strict_evidence,
                sentinels=sentinels,
            )
        else:
            findings = scan_files(
                args.paths,
                strict_evidence=args.strict_evidence,
                sentinels=sentinels,
            )
    except PrivacyGateError as error:
        print(f"privacy gate error: {error}", file=sys.stderr)
        return 2
    if findings:
        for finding in sorted(findings):
            print(f"{finding.path}: {finding.rule}", file=sys.stderr)
        print(f"privacy gate failed: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("privacy gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
