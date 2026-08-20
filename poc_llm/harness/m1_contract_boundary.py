#!/usr/bin/env python3
"""Callable reference boundary for the M1 PromptBuilder, P5, and identity contract."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "poc_llm/contracts/m1"
PERCEPTION_ORDER = {"listen": 0, "read": 1, "look": 2}
ACTION_ORDER = {"speak": 0, "tool": 1, "rest": 2}
TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
APOLOGY = {
    "action_kind": "speak",
    "action_payload": {"text": "Sorry, please try again."},
    "next_perceptions": ["listen"],
}
REST = {"action_kind": "rest", "action_payload": {}, "next_perceptions": []}


class BoundaryValidationError(ValueError):
    """Sanitized contract failure; never includes prompt, raw output, or payload."""


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validator(filename: str) -> Draft202012Validator:
    schema = load(CONTRACT_ROOT / filename)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _require_schema(value: Any, filename: str, label: str) -> None:
    errors = list(validator(filename).iter_errors(value))
    if errors:
        path = ".".join(str(item) for item in errors[0].path) or "$"
        raise BoundaryValidationError(f"{label} path={path} reason=schema")


def _validate_json_value(value: Any, depth: int = 0) -> None:
    if depth > 32:
        raise BoundaryValidationError("json path=$ reason=max-depth")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BoundaryValidationError("json path=$ reason=non-finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth + 1)
        return
    if type(value) is dict:
        if not all(isinstance(key, str) for key in value):
            raise BoundaryValidationError("json path=$ reason=non-string-key")
        for item in value.values():
            _validate_json_value(item, depth + 1)
        return
    raise BoundaryValidationError("json path=$ reason=unsupported-type")


def project_reasoning_input(reasoning_input: dict[str, Any]) -> dict[str, Any]:
    """Map Core ReasoningInput to the privacy-preserving child prompt projection."""
    _require_schema(reasoning_input, "reasoning-input.schema.json", "reasoning-input")
    for tool in reasoning_input["tool_schemas"]:
        try:
            Draft202012Validator.check_schema(tool["input_schema"])
        except SchemaError as error:
            raise BoundaryValidationError(
                "reasoning-input path=tool_schemas.input_schema reason=invalid-schema"
            ) from error
    perceptions = [
        {"kind": item["kind"], "status": item["status"], "text": item.get("text", "")}
        for item in reasoning_input["perceptions"]
    ]
    perceptions.sort(key=lambda item: (PERCEPTION_ORDER[item["kind"]], item["status"], item["text"]))
    tools = sorted(copy.deepcopy(reasoning_input["tool_schemas"]), key=lambda item: item["name"])
    projection = {
        "perceptions": perceptions,
        "pending_message_count": len(reasoning_input["pending_message_ids"]),
        "capabilities": {
            "perceptions": sorted(reasoning_input["available_perceptions"], key=PERCEPTION_ORDER.__getitem__),
            "actions": sorted(reasoning_input["available_actions"], key=ACTION_ORDER.__getitem__),
            "tools": tools,
        },
    }
    _require_schema(projection, "prompt-input.schema.json", "prompt-projection")
    return projection


def _fallback(prompt_projection: dict[str, Any]) -> dict[str, Any]:
    capabilities = prompt_projection["capabilities"]
    if "speak" in capabilities["actions"] and "listen" in capabilities["perceptions"]:
        return copy.deepcopy(APOLOGY)
    return copy.deepcopy(REST)


def normalize_response(
    raw_output: Any,
    prompt_projection: dict[str, Any],
    *,
    refused: bool = False,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Normalize untrusted model output without logging or executing a tool handler."""
    _require_schema(prompt_projection, "prompt-input.schema.json", "prompt-projection")
    diagnostic = "valid"
    try:
        if refused:
            raise BoundaryValidationError("response path=$ reason=refused")
        value = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        _validate_json_value(value)
        if type(value) is not dict:
            raise BoundaryValidationError("response path=$ reason=not-object")
        if isinstance(value.get("next_perceptions"), list):
            value = copy.deepcopy(value)
            value["next_perceptions"] = list(dict.fromkeys(value["next_perceptions"]))
        _require_schema(value, "response.schema.json", "response")
        capabilities = prompt_projection["capabilities"]
        if value["action_kind"] not in capabilities["actions"]:
            raise BoundaryValidationError("response path=action_kind reason=unavailable")
        if not set(value["next_perceptions"]).issubset(capabilities["perceptions"]):
            raise BoundaryValidationError("response path=next_perceptions reason=unavailable")
        if value["action_kind"] == "tool":
            tool_name = value["action_payload"]["name"]
            if not TOOL_NAME.fullmatch(tool_name):
                raise BoundaryValidationError("response path=action_payload.name reason=format")
            tools = {item["name"]: item for item in capabilities["tools"]}
            if tool_name not in tools:
                raise BoundaryValidationError("response path=action_payload.name reason=unknown")
            try:
                Draft202012Validator.check_schema(tools[tool_name]["input_schema"])
            except SchemaError as error:
                raise BoundaryValidationError(
                    "response path=action_payload.arguments reason=invalid-tool-schema"
                ) from error
            tool_validator = Draft202012Validator(tools[tool_name]["input_schema"])
            tool_errors = list(
                tool_validator.iter_errors(value["action_payload"]["arguments"])
            )
            if tool_errors:
                raise BoundaryValidationError("response path=action_payload.arguments reason=schema")
        return value, (diagnostic,)
    except (BoundaryValidationError, json.JSONDecodeError, TypeError, ValueError) as error:
        if isinstance(error, BoundaryValidationError):
            diagnostic = str(error)
        elif isinstance(error, json.JSONDecodeError):
            diagnostic = "response path=$ reason=malformed-json"
        else:
            diagnostic = "response path=$ reason=invalid"
        return _fallback(prompt_projection), (diagnostic,)


def _canonical_approved_path(value: str, label: str) -> str:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise BoundaryValidationError(f"identity path={label} reason=not-canonical")
    resolved = str(path.resolve(strict=False))
    if resolved != str(path):
        raise BoundaryValidationError(f"identity path={label} reason=alias")
    return resolved


def validate_identity(
    config: dict[str, Any],
    candidate: dict[str, Any],
    acquisition: dict[str, Any],
    ready_identity: dict[str, Any],
    *,
    config_sha256: str,
) -> None:
    """Bind strict config and READY to one approved candidate/acquisition platform identity."""
    _require_schema(config, "strict-config.schema.json", "strict-config")
    if (
        candidate["candidate_id"] != config["candidate_id"]
        or candidate["pairing_revision"] != config["pairing_revision"]
    ):
        raise BoundaryValidationError("identity path=candidate reason=mismatch")
    if (
        acquisition["candidate_id"] != config["candidate_id"]
        or acquisition["pairing_revision"] != config["pairing_revision"]
    ):
        raise BoundaryValidationError("identity path=acquisition reason=mismatch")
    platform = config["platform"]
    if platform not in acquisition["platforms"]:
        raise BoundaryValidationError("identity path=platform reason=unapproved")
    acquired = acquisition["platforms"][platform]["runtime_artifact"]
    runtime_path = _canonical_approved_path(config["runtime_path"], "runtime_path")
    model_path = _canonical_approved_path(config["model_path"], "model_path")
    if runtime_path != _canonical_approved_path(acquired["path"], "approved_runtime_path"):
        raise BoundaryValidationError("identity path=runtime_path reason=mismatch")
    if model_path != _canonical_approved_path(candidate["model"]["path"], "approved_model_path"):
        raise BoundaryValidationError("identity path=model_path reason=mismatch")
    if config["runtime_sha256"] != acquired["sha256"] or config["model_sha256"] != candidate["model"]["sha256"]:
        raise BoundaryValidationError("identity path=artifact_sha256 reason=mismatch")
    if candidate["config"]["sha256"] != config_sha256:
        raise BoundaryValidationError("identity path=config_sha256 reason=mismatch")
    expected_ready = {
        "candidate_id": config["candidate_id"],
        "pairing_revision": config["pairing_revision"],
        "platform": platform,
        "runtime_sha256": config["runtime_sha256"],
        "model_sha256": config["model_sha256"],
        "config_sha256": config_sha256,
    }
    if ready_identity != expected_ready:
        raise BoundaryValidationError("identity path=READY reason=drift")
