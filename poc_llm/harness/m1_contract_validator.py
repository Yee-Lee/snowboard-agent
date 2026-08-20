#!/usr/bin/env python3
"""Validate the proposed M1 contract schemas, fixtures, and protocol lifecycle."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.m1_contract_boundary import (
    BoundaryValidationError,
    normalize_response,
    project_reasoning_input,
    validate_identity,
)

CONTRACT_ROOT = ROOT / "poc_llm/contracts/m1"
SCHEMAS = {
    "reasoning": CONTRACT_ROOT / "reasoning-input.schema.json",
    "prompt": CONTRACT_ROOT / "prompt-input.schema.json",
    "response": CONTRACT_ROOT / "response.schema.json",
    "protocol": CONTRACT_ROOT / "protocol-frame.schema.json",
    "config": CONTRACT_ROOT / "strict-config.schema.json",
}
FIXTURES = CONTRACT_ROOT / "contract-fixtures.json"
LOCK = CONTRACT_ROOT / "m1-contract-lock.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_validators() -> dict[str, Draft202012Validator]:
    """Build schema validators with the protocol's external references resolved."""
    schemas = {name: load(path) for name, path in SCHEMAS.items()}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    schema_store = {schema["$id"]: schema for schema in schemas.values()}
    validators = {
        name: Draft202012Validator(schema)
        for name, schema in schemas.items()
        if name != "protocol"
    }
    validators["protocol"] = Draft202012Validator(
        schemas["protocol"],
        resolver=RefResolver.from_schema(schemas["protocol"], store=schema_store),
    )
    return validators


def validate_sequence(frames: list[dict[str, Any]], protocol: Draft202012Validator) -> list[str]:
    errors: list[str] = []
    ready = False
    active: str | None = None
    shutting_down = False
    fatal = False
    pending_rejection: str | None = None
    terminal_ids: set[str] = set()
    for index, frame in enumerate(frames):
        schema_errors = sorted(protocol.iter_errors(frame), key=lambda error: list(error.path))
        if schema_errors:
            errors.append(f"frame {index} schema: {schema_errors[0].message}")
            continue
        if fatal:
            errors.append(f"frame {index}: frame after FATAL")
            continue
        frame_type = frame["type"]
        request_id = frame.get("request_id")
        if frame_type == "READY":
            if index != 0 or ready or active is not None or shutting_down:
                errors.append(f"frame {index}: unexpected READY")
            ready = True
        elif frame_type == "GENERATE":
            if fatal or shutting_down or request_id in terminal_ids or request_id == active:
                errors.append(f"frame {index}: GENERATE not accepted in current state")
            elif active is not None and pending_rejection is None:
                pending_rejection = request_id
            elif active is not None:
                errors.append(f"frame {index}: prior rejected request has no response")
            elif not ready:
                errors.append(f"frame {index}: GENERATE not accepted in current state")
            else:
                active = request_id
                ready = False
        elif frame_type == "CANCEL":
            if active != request_id:
                errors.append(f"frame {index}: CANCEL does not target active request")
        elif frame_type == "ERROR" and frame["code"] in {"BUSY", "INVALID_REQUEST"}:
            if frame["code"] == "BUSY":
                if pending_rejection != request_id or active is None or frame["state"] != "GENERATING":
                    errors.append(f"frame {index}: BUSY must reject only the pending second request")
                else:
                    pending_rejection = None
            else:
                expected_state = "GENERATING" if active is not None else "READY"
                if request_id == active or frame["state"] != expected_state:
                    errors.append(f"frame {index}: INVALID_REQUEST must be non-terminal")
                if request_id == pending_rejection:
                    pending_rejection = None
        elif frame_type in {"RESULT", "CANCELLED", "ERROR"}:
            if active != request_id:
                errors.append(f"frame {index}: terminal frame does not match active request")
            else:
                terminal_ids.add(request_id)
                active = None
                ready = frame.get("state", "READY") == "READY"
                fatal = frame.get("state") == "FATAL"
        elif frame_type == "SHUTDOWN":
            if not ready or active is not None or shutting_down or fatal:
                errors.append(f"frame {index}: SHUTDOWN requires idle READY")
            else:
                ready = False
                shutting_down = True
        elif frame_type == "SHUTDOWN_ACK":
            if not shutting_down:
                errors.append(f"frame {index}: SHUTDOWN_ACK without SHUTDOWN")
            shutting_down = False
    if pending_rejection is not None:
        errors.append("rejected request has no BUSY/INVALID_REQUEST response")
    if active is not None:
        errors.append("active request has no terminal outcome")
    if shutting_down:
        errors.append("SHUTDOWN has no acknowledgement")
    return errors


def validate_contract() -> dict[str, Any]:
    validators = make_validators()
    fixtures = load(FIXTURES)
    lock = load(LOCK)
    errors: list[str] = []

    for name, artifact in lock["artifacts"].items():
        path = ROOT / artifact["path"]
        if not path.is_file():
            errors.append(f"lock artifact {name} is missing")
        elif sha256(path) != artifact["sha256"]:
            errors.append(f"lock artifact {name} checksum mismatch")

    reasoning_input = fixtures["valid_reasoning_input"]
    for error in validators["reasoning"].iter_errors(reasoning_input):
        errors.append(f"valid reasoning input: {error.message}")
    prompt = project_reasoning_input(reasoning_input)
    if prompt != fixtures["valid_prompt"]:
        errors.append("ReasoningInput projection differs from frozen prompt fixture")
    for error in validators["prompt"].iter_errors(prompt):
        errors.append(f"valid prompt: {error.message}")
    for index, response in enumerate(fixtures["valid_responses"]):
        for error in validators["response"].iter_errors(response):
            errors.append(f"valid response {index}: {error.message}")
    for name, fallback in fixtures["p5_fallbacks"].items():
        for error in validators["response"].iter_errors(fallback):
            errors.append(f"fallback {name}: {error.message}")
    for error in validators["config"].iter_errors(fixtures["valid_config"]):
        errors.append(f"valid config: {error.message}")

    for case in fixtures["schema_negative_cases"]:
        if "value" in case:
            value = case["value"]
        elif case["target"] == "prompt":
            value = copy.deepcopy(prompt)
            value.update(case["mutation"])
        else:
            value = copy.deepcopy(fixtures["valid_config"])
            value.update(case["mutation"])
        if validators[case["target"]].is_valid(value):
            errors.append(f'{case["case_id"]}: negative schema case passed')

    for response in fixtures["valid_responses"]:
        normalized, diagnostics = normalize_response(response, prompt)
        if normalized != response or diagnostics != ("valid",):
            errors.append("valid response changed or failed through locked normalizer")

    identity = fixtures["valid_identity"]
    try:
        validate_identity(
            fixtures["valid_config"], identity["candidate"], identity["acquisition"], identity["ready"],
            config_sha256=identity["config_sha256"],
        )
    except BoundaryValidationError as error:
        errors.append(f"valid identity failed: {error}")

    for case in fixtures["valid_sequences"]:
        errors.extend(
            f'{case["case_id"]}: {error}'
            for error in validate_sequence(case["frames"], validators["protocol"])
        )
    for case in fixtures["invalid_sequences"]:
        if not validate_sequence(case["frames"], validators["protocol"]):
            errors.append(f'{case["case_id"]}: invalid lifecycle sequence passed')

    return {
        "contract_id": lock["contract_id"],
        "fixture_id": fixtures["fixture_id"],
        "fixture_sha256": sha256(FIXTURES),
        "lock_sha256": sha256(LOCK),
        "schema_sha256": {name: sha256(path) for name, path in SCHEMAS.items()},
        "schema_negative_cases": len(fixtures["schema_negative_cases"]),
        "valid_sequences": len(fixtures["valid_sequences"]),
        "invalid_sequences": len(fixtures["invalid_sequences"]),
        "result": "PASS" if not errors else "FAIL",
        "violations": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", required=True)
    parser.parse_args()
    report = validate_contract()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
