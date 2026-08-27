"""M4A-INH-001 — fail-closed POC-to-product inheritance generator."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.m4a_inheritance import (
    ACCEPTED_AUDIO_SHA,
    DELIVERY_ID,
    REQUIRED_AREAS,
    InheritanceError,
    resolve_locator,
    validate_rows,
)


CANDIDATE = "1" * 40


def _rows() -> tuple[list[dict[str, str]], dict[str, bytes]]:
    content: dict[str, bytes] = {}
    rows = []
    for index, area in enumerate(sorted(REQUIRED_AREAS)):
        poc_locator = f"poc:{index}"
        result_locator = f"result:{index}"
        poc = f"accepted POC evidence {area}".encode()
        test_id = "M4A-INH-001"
        content[poc_locator] = poc
        content[result_locator] = json.dumps({
            "candidate_sha": CANDIDATE, "test_id": test_id, "status": "Pass",
        }).encode()
        rows.append({
            "area": area,
            "poc_delivery_id": DELIVERY_ID,
            "accepted_audio_sha": ACCEPTED_AUDIO_SHA,
            "poc_locator": poc_locator,
            "poc_sha256": hashlib.sha256(poc).hexdigest(),
            "classification": "reused_rerun",
            "inheritance_reason": f"Rerun product delta under {test_id}",
            "product_sha": CANDIDATE,
            "delta_test_id": test_id,
            "delta_result": "PASS",
            "result_locator": result_locator,
        })
    return rows, content


def test_m4a_inh_001_accepts_complete_same_sha_content_proven_index() -> None:
    rows, content = _rows()
    assert validate_rows(rows, CANDIDATE, resolver=content.__getitem__) == rows


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows[0].pop("classification"),
        lambda rows: rows[0].__setitem__("accepted_audio_sha", "0" * 40),
        lambda rows: rows[0].__setitem__("product_sha", "2" * 40),
        lambda rows: rows[0].__setitem__("delta_test_id", "UNKNOWN"),
        lambda rows: rows[0].__setitem__("delta_result", "Pending"),
        lambda rows: rows[0].__setitem__("inheritance_reason", "沿用POC"),
        lambda rows: rows.pop(),
    ],
)
def test_m4a_inh_001_rejects_missing_mixed_or_unproved_rows(mutation) -> None:
    rows, content = _rows()
    mutation(rows)
    with pytest.raises(InheritanceError):
        validate_rows(rows, CANDIDATE, resolver=content.__getitem__)


@pytest.mark.parametrize("locator_kind", ["poc", "result"])
def test_m4a_inh_001_nonempty_missing_locator_fails_closed(locator_kind: str) -> None:
    rows, content = _rows()
    key = f"{locator_kind}_locator"
    rows[0][key] = "missing:content"
    with pytest.raises((InheritanceError, KeyError)):
        validate_rows(rows, CANDIDATE, resolver=content.__getitem__)


def test_m4a_inh_001_rejects_wrong_resolved_content_hash_and_result_identity() -> None:
    rows, content = _rows()
    content[rows[0]["poc_locator"]] = b"drift"
    with pytest.raises(InheritanceError, match="checksum"):
        validate_rows(rows, CANDIDATE, resolver=content.__getitem__)
    rows, content = _rows()
    content[rows[0]["result_locator"]] = json.dumps({
        "candidate_sha": CANDIDATE, "test_id": "M4A-LOCK-001", "status": "Pass",
    }).encode()
    with pytest.raises(InheritanceError, match="identity"):
        validate_rows(rows, CANDIDATE, resolver=content.__getitem__)


def test_m4a_inh_001_local_locator_requires_readable_regular_nonsymlink_file(
    tmp_path: Path,
) -> None:
    valid = tmp_path / "valid.json"
    valid.write_bytes(b"evidence")
    assert resolve_locator(str(valid)) == b"evidence"
    with pytest.raises(InheritanceError):
        resolve_locator(str(tmp_path / "missing"))
    with pytest.raises(InheritanceError):
        resolve_locator(str(tmp_path))
    link = tmp_path / "link"
    link.symlink_to(valid)
    with pytest.raises(InheritanceError):
        resolve_locator(str(link))
    valid.chmod(0)
    with pytest.raises(InheritanceError):
        resolve_locator(str(valid))


def test_m4a_inh_001_git_locator_uses_frozen_revision_not_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b"frozen-content", b"")

    monkeypatch.setattr(subprocess, "run", run)
    revision = "a" * 40
    locator = f"{tmp_path}@{revision}:evidence/result.json"
    assert resolve_locator(locator) == b"frozen-content"
    assert calls == [[
        "git", "-C", str(tmp_path.resolve()), "show",
        f"{revision}:evidence/result.json",
    ]]
