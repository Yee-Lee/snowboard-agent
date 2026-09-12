"""Strict private snowboard.llm/3 framing and shared state/proof ledger."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping
from sbd.adaptor.errors import AdapterRejected
from sbd.cognition.llm import GenerationMetrics, LLMFatalError

PROTOCOL_VERSION = "snowboard.llm/3"
TICKET_SCRUB_TEXT = "__M4B_TICKET_SCRUB__"
MAX_CONTROL_BYTES = 16 * 1024
CLOSE_REASONS = {"replace_context", "replace_generation_failure", "session_end", "interrupt", "error", "shutdown", "memory_pressure"}
FAILURE_CODES = {"INVALID_SEMANTIC", "GENERATION_REJECTED", "GENERATION_TIMEOUT"}
COUNTS = {"user_tokens", "current_kv_tokens", "rendered_incremental_tokens", "runtime_prefill_tokens", "output_reserve_tokens", "engine_context_tokens"}
METRICS = set(GenerationMetrics.__dataclass_fields__)
READY_FIELDS = {"protocol_name", "pid", "pgid", "candidate_id", "pairing_revision", "profile_id", "profile_stage", "profile_sha256", "runtime_sha256", "native_sha256", "model_sha256", "prompt_sha256", "grammar_sha256", "prompt_tokens", "max_output_tokens", "engine_context_tokens", "temperature", "top_p", "threads", "min_mem_available_generate_bytes", "min_mem_available_speak_bytes", "conversation_state", "network"}
COMMON = {"protocol", "request_id", "session_id", "generation"}


class LLMProtocolError(LLMFatalError):
    def __init__(self, *, stage: str = "wire", field: str = "$", reason: str = "invalid contract") -> None:
        self.stage, self.field, self.reason = stage, field, reason
        super().__init__(f"stage={stage} field={field} reason={reason}")


class ReasoningInputContractError(AdapterRejected):
    def __init__(self, *, field: str, reason: str) -> None:
        super().__init__(f"field={field} reason={reason}")


class ReasoningInputTooLarge(ReasoningInputContractError):
    pass


@dataclass(frozen=True, slots=True)
class LLMReadyIdentity:
    fields: Mapping[str, object]


def require(condition: bool, field: str = "$") -> None:
    if not condition:
        raise LLMProtocolError(field=field)


def exact(value: Mapping[str, object], keys: set[str]) -> None:
    require(set(value) == keys)


def uint(value: object, *, upper: int = 2**63 - 1) -> int:
    require(type(value) is int and 0 <= value <= upper, "number")
    return value  # type: ignore[return-value]


def digest(text: str) -> str:
    require(type(text) is str, "text")
    try:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeError:
        raise LLMProtocolError(field="text") from None


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def decode_frame(raw: bytes) -> dict[str, object]:
    require(bool(raw) and len(raw) <= MAX_CONTROL_BYTES and raw.endswith(b"\n"), "frame")
    try:
        value = json.loads(raw[:-1].decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(LLMProtocolError()))
    except (UnicodeError, ValueError, RecursionError):
        raise LLMProtocolError(field="frame") from None
    require(type(value) is dict and type(value.get("protocol")) is int and value["protocol"] == 3, "protocol")
    return value


def encode_frame(value: Mapping[str, object]) -> bytes:
    try:
        raw = json.dumps(dict(value), ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"
    except (TypeError, ValueError, UnicodeError):
        raise LLMProtocolError(field="frame") from None
    require(len(raw) <= MAX_CONTROL_BYTES, "frame")
    return raw


async def read_frame(reader: asyncio.StreamReader) -> dict[str, object]:
    try:
        return decode_frame(await reader.readuntil(b"\n"))
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        raise LLMProtocolError(field="frame") from None


def parse_ready(value: Mapping[str, object], *, expected_identity: LLMReadyIdentity | Mapping[str, object], pid: int, pgid: int) -> None:
    expected = dict(expected_identity.fields if isinstance(expected_identity, LLMReadyIdentity) else expected_identity)
    expected.update(pid=pid, pgid=pgid)
    exact(expected, READY_FIELDS)
    exact(value, READY_FIELDS | {"protocol", "event"})
    require(value["protocol"] == 3 and type(value["protocol"]) is int and value["event"] == "READY")
    require(pid == pgid and type(pid) is int and pid > 0, "pid")
    for key, item in expected.items():
        require(type(value[key]) is type(item) and value[key] == item, "identity")
    require(value["protocol_name"] == PROTOCOL_VERSION and value["conversation_state"] == "none" and value["network"] == "disabled")


def validate_counts(value: Mapping[str, object]) -> None:
    for name in COUNTS:
        uint(value[name])
    require(value["output_reserve_tokens"] == 128 and value["engine_context_tokens"] == 1024, "counts")
    require(value["current_kv_tokens"] <= 1024, "counts")
    require(value["user_tokens"] <= value["rendered_incremental_tokens"], "counts")
    require(value["runtime_prefill_tokens"] == value["rendered_incremental_tokens"], "counts")


class ProtocolLedger:
    """One claim/request/ticket. Private input text is never copied into the ledger."""
    def __init__(self, issued_tickets: set[str] | None = None) -> None:
        self.state = "ENGINE_READY"
        self.claim: tuple[str, int] | None = None
        self.revision = 0
        self.counter = 0
        self.active: dict[str, object] | None = None
        self.ticket: dict[str, object] | None = None
        self.consumed: dict[str, object] | None = None
        self.cancelled = False
        self.deferred = False
        self.fragments: list[str] = []
        self.fragment_times: list[int] = []
        self.issued_tickets = issued_tickets if issued_tickets is not None else set()

    def command(self, frame: Mapping[str, object]) -> None:
        require(type(frame.get("protocol")) is int and frame["protocol"] == 3)
        op = frame.get("op")
        if op == "CANCEL":
            exact(frame, {"protocol", "op", "request_id"})
            require(self.active is not None and not self.cancelled and type(frame["request_id"]) is int and frame["request_id"] == self.active["request_id"])
            require(self.active["op"] in {"OPEN", "MEASURE", "GENERATE", "CLOSE"}, "state")
            self.cancelled = True
            return
        if op == "SHUTDOWN":
            exact(frame, {"protocol", "op"})
            require(self.state == "ENGINE_READY" and self.active is None)
            self.state = "STOPPING"
            return
        require(self.active is None, "order")
        allowed = {"ENGINE_READY": {"OPEN"}, "CONVERSATION_READY": {"MEASURE", "CLOSE"}, "MEASURED": {"DISCARD_TICKET", "GENERATE", "CLOSE"}, "TAINTED": {"CLOSE"}}
        require(type(op) is str and op in allowed.get(self.state, set()), "state")
        extra = {"OPEN": set(), "MEASURE": {"text", "input_sha256", "output_reserve_tokens"}, "GENERATE": {"text", "input_sha256", "conversation_revision", "ticket"}, "DISCARD_TICKET": {"input_sha256", "conversation_revision", "ticket"}, "CLOSE": {"reason"}}[op]
        exact(frame, COMMON | {"op"} | extra)
        require(uint(frame["request_id"]) == self.counter + 1, "request_id")
        require(type(frame["session_id"]) is str and 0 < len(frame["session_id"]) <= 128, "identity")
        require(uint(frame["generation"]) > 0, "identity")
        identity = (frame["session_id"], frame["generation"])
        if op != "OPEN":
            require(identity == self.claim, "identity")
        if op in {"MEASURE", "GENERATE"}:
            require(frame["input_sha256"] == digest(frame["text"]), "digest")
        if op == "MEASURE":
            require(frame["output_reserve_tokens"] == 128 and type(frame["output_reserve_tokens"]) is int)
        if op in {"GENERATE", "DISCARD_TICKET"}:
            require(self.ticket is not None, "ticket")
            for key in ("ticket", "input_sha256", "conversation_revision", "session_id", "generation"):
                require(type(frame[key]) is type(self.ticket[key]) and frame[key] == self.ticket[key], "ticket")
            if op == "GENERATE":
                self.consumed, self.ticket = self.ticket, None
        if op == "CLOSE":
            require(type(frame["reason"]) is str and frame["reason"] in CLOSE_REASONS, "reason")
            self.ticket = self.consumed = None
        self.active = {key: item for key, item in frame.items() if key != "text"}
        self.counter += 1
        self.cancelled = self.deferred = False
        self.fragments.clear()
        self.fragment_times.clear()
        self.state = {"OPEN": "OPENING", "MEASURE": "MEASURING", "DISCARD_TICKET": "DISCARDING", "GENERATE": "GENERATING", "CLOSE": "CLOSING"}[op]

    def event(self, frame: Mapping[str, object]) -> bool:
        require(type(frame.get("protocol")) is int and frame["protocol"] == 3)
        event = frame.get("event")
        if event == "SHUTDOWN_ACK":
            exact(frame, {"protocol", "event"})
            require(self.state == "STOPPING")
            self.state = "STOPPED"
            return True
        active = self.active
        require(active is not None, "order")
        require(type(frame.get("request_id")) is int and frame["request_id"] == active["request_id"], "request_id")
        op = active["op"]
        base = COMMON | {"event"}
        if event == "CANCEL_DEFERRED":
            exact(frame, {"protocol", "event", "request_id"})
            require(self.cancelled and not self.deferred)
            self.deferred = True
            return False
        if event == "SAFE_TEXT":
            exact(frame, {"protocol", "event", "request_id", "sequence", "text", "monotonic_ns"})
            require(op == "GENERATE" and uint(frame["sequence"]) == len(self.fragments))
            require(type(frame["text"]) is str and bool(frame["text"]))
            require(sum(len(fragment.encode("utf-8")) for fragment in self.fragments) + len(frame["text"].encode("utf-8")) <= MAX_CONTROL_BYTES, "fragments")
            instant = uint(frame["monotonic_ns"])
            require(not self.fragment_times or instant >= self.fragment_times[-1])
            self.fragments.append(frame["text"])
            self.fragment_times.append(instant)
            return False
        if event == "CANCELLED":
            exact(frame, {"protocol", "event", "request_id", "operation", "request_terminal_proven", "operation_cleanup_proven", "engine_usable", "conversation_state"})
            require(self.cancelled and frame["operation"] == op)
            require(all(frame[key] is True for key in ("request_terminal_proven", "operation_cleanup_proven", "engine_usable")), "proof")
            states = {"OPEN": ("none", "ENGINE_READY"), "MEASURE": ("ready", "CONVERSATION_READY"), "GENERATE": ("tainted", "TAINTED")}
            require(op in states, "proof")
            wire_state, self.state = states[op]
            require(frame["conversation_state"] == wire_state)
            self.ticket = self.consumed = None
        else:
            require(frame.get("session_id") == active["session_id"] and type(frame.get("generation")) is int and frame["generation"] == active["generation"], "identity")
            if event == "OPENED":
                exact(frame, base | {"conversation_revision"})
                require(op == "OPEN" and uint(frame["conversation_revision"]) == 0)
                self.claim = (active["session_id"], active["generation"])
                self.revision = 0
                self.state = "CONVERSATION_READY"
            elif event == "OPEN_REJECTED":
                exact(frame, base | {"code", "cleanup_proven", "engine_usable"})
                require(op == "OPEN" and frame["code"] == "OPEN_REJECTED")
                require(frame["cleanup_proven"] is True and frame["engine_usable"] is True, "proof")
                self.state = "ENGINE_READY"
            elif event == "MEASURED":
                exact(frame, base | COUNTS | {"conversation_revision", "input_sha256", "ticket"})
                require(op == "MEASURE" and uint(frame["conversation_revision"]) == self.revision)
                require(frame["input_sha256"] == active["input_sha256"])
                require(type(frame["ticket"]) is str and re.fullmatch(r"[0-9a-f]{32}", frame["ticket"]) is not None, "ticket")
                require(frame["ticket"] not in self.issued_tickets, "ticket")
                validate_counts(frame)
                self.issued_tickets.add(frame["ticket"])
                self.ticket = dict(frame)
                self.state = "MEASURED"
            elif event == "TICKET_DISCARDED":
                exact(frame, base | {"conversation_revision", "ticket", "input_sha256", "native_render_scrubbed", "ticket_invalidated", "private_input_erased", "conversation_state"})
                require(op == "DISCARD_TICKET", "state")
                for key in ("conversation_revision", "ticket", "input_sha256"):
                    require(type(frame[key]) is type(active[key]) and frame[key] == active[key], "ticket")
                require(all(frame[key] is True for key in ("native_render_scrubbed", "ticket_invalidated", "private_input_erased")), "proof")
                require(frame["conversation_state"] == "ready", "state")
                self.ticket = self.consumed = None
                self.state = "CONVERSATION_READY"
            elif event == "RESULT":
                exact(frame, base | METRICS | {"conversation_revision", "text", "end"})
                require(op == "GENERATE" and uint(frame["conversation_revision"]) == self.revision + 1)
                from sbd.cognition.semantic import validate_semantic
                result = validate_semantic({"text": frame["text"], "end": frame["end"]})
                require(result.text == frame["text"] and result.text.startswith("".join(self.fragments)), "prefix")
                for name in METRICS - {"first_safe_text_monotonic_ns"}:
                    uint(frame[name])
                require(self.consumed is not None)
                for name in COUNTS - {"output_reserve_tokens", "engine_context_tokens"}:
                    require(frame[name] == self.consumed[name], "metrics")
                require(frame["decode_tokens"] <= 128 and frame["conversation_kv_tokens"] <= 1024, "metrics")
                prefilled = frame["current_kv_tokens"] + frame["runtime_prefill_tokens"]
                require(prefilled <= frame["conversation_kv_tokens"] <= prefilled + frame["decode_tokens"], "metrics")
                require(frame["llm_send_monotonic_ns"] <= frame["terminal_monotonic_ns"], "clock")
                first = frame["first_safe_text_monotonic_ns"]
                require(first == (self.fragment_times[0] if self.fragment_times else None), "clock")
                if self.fragment_times:
                    uint(first)
                    require(frame["llm_send_monotonic_ns"] <= self.fragment_times[0] <= self.fragment_times[-1] <= frame["terminal_monotonic_ns"], "clock")
                self.revision += 1
                self.consumed = None
                self.state = "CONVERSATION_READY"
            elif event == "REQUEST_FAILED":
                exact(frame, base | {"code", "request_terminal_proven", "engine_usable", "terminal_monotonic_ns"})
                require(op == "GENERATE" and type(frame["code"]) is str and frame["code"] in FAILURE_CODES)
                require(frame["request_terminal_proven"] is True and frame["engine_usable"] is True, "proof")
                uint(frame["terminal_monotonic_ns"])
                self.consumed = None
                self.state = "TAINTED"
            elif event == "CLOSED":
                exact(frame, base | {"request_terminal_proven", "cleanup_proven", "engine_usable"})
                require(op == "CLOSE")
                require(all(frame[key] is True for key in ("request_terminal_proven", "cleanup_proven", "engine_usable")), "proof")
                self.claim = self.ticket = self.consumed = None
                self.fragments.clear()
                self.state = "ENGINE_READY"
            else:
                raise LLMProtocolError(field="event")
        self.active = None
        return True
