"""M4B-PRIV-001 — scanner and sanitized protocol failures."""

from __future__ import annotations

from scripts.m4b_target_metrics import privacy_hits
from sbd.cognition.llm_child_protocol import LLMProtocolError


def test_m4b_priv_001_scanner_detects_private_prompt_response_and_credentials() -> None:
    sentinels = ("PRIVATE_PROMPT", "PRIVATE_RESPONSE", b"PRIVATE_CREDENTIAL")
    blobs = [("one", b"PRIVATE_PROMPT"), ("two", b"PRIVATE_CREDENTIAL"), ("clean", b'{"status":"Pass"}')]
    assert privacy_hits(blobs, sentinels) == ["one", "two"]


def test_m4b_priv_001_protocol_exception_has_only_sanitized_fields() -> None:
    error = LLMProtocolError(stage="RESULT", field="response", reason="invalid")
    assert str(error) == "stage=RESULT field=response reason=invalid"
