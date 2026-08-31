"""Pure ``snowboard.llm/1`` codec and exact structured-wire validation."""

from __future__ import annotations

import asyncio
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from sbd.adaptor.errors import AdapterError, AdapterRejected
from sbd.cognition.llm import LLMGenerationMetrics
from sbd.cognition.prompt_builder import ReasoningInput


PROTOCOL_VERSION = "snowboard.llm/1"
MAX_CONTROL_BYTES = 16 * 1024
MAX_REQUEST_ID_BYTES = 128
MAX_PERCEPTIONS = 16
MAX_PERCEPTION_CODEPOINTS = 4096

_REQUEST_ID = re.compile(r"^llm\.\d+\.\d+$")
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+$")
_PERCEPTION_ORDER = {"listen": 0, "read": 1, "look": 2}
_ACTION_ORDER = {"speak": 0, "tool": 1, "rest": 2}
_DIGEST_FIELDS = {"runtime_sha256", "model_sha256", "config_sha256"}
_IDENTITY_FIELDS = {
    "candidate_id",
    "pairing_revision",
    "platform",
    *_DIGEST_FIELDS,
}
_METRIC_FIELDS = {
    "init_ms",
    "ttft_ms",
    "prefill_tokens",
    "prefill_tokens_per_second",
    "decode_tokens",
    "decode_tokens_per_second",
    "kv_tokens",
}
_ERROR_STATES = {
    "BUSY": {"GENERATING"},
    "INVALID_REQUEST": {"READY", "GENERATING"},
    "TIMEOUT": {"READY"},
    "GENERATION_FAILED": {"READY"},
    "CANCEL_FAILED": {"FATAL"},
    "PROTOCOL_ERROR": {"FATAL"},
}


class LLMProtocolError(AdapterError):
    """Sanitized child-wire contract failure."""

    def __init__(self, *, stage: str, field: str, reason: str) -> None:
        self.stage = stage
        self.field = field
        self.reason = reason
        super().__init__(f"stage={stage} field={field} reason={reason}")


class ReasoningInputContractError(AdapterRejected):
    """Sanitized local semantic projection failure."""

    def __init__(self, *, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"field={field} reason={reason}")


class ReasoningInputTooLarge(AdapterRejected):
    """A locally valid private input exceeded a documented bound."""

    def __init__(self, *, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"field={field} reason={reason}")


@dataclass(frozen=True, slots=True)
class LLMReadyIdentity:
    candidate_id: str
    pairing_revision: str
    platform: str
    runtime_sha256: str
    model_sha256: str
    config_sha256: str


@dataclass(frozen=True, slots=True)
class LLMReady:
    identity: LLMReadyIdentity


@dataclass(frozen=True, slots=True)
class LLMWireResult:
    request_id: str
    response: Mapping[str, object]
    metrics: LLMGenerationMetrics


@dataclass(frozen=True, slots=True)
class LLMWireError:
    request_id: str
    code: Literal[
        "BUSY",
        "INVALID_REQUEST",
        "TIMEOUT",
        "GENERATION_FAILED",
        "CANCEL_FAILED",
        "PROTOCOL_ERROR",
    ]
    state: Literal["READY", "GENERATING", "FATAL"]


@dataclass(frozen=True, slots=True)
class LLMWireCancelled:
    request_id: str


def _fail(stage: str, field: str, reason: str) -> LLMProtocolError:
    return LLMProtocolError(stage=stage, field=field, reason=reason)


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    stage: str,
) -> None:
    if set(value) != expected:
        raise _fail(stage, "$", "missing or extra fields")


def _require_request_id(value: object, *, stage: str) -> str:
    if (
        type(value) is not str
        or len(value.encode("utf-8")) > MAX_REQUEST_ID_BYTES
        or _REQUEST_ID.fullmatch(value) is None
    ):
        raise _fail(stage, "request_id", "invalid identity")
    return value


def _require_digest(value: object, *, stage: str, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _fail(stage, field, "invalid sha256")
    return value


def _canonical_unique(
    values: tuple[str, ...],
    order: Mapping[str, int],
    *,
    field: str,
) -> list[str]:
    if any(type(value) is not str or value not in order for value in values):
        raise ReasoningInputContractError(field=field, reason="unknown member")
    if len(set(values)) != len(values):
        raise ReasoningInputContractError(field=field, reason="duplicate member")
    return sorted(values, key=order.__getitem__)


def _encode_tools(value: ReasoningInput) -> list[dict[str, object]]:
    tools: list[dict[str, object]] = []
    names: set[str] = set()
    for index, tool in enumerate(value.tool_schemas):
        field = f"input.capabilities.tools[{index}]"
        if type(tool) is not dict or set(tool) != {
            "name", "description", "input_schema",
        }:
            raise ReasoningInputContractError(field=field, reason="invalid fields")
        name = tool["name"]
        description = tool["description"]
        schema = tool["input_schema"]
        if type(name) is not str or _TOOL_NAME.fullmatch(name) is None:
            raise ReasoningInputContractError(field=f"{field}.name", reason="invalid dotted name")
        if name in names:
            raise ReasoningInputContractError(field=f"{field}.name", reason="duplicate name")
        if type(description) is not str or not description.strip():
            raise ReasoningInputContractError(field=f"{field}.description", reason="blank")
        if (
            type(schema) is not dict
            or schema.get("type") != "object"
            or type(schema.get("properties")) is not dict
            or schema.get("additionalProperties") is not False
        ):
            raise ReasoningInputContractError(field=f"{field}.input_schema", reason="not closed object")
        names.add(name)
        tools.append({
            "name": name,
            "description": description,
            "input_schema": schema,
        })
    return sorted(tools, key=lambda tool: str(tool["name"]))


def encode_reasoning_input(value: ReasoningInput) -> dict[str, object]:
    if not isinstance(value, ReasoningInput):
        raise ReasoningInputContractError(field="input", reason="wrong type")
    if len(value.perceptions) > MAX_PERCEPTIONS:
        raise ReasoningInputContractError(field="input.perceptions", reason="too many items")
    seen: set[str] = set()
    perceptions: list[dict[str, str]] = []
    for index, perception in enumerate(value.perceptions):
        field = f"input.perceptions[{index}]"
        if perception.kind not in _PERCEPTION_ORDER:
            raise ReasoningInputContractError(field=f"{field}.kind", reason="unknown member")
        if perception.kind in seen:
            raise ReasoningInputContractError(field=f"{field}.kind", reason="duplicate member")
        if perception.status not in {"ok", "timeout", "error"}:
            raise ReasoningInputContractError(field=f"{field}.status", reason="unknown member")
        text = "" if perception.text is None else perception.text
        if type(text) is not str:
            raise ReasoningInputContractError(field=f"{field}.text", reason="wrong type")
        if len(text) > MAX_PERCEPTION_CODEPOINTS:
            raise ReasoningInputTooLarge(field=f"{field}.text", reason="codepoint bound exceeded")
        seen.add(perception.kind)
        perceptions.append({"kind": perception.kind, "status": perception.status, "text": text})
    perceptions.sort(key=lambda item: _PERCEPTION_ORDER[item["kind"]])

    pending_count = value.pending_message_count
    if type(pending_count) is not int or pending_count < 0:
        raise ReasoningInputContractError(field="input.pending_message_count", reason="invalid count")
    available_perceptions = _canonical_unique(
        value.available_perceptions,
        _PERCEPTION_ORDER,
        field="input.capabilities.perceptions",
    )
    available_actions = _canonical_unique(
        value.available_actions,
        _ACTION_ORDER,
        field="input.capabilities.actions",
    )
    if "rest" not in available_actions:
        raise ReasoningInputContractError(field="input.capabilities.actions", reason="rest required")
    tools = _encode_tools(value)
    if ("tool" in available_actions) != bool(tools):
        raise ReasoningInputContractError(field="input.capabilities.tools", reason="tool/action mismatch")
    if not available_perceptions and ({"speak", "tool"} & set(available_actions)):
        raise ReasoningInputContractError(field="input.capabilities.actions", reason="perception required")
    return {
        "perceptions": perceptions,
        "pending_message_count": pending_count,
        "capabilities": {
            "perceptions": available_perceptions,
            "actions": available_actions,
            "tools": tools,
        },
    }


def encode_generate(request_id: str, value: ReasoningInput) -> dict[str, object]:
    request_id = _require_request_id(request_id, stage="GENERATE")
    frame: dict[str, object] = {
        "type": "GENERATE",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "input": encode_reasoning_input(value),
    }
    # Enforce the complete control-line bound before any writer sees private data.
    encode_frame(frame)
    return frame


def encode_cancel(request_id: str) -> dict[str, object]:
    return {
        "type": "CANCEL",
        "protocol_version": PROTOCOL_VERSION,
        "request_id": _require_request_id(request_id, stage="CANCEL"),
    }


def _validate_wire_reasoning_input(value: object) -> Mapping[str, object]:
    if type(value) is not dict or set(value) != {
        "perceptions", "pending_message_count", "capabilities",
    }:
        raise _fail("GENERATE", "input", "missing or extra fields")
    perceptions = value["perceptions"]
    if type(perceptions) is not list or len(perceptions) > MAX_PERCEPTIONS:
        raise _fail("GENERATE", "input.perceptions", "invalid array")
    seen_perceptions: set[str] = set()
    order: list[int] = []
    for index, perception in enumerate(perceptions):
        field = f"input.perceptions[{index}]"
        if type(perception) is not dict or set(perception) != {"kind", "status", "text"}:
            raise _fail("GENERATE", field, "missing or extra fields")
        kind = perception["kind"]
        status = perception["status"]
        text = perception["text"]
        if type(kind) is not str or kind not in _PERCEPTION_ORDER:
            raise _fail("GENERATE", f"{field}.kind", "unknown member")
        if kind in seen_perceptions:
            raise _fail("GENERATE", f"{field}.kind", "duplicate member")
        if type(status) is not str or status not in {"ok", "timeout", "error"}:
            raise _fail("GENERATE", f"{field}.status", "unknown member")
        if type(text) is not str or len(text) > MAX_PERCEPTION_CODEPOINTS:
            raise _fail("GENERATE", f"{field}.text", "invalid string bound")
        seen_perceptions.add(kind)
        order.append(_PERCEPTION_ORDER[kind])
    if order != sorted(order):
        raise _fail("GENERATE", "input.perceptions", "noncanonical order")

    pending_count = value["pending_message_count"]
    if type(pending_count) is not int or pending_count < 0:
        raise _fail("GENERATE", "input.pending_message_count", "invalid count")
    capabilities = value["capabilities"]
    if type(capabilities) is not dict or set(capabilities) != {
        "perceptions", "actions", "tools",
    }:
        raise _fail("GENERATE", "input.capabilities", "missing or extra fields")
    for field, member_order in (
        ("perceptions", _PERCEPTION_ORDER),
        ("actions", _ACTION_ORDER),
    ):
        members = capabilities[field]
        if type(members) is not list or any(type(item) is not str for item in members):
            raise _fail("GENERATE", f"input.capabilities.{field}", "invalid array")
        if len(set(members)) != len(members) or any(item not in member_order for item in members):
            raise _fail("GENERATE", f"input.capabilities.{field}", "unknown or duplicate member")
        if members != sorted(members, key=member_order.__getitem__):
            raise _fail("GENERATE", f"input.capabilities.{field}", "noncanonical order")
    actions = capabilities["actions"]
    if "rest" not in actions:
        raise _fail("GENERATE", "input.capabilities.actions", "rest required")
    tools = capabilities["tools"]
    if type(tools) is not list:
        raise _fail("GENERATE", "input.capabilities.tools", "invalid array")
    names: list[str] = []
    for index, tool in enumerate(tools):
        field = f"input.capabilities.tools[{index}]"
        if type(tool) is not dict or set(tool) != {"name", "description", "input_schema"}:
            raise _fail("GENERATE", field, "missing or extra fields")
        name = tool["name"]
        description = tool["description"]
        schema = tool["input_schema"]
        if type(name) is not str or _TOOL_NAME.fullmatch(name) is None:
            raise _fail("GENERATE", f"{field}.name", "invalid dotted name")
        if type(description) is not str or not description.strip():
            raise _fail("GENERATE", f"{field}.description", "blank")
        if (
            type(schema) is not dict
            or schema.get("type") != "object"
            or type(schema.get("properties")) is not dict
            or schema.get("additionalProperties") is not False
        ):
            raise _fail("GENERATE", f"{field}.input_schema", "not closed object")
        names.append(name)
    if len(set(names)) != len(names) or names != sorted(names):
        raise _fail("GENERATE", "input.capabilities.tools", "duplicate or noncanonical name")
    if ("tool" in actions) != bool(tools):
        raise _fail("GENERATE", "input.capabilities.tools", "tool/action mismatch")
    if not capabilities["perceptions"] and ({"speak", "tool"} & set(actions)):
        raise _fail("GENERATE", "input.capabilities.actions", "perception required")
    return value


def parse_generate(value: Mapping[str, object]) -> tuple[str, Mapping[str, object]]:
    _require_exact_keys(
        value,
        {"type", "protocol_version", "request_id", "input"},
        stage="GENERATE",
    )
    if value["type"] != "GENERATE" or value["protocol_version"] != PROTOCOL_VERSION:
        raise _fail("GENERATE", "$", "invalid type or protocol")
    request_id = _require_request_id(value["request_id"], stage="GENERATE")
    return request_id, _validate_wire_reasoning_input(value["input"])


def parse_cancel(value: Mapping[str, object]) -> str:
    _require_exact_keys(
        value,
        {"type", "protocol_version", "request_id"},
        stage="CANCEL",
    )
    if value["type"] != "CANCEL" or value["protocol_version"] != PROTOCOL_VERSION:
        raise _fail("CANCEL", "$", "invalid type or protocol")
    return _require_request_id(value["request_id"], stage="CANCEL")


def encode_frame(value: Mapping[str, object]) -> bytes:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as error:
        raise _fail("encode", "$", "not JSON encodable") from error
    if len(payload) > MAX_CONTROL_BYTES:
        raise ReasoningInputTooLarge(field="frame", reason="16 KiB bound exceeded")
    return payload


async def read_frame(reader: asyncio.StreamReader) -> dict[str, object]:
    try:
        raw = await reader.readuntil(b"\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as error:
        raise _fail("decode", "$", "stream ended or bound exceeded") from error
    if len(raw) > MAX_CONTROL_BYTES:
        raise _fail("decode", "$", "16 KiB bound exceeded")
    try:
        value = json.loads(raw[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _fail("decode", "$", "invalid UTF-8/JSON") from error
    if type(value) is not dict or value.get("protocol_version") != PROTOCOL_VERSION:
        raise _fail("decode", "protocol_version", "invalid protocol object")
    return value


def parse_ready(
    value: Mapping[str, object],
    *,
    expected_identity: LLMReadyIdentity,
) -> LLMReady:
    _require_exact_keys(value, {"type", "protocol_version", "state", "identity"}, stage="READY")
    if value["type"] != "READY" or value["protocol_version"] != PROTOCOL_VERSION or value["state"] != "READY":
        raise _fail("READY", "$", "invalid type, protocol, or state")
    identity = value["identity"]
    if type(identity) is not dict or set(identity) != _IDENTITY_FIELDS:
        raise _fail("READY", "identity", "missing or extra fields")
    decoded: dict[str, str] = {}
    for field in _IDENTITY_FIELDS:
        item = identity[field]
        if field in _DIGEST_FIELDS:
            decoded[field] = _require_digest(item, stage="READY", field=f"identity.{field}")
        elif type(item) is str and item:
            decoded[field] = item
        else:
            raise _fail("READY", f"identity.{field}", "invalid string")
        if decoded[field] != getattr(expected_identity, field):
            raise _fail("READY", f"identity.{field}", "identity mismatch")
    return LLMReady(LLMReadyIdentity(**decoded))


def _parse_metrics(value: object) -> LLMGenerationMetrics:
    if type(value) is not dict or set(value) != _METRIC_FIELDS:
        raise _fail("RESULT", "metrics", "missing or extra fields")
    numbers: dict[str, float | int] = {}
    for field in ("init_ms", "ttft_ms", "prefill_tokens_per_second", "decode_tokens_per_second"):
        item = value[field]
        if type(item) not in (int, float) or not math.isfinite(item):
            raise _fail("RESULT", f"metrics.{field}", "invalid finite number")
        if field.endswith("_per_second") and item <= 0:
            raise _fail("RESULT", f"metrics.{field}", "rate outside bound")
        if field.endswith("_ms") and item < 0:
            raise _fail("RESULT", f"metrics.{field}", "time outside bound")
        numbers[field] = float(item)
    for field, upper in (("prefill_tokens", 128), ("decode_tokens", 128), ("kv_tokens", 1024)):
        item = value[field]
        if type(item) is not int or not 1 <= item <= upper:
            raise _fail("RESULT", f"metrics.{field}", "token count outside bound")
        numbers[field] = item
    return LLMGenerationMetrics(**numbers)


def parse_terminal(
    value: Mapping[str, object],
    *,
    active_request_id: str,
) -> LLMWireResult | LLMWireError | LLMWireCancelled:
    _require_request_id(active_request_id, stage="terminal")
    frame_type = value.get("type")
    if frame_type == "RESULT":
        _require_exact_keys(
            value,
            {"type", "protocol_version", "request_id", "response", "metrics", "state"},
            stage="RESULT",
        )
        if value["protocol_version"] != PROTOCOL_VERSION or value["state"] != "READY":
            raise _fail("RESULT", "$", "invalid protocol or state")
        request_id = _require_request_id(value["request_id"], stage="RESULT")
        if request_id != active_request_id:
            raise _fail("RESULT", "request_id", "active identity mismatch")
        response = value["response"]
        if type(response) is not dict:
            raise _fail("RESULT", "response", "expected object")
        return LLMWireResult(request_id, response, _parse_metrics(value["metrics"]))
    if frame_type == "CANCELLED":
        _require_exact_keys(
            value,
            {"type", "protocol_version", "request_id", "state"},
            stage="CANCELLED",
        )
        if value["protocol_version"] != PROTOCOL_VERSION or value["state"] != "READY":
            raise _fail("CANCELLED", "$", "invalid protocol or state")
        request_id = _require_request_id(value["request_id"], stage="CANCELLED")
        if request_id != active_request_id:
            raise _fail("CANCELLED", "request_id", "active identity mismatch")
        return LLMWireCancelled(request_id)
    if frame_type == "ERROR":
        _require_exact_keys(
            value,
            {"type", "protocol_version", "request_id", "code", "state"},
            stage="ERROR",
        )
        if value["protocol_version"] != PROTOCOL_VERSION:
            raise _fail("ERROR", "protocol_version", "invalid protocol")
        request_id = _require_request_id(value["request_id"], stage="ERROR")
        if request_id != active_request_id:
            raise _fail("ERROR", "request_id", "active identity mismatch")
        code = value["code"]
        state = value["state"]
        if type(code) is not str or code not in _ERROR_STATES:
            raise _fail("ERROR", "code", "unknown code")
        if type(state) is not str or state not in _ERROR_STATES[code]:
            raise _fail("ERROR", "state", "illegal code/state pair")
        return LLMWireError(request_id, code, state)  # type: ignore[arg-type]
    raise _fail("terminal", "type", "unknown terminal")


__all__ = [
    "LLMProtocolError",
    "LLMReady",
    "LLMReadyIdentity",
    "LLMWireCancelled",
    "LLMWireError",
    "LLMWireResult",
    "MAX_CONTROL_BYTES",
    "PROTOCOL_VERSION",
    "ReasoningInputContractError",
    "ReasoningInputTooLarge",
    "encode_cancel",
    "encode_frame",
    "encode_generate",
    "encode_reasoning_input",
    "parse_ready",
    "parse_cancel",
    "parse_generate",
    "parse_terminal",
    "read_frame",
]
