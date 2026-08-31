"""Validate the Tester-owned M4b POC-to-product inheritance index."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any


AREAS = {"P1", "P2", "P3", "P4", "P5", "P6.1", "P7.1", "P8", "P9", "P10A", "P10B", "P11", "P12"}
TEST_IDS = {
    "M4B-CFG-001", "M4B-LOCK-001", "M4B-IPC-001", "M4B-RDY-001", "M4B-GEN-001",
    "M4B-OUT-001", "M4B-P5-001", "M4B-CAN-001", "M4B-REC-001", "M4B-HIST-001",
    "M4B-PRIV-001", "M4B-OFF-001", "M4B-RES-001", "M4B-PKG-001",
}
AREA_REQUIRED_IDS = {
    "P1": {"M4B-RDY-001"},
    "P2": {"M4B-OUT-001"},
    "P3": {"M4B-OUT-001"},
    "P4": {"M4B-GEN-001"},
    "P5": {"M4B-P5-001", "M4B-CAN-001"},
    "P6.1": {"M4B-CAN-001"},
    "P7.1": {"M4B-REC-001"},
    "P8": {"M4B-HIST-001"},
    "P9": {"M4B-RES-001"},
    "P10A": {"M4B-GEN-001", "M4B-REC-001"},
    "P10B": {"M4B-RES-001"},
    "P11": {"M4B-LOCK-001", "M4B-PKG-001"},
    "P12": {"M4B-OFF-001", "M4B-PRIV-001"},
}
TARGET_CARD_IDS = {
    "M4B-RDY-001", "M4B-GEN-001", "M4B-OUT-001", "M4B-P5-001",
    "M4B-CAN-001", "M4B-REC-001", "M4B-HIST-001", "M4B-PRIV-001",
    "M4B-OFF-001", "M4B-RES-001", "M4B-PKG-001",
}
ROW_FIELDS = {
    "area", "core_ack_id", "poc_delivery_id", "poc_execution_sha", "poc_closure_sha",
    "poc_publication_sha", "poc_evidence_id", "poc_manifest_locator", "poc_manifest_sha256",
    "poc_evidence_locator", "poc_evidence_sha256", "poc_machine_result", "user_waiver",
    "candidate_id", "pairing_revision", "classification", "inheritance_reason", "product_sha",
    "delta_test_id", "delta_result", "result_proof_kind", "result_locator", "portable_run_id",
    "acceptance_run_id",
}
FIXED = {
    "core_ack_id": "DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001",
    "poc_delivery_id": "POC-llm-DEL-2026-001-R3",
    "poc_execution_sha": "0c75536e6ee99b502c59438989ca852194648946",
    "poc_closure_sha": "5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae",
    "poc_publication_sha": "485bb2a7c07d86a09899f09358c744edd733f875",
    "poc_evidence_id": "G2B-PI-COMBINED-006",
    "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
    "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class InheritanceError(RuntimeError): pass


def local_resolver(locator: str) -> bytes:
    path = Path(locator)
    if not path.is_file() or path.is_symlink():
        raise InheritanceError("locator is missing or unsafe")
    return path.read_bytes()


def validate_rows(rows: Any, candidate_sha: str, *, resolver: Callable[[str], bytes] = local_resolver) -> list[dict[str, Any]]:
    if not SHA40.fullmatch(candidate_sha) or type(rows) is not list or not rows:
        raise InheritanceError("invalid inheritance identity")
    seen_areas: set[str] = set()
    seen_rows: set[tuple[str, str]] = set()
    area_ids: dict[str, set[str]] = {area: set() for area in AREAS}
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if type(raw) is not dict or set(raw) != ROW_FIELDS:
            raise InheritanceError(f"row {index} has missing or extra fields")
        if raw["area"] not in AREAS:
            raise InheritanceError("unknown area")
        area = raw["area"]
        seen_areas.add(area)
        if any(raw[name] != expected for name, expected in FIXED.items()):
            raise InheritanceError("immutable POC or candidate identity mismatch")
        test_id = raw["delta_test_id"]
        if raw["product_sha"] != candidate_sha or test_id not in TEST_IDS:
            raise InheritanceError("product SHA or delta Test ID mismatch")
        row_identity = (area, test_id)
        if row_identity in seen_rows:
            raise InheritanceError("duplicate area and delta Test ID row")
        seen_rows.add(row_identity)
        area_ids[area].add(test_id)
        if raw["classification"] not in {"inherit", "delta", "waiver"} or raw["delta_result"] not in {"PASS", "FAIL"}:
            raise InheritanceError("classification or final result is invalid")
        if type(raw["poc_machine_result"]) is not str or not raw["poc_machine_result"].strip():
            raise InheritanceError("POC machine result is invalid")
        if not str(raw["inheritance_reason"]).strip() or raw["inheritance_reason"] in {"沿用POC", "沿用 POC"}:
            raise InheritanceError("inheritance reason is not concrete")
        for prefix in ("poc_manifest", "poc_evidence"):
            digest = raw[f"{prefix}_sha256"]
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                raise InheritanceError("POC digest is invalid")
            if hashlib.sha256(resolver(raw[f"{prefix}_locator"])).hexdigest() != digest:
                raise InheritanceError("POC locator checksum mismatch")
        proof_kind = raw["result_proof_kind"]
        if proof_kind not in {"target_card", "lock_preflight_reconciliation", "portable_reconciliation"}:
            raise InheritanceError("proof kind is invalid")
        expected_proof_kind = (
            "lock_preflight_reconciliation" if test_id == "M4B-LOCK-001"
            else "target_card" if test_id in TARGET_CARD_IDS
            else "portable_reconciliation"
        )
        if proof_kind != expected_proof_kind:
            raise InheritanceError("proof kind does not match Test ID scope")
        try:
            proof = json.loads(resolver(raw["result_locator"]))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InheritanceError("result proof is invalid") from error
        proof_status = proof.get("status") if type(proof) is dict else None
        if type(proof) is not dict or proof.get("candidate_sha") != candidate_sha or proof.get("test_id") != test_id or type(proof_status) is not str or proof_status.upper() != raw["delta_result"]:
            raise InheritanceError("result proof binding mismatch")
        if proof_kind == "portable_reconciliation":
            if not raw["portable_run_id"] or raw["acceptance_run_id"] is not None or proof.get("run_id") != raw["portable_run_id"] or set(proof.get("python_minors", ())) != {"3.11", "3.12", "3.13"}:
                raise InheritanceError("portable reconciliation is incomplete")
        else:
            if not raw["acceptance_run_id"] or raw["portable_run_id"] is not None or proof.get("run_id") != raw["acceptance_run_id"]:
                raise InheritanceError("target reconciliation is incomplete")
        if area in {"P9", "P10B"} and (raw["poc_machine_result"] != "FAIL" or raw["classification"] != "waiver" or raw["user_waiver"] != "KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION"):
            raise InheritanceError("resident-retention waiver was rewritten")
        if area not in {"P9", "P10B"} and (raw["classification"] == "waiver" or raw["user_waiver"] is not None):
            raise InheritanceError("unexpected waiver outside resident-retention rows")
        result.append(dict(raw))
    if seen_areas != AREAS:
        raise InheritanceError("required P1-P12 areas are incomplete")
    for area, required_ids in AREA_REQUIRED_IDS.items():
        if not required_ids.issubset(area_ids[area]):
            raise InheritanceError("area-specific delta evidence is incomplete")
    return result


__all__ = [
    "AREAS", "AREA_REQUIRED_IDS", "FIXED", "InheritanceError", "ROW_FIELDS",
    "TARGET_CARD_IDS", "TEST_IDS", "validate_rows",
]
