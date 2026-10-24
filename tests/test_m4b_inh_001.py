"""Exact current evidence identity, scope, checksum and completeness regressions."""
import hashlib
from copy import deepcopy
import pytest
from scripts.m4b_inheritance import InheritanceError, validate_rows, validate_result_record


def record(test_id="M4B-MEM-001"):
    return dict(schema_version=1, test_id=test_id, case_id="M01", candidate_sha="a" * 40,
        profile_id="core-m4b-cognition-001", profile_sha256="b" * 64, matrix="PU", platform="darwin",
        python="3.13.15", start_monotonic_ns=1, end_monotonic_ns=2, status="Pass",
        evidence_sha256=hashlib.sha256(b"evidence").hexdigest())


def test_current_index_binds_checksum_and_exact_candidate():
    r = record()
    row = {"record": r, "evidence_locator": f"sha256/{r['evidence_sha256']}"}
    assert validate_rows([row], "a" * 40, profile_sha256="b" * 64,
        resolver=lambda _: b"evidence", required_ids={"M4B-MEM-001"}) == [r]
    for rows, resolver in (([row, row], lambda _: b"evidence"), ([row], lambda _: b"changed"),
                           ([], lambda _: b"evidence")):
        with pytest.raises(InheritanceError):
            validate_rows(rows, "a" * 40, profile_sha256="b" * 64,
                resolver=resolver, required_ids={"M4B-MEM-001"})


@pytest.mark.parametrize("changes", [
    {"test_id": "M4B-HIST-001"}, {"candidate_sha": "c" * 40}, {"profile_sha256": "d" * 64},
    {"private": "CANARY"}, {"matrix": "PR"}, {"matrix": "PS"},
    {"python": "3.14.0"}, {"end_monotonic_ns": 0}, {"case_id": "PRIVATE_SESSION"},
])
def test_metadata_rejects_retired_identity_wrong_scope_and_private_fields(changes):
    with pytest.raises(InheritanceError):
        validate_result_record({**record(), **changes}, candidate_sha="a" * 40,
                               profile_sha256="b" * 64)


def test_target_metadata_cannot_inherit_portable_evidence():
    r = record("M4B-PI-MEM-001")
    with pytest.raises(InheritanceError):
        validate_result_record(r, candidate_sha="a" * 40, profile_sha256="b" * 64)
