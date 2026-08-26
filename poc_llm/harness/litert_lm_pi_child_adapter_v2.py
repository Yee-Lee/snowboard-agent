#!/usr/bin/env python3
"""Pi adapter using a run-scoped, one-pass model authentication receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.litert_lm_child_adapter import Child, LiteRtBackend
from poc_llm.harness.litert_lm_pi_child_adapter import PiChild
from poc_llm.harness.pi_artifact_auth import streaming_digest, verify_model_receipt
from poc_llm.harness.pi_runtime import protocol_validator


def load_pi_config_v2(
    path: Path,
    expected_sha256: str,
    schema_path: Path,
    receipt_path: Path,
    receipt_sha256: str,
    receipt_schema_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = path.resolve()
    receipt_path = receipt_path.resolve()
    if not path.is_file() or streaming_digest(path) != expected_sha256:
        raise ValueError("Pi config identity mismatch")
    config = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if list(Draft202012Validator(schema).iter_errors(config)):
        raise ValueError("Pi strict config schema mismatch")
    if not receipt_path.is_file() or streaming_digest(receipt_path) != receipt_sha256:
        raise ValueError("Pi artifact receipt identity mismatch")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_schema = json.loads(receipt_schema_path.read_text(encoding="utf-8"))
    if list(Draft202012Validator(receipt_schema).iter_errors(receipt)):
        raise ValueError("Pi artifact receipt schema mismatch")
    if (
        receipt["candidate_id"] != config["candidate_id"]
        or receipt["runtime_sha256"] != config["runtime_sha256"]
        or receipt["model"]["sha256"] != config["model_sha256"]
    ):
        raise ValueError("Pi artifact receipt/config mismatch")
    verify_model_receipt(receipt["model"], Path(config["model_path"]), config["model_sha256"])
    return config, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--config-schema", type=Path, required=True)
    parser.add_argument("--config-schema-sha256", required=True)
    parser.add_argument("--protocol-schema", type=Path, required=True)
    parser.add_argument("--protocol-schema-sha256", required=True)
    parser.add_argument("--prompt-schema", type=Path, required=True)
    parser.add_argument("--prompt-schema-sha256", required=True)
    parser.add_argument("--response-schema", type=Path, required=True)
    parser.add_argument("--response-schema-sha256", required=True)
    parser.add_argument("--artifact-receipt", type=Path, required=True)
    parser.add_argument("--artifact-receipt-sha256", required=True)
    parser.add_argument("--artifact-receipt-schema", type=Path, required=True)
    parser.add_argument("--artifact-receipt-schema-sha256", required=True)
    args = parser.parse_args()
    try:
        for path, expected in (
            (args.config_schema, args.config_schema_sha256),
            (args.protocol_schema, args.protocol_schema_sha256),
            (args.prompt_schema, args.prompt_schema_sha256),
            (args.response_schema, args.response_schema_sha256),
            (args.artifact_receipt_schema, args.artifact_receipt_schema_sha256),
        ):
            if not path.is_file() or streaming_digest(path) != expected:
                raise ValueError("Pi schema identity mismatch")
        config, _receipt = load_pi_config_v2(
            args.config,
            args.config_sha256,
            args.config_schema,
            args.artifact_receipt,
            args.artifact_receipt_sha256,
            args.artifact_receipt_schema,
        )
        backend = LiteRtBackend(config)
        child: Child = PiChild(config, args.config_sha256, backend, sys.stdout)
        child.protocol = protocol_validator(
            args.protocol_schema,
            args.prompt_schema,
            args.response_schema,
        )
    except Exception:
        print("Pi adapter startup authentication failed", file=sys.stderr)
        return 2
    child.ready()
    try:
        for line in sys.stdin:
            try:
                frame = json.loads(line)
            except (json.JSONDecodeError, UnicodeError):
                break
            if not isinstance(frame, dict) or not child.handle(frame):
                break
    finally:
        child.close()
    return 0 if child.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
