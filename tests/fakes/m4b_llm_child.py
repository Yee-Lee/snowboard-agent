"""Deterministic structured-wire child seam for M4b portable tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from sbd.cognition.llm_child_protocol import (
    LLMProtocolError,
    LLMReadyIdentity,
    LLMWireCancelled,
    LLMWireError,
    LLMWireResult,
    encode_cancel,
    encode_generate,
    parse_terminal,
)
from sbd.cognition.prompt_builder import ReasoningInput


@dataclass(frozen=True, slots=True)
class ActiveRequest:
    request_id: str
    frame: Mapping[str, object]


class ScriptedLLMChild:
    """In-memory admission/state seam; it never imports the selected runtime."""

    def __init__(
        self,
        identity: LLMReadyIdentity,
        *,
        child_generation: int = 1,
    ) -> None:
        self.identity = identity
        self.child_generation = child_generation
        self.state = "STOPPED"
        self.counter = 0
        self.frames: list[dict[str, object]] = []
        self.inference_calls = 0
        self.native_cancel_calls = 0
        self.active: ActiveRequest | None = None
        self.terminals: list[LLMWireResult | LLMWireError | LLMWireCancelled] = []

    def set_state(self, state: str) -> None:
        self.state = state

    def admit(self, value: ReasoningInput) -> str:
        if self.state != "READY" or self.active is not None:
            raise LLMProtocolError(
                stage="admission",
                field="state",
                reason="operation requires READY",
            )
        self.counter += 1
        request_id = f"llm.{self.child_generation}.{self.counter}"
        frame = encode_generate(request_id, value)
        self.frames.append(frame)
        self.inference_calls += 1
        self.active = ActiveRequest(request_id, frame)
        self.state = "GENERATING"
        return request_id

    def cancel(self) -> dict[str, object]:
        if self.state != "GENERATING" or self.active is None:
            raise LLMProtocolError(
                stage="CANCEL",
                field="state",
                reason="no active request",
            )
        frame = encode_cancel(self.active.request_id)
        self.frames.append(frame)
        self.native_cancel_calls += 1
        return frame

    def complete(
        self,
        value: Mapping[str, object],
    ) -> LLMWireResult | LLMWireError | LLMWireCancelled:
        if self.active is None:
            raise LLMProtocolError(
                stage="terminal",
                field="request_id",
                reason="no active request",
            )
        terminal = parse_terminal(value, active_request_id=self.active.request_id)
        self.terminals.append(terminal)
        self.active = None
        self.state = terminal.state if isinstance(terminal, LLMWireError) else "READY"
        return terminal


__all__ = ["ActiveRequest", "ScriptedLLMChild"]
