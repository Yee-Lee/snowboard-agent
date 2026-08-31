"""M4B-INH-001 — strict POC inheritance generator schema."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts.m4b_inheritance import (
    AREA_REQUIRED_IDS, FIXED, InheritanceError, ROW_FIELDS, TARGET_CARD_IDS,
    validate_rows,
)


def _rows(candidate: str):
    manifest = b"manifest"
    evidence = b"evidence"
    blobs = {"manifest": manifest, "evidence": evidence}
    rows = []
    identities = [
        (area, test_id)
        for area in sorted(AREA_REQUIRED_IDS)
        for test_id in sorted(AREA_REQUIRED_IDS[area])
    ]
    for index, (area, test_id) in enumerate(identities):
        run_id = "acceptance-001"
        proof_name = f"proof-{index}"
        blobs[proof_name] = json.dumps({
            "candidate_sha": candidate, "test_id": test_id, "status": "Pass", "run_id": run_id,
        }).encode()
        row = {
            **FIXED, "area": area,
            "poc_manifest_locator": "manifest", "poc_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "poc_evidence_locator": "evidence", "poc_evidence_sha256": hashlib.sha256(evidence).hexdigest(),
            "poc_machine_result": "FAIL" if area in {"P9", "P10B"} else "PASS",
            "user_waiver": "KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION" if area in {"P9", "P10B"} else None,
            "classification": "waiver" if area in {"P9", "P10B"} else "delta",
            "inheritance_reason": f"Core delta {test_id}", "product_sha": candidate,
            "delta_test_id": test_id, "delta_result": "PASS",
            "result_proof_kind": (
                "lock_preflight_reconciliation" if test_id == "M4B-LOCK-001"
                else "target_card" if test_id in TARGET_CARD_IDS
                else "portable_reconciliation"
            ),
            "result_locator": proof_name,
            "portable_run_id": None if test_id in TARGET_CARD_IDS or test_id == "M4B-LOCK-001" else run_id,
            "acceptance_run_id": run_id if test_id in TARGET_CARD_IDS or test_id == "M4B-LOCK-001" else None,
        }
        if row["result_proof_kind"] == "portable_reconciliation":
            proof = json.loads(blobs[proof_name])
            proof["python_minors"] = ["3.11", "3.12", "3.13"]
            blobs[proof_name] = json.dumps(proof).encode()
        assert set(row) == ROW_FIELDS
        rows.append(row)
    return rows, blobs.__getitem__


def test_m4b_inh_001_accepts_complete_immutable_index() -> None:
    candidate = "a" * 40
    rows, resolver = _rows(candidate)
    assert len(validate_rows(rows, candidate, resolver=resolver)) == 17


def test_m4b_inh_001_rejects_self_row_mixed_sha_and_rewritten_waiver() -> None:
    candidate = "a" * 40
    for mutate in (
        lambda rows: rows[0].update(delta_test_id="M4B-INH-001"),
        lambda rows: rows[0].update(product_sha="b" * 40),
        lambda rows: next(row for row in rows if row["area"] == "P9").update(poc_machine_result="PASS"),
    ):
        rows, resolver = _rows(candidate)
        mutate(rows)
        with pytest.raises(InheritanceError):
            validate_rows(rows, candidate, resolver=resolver)


def test_m4b_inh_001_rejects_missing_area_evidence_duplicate_and_wrong_scope() -> None:
    candidate = "a" * 40
    for mutate in (
        lambda rows: rows.pop(next(
            index for index, row in enumerate(rows)
            if row["area"] == "P12" and row["delta_test_id"] == "M4B-PRIV-001"
        )),
        lambda rows: rows.append(dict(rows[0])),
        lambda rows: rows[0].update(result_proof_kind="portable_reconciliation"),
    ):
        rows, resolver = _rows(candidate)
        mutate(rows)
        with pytest.raises(InheritanceError):
            validate_rows(rows, candidate, resolver=resolver)
