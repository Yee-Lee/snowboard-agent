"""Minimum listen-only Reasoner reference for the M4B-MVA POC.

This module owns product-envelope projection and action policy.  It deliberately
does not import a model runtime or the product composition root.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Protocol, Sequence

from poc_llm.harness.mva_contract import (
    ContractViolation,
    admit_tokens,
    reasoner_projection,
    validate_semantic,
    validate_session_facts,
)


class ReasonerCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    NO_ACTIONABLE_INPUT = "NO_ACTIONABLE_INPUT"
    UNSUPPORTED_PERCEPTION = "UNSUPPORTED_PERCEPTION"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    CONTEXT_LIMIT = "CONTEXT_LIMIT"
    INVALID_OUTPUT = "INVALID_OUTPUT"


class ReasonerError(ValueError):
    """Typed failure at the POC Reasoner boundary."""

    def __init__(self, code: ReasonerCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail


class PerceptionProjector(Protocol):
    kind: str

    def project(self, perception: Mapping[str, object]) -> str:
        """Return normalized model-facing text or raise a typed error."""


@dataclass(frozen=True)
class ListenProjector:
    kind: str = "listen"
    maximum_codepoints: int = 20

    def project(self, perception: Mapping[str, object]) -> str:
        if set(perception) != {"kind", "status", "text"}:
            raise ReasonerError(ReasonerCode.INVALID_INPUT, "listen fields are not exact")
        if perception.get("status") != "ok":
            raise ReasonerError(ReasonerCode.NO_ACTIONABLE_INPUT, "listen status is not ok")
        text = perception.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ReasonerError(ReasonerCode.NO_ACTIONABLE_INPUT, "listen text is blank")
        if len(text) > self.maximum_codepoints:
            raise ReasonerError(ReasonerCode.INPUT_TOO_LARGE, "listen text exceeds 20 codepoints")
        return text


@dataclass(frozen=True)
class ProjectedTurn:
    user_text: str


@dataclass(frozen=True)
class AdmittedTurn:
    user_text: str
    rendered_user: str
    new_user_tokens: int
    rendered_tokens: int
    rendered_input_tier: str


class ListenReasoner:
    """A small executable reference with an explicit future projector seam."""

    def __init__(
        self,
        *,
        projectors: Sequence[PerceptionProjector] | None = None,
    ) -> None:
        selected = tuple(projectors or (ListenProjector(),))
        if not selected or any(not projector.kind for projector in selected):
            raise ValueError("at least one named projector is required")
        if len({projector.kind for projector in selected}) != len(selected):
            raise ValueError("projector kinds must be unique")
        self._projectors = {projector.kind: projector for projector in selected}

    def project_turn(self, facts: object, turn_input: object) -> ProjectedTurn:
        try:
            validate_session_facts(facts)
        except ContractViolation as error:
            raise ReasonerError(ReasonerCode.INVALID_INPUT, str(error)) from error
        if not isinstance(turn_input, dict) or set(turn_input) != {"perceptions"}:
            raise ReasonerError(ReasonerCode.INVALID_INPUT, "turn input fields are not exact")
        perceptions = turn_input["perceptions"]
        if not isinstance(perceptions, list) or len(perceptions) != 1:
            raise ReasonerError(
                ReasonerCode.INVALID_INPUT, "current listen path requires one perception")
        perception = perceptions[0]
        if not isinstance(perception, dict):
            raise ReasonerError(ReasonerCode.INVALID_INPUT, "perception must be an object")
        kind = perception.get("kind")
        if not isinstance(kind, str) or kind not in self._projectors:
            raise ReasonerError(
                ReasonerCode.UNSUPPORTED_PERCEPTION, "no projector for perception kind")
        return ProjectedTurn(self._projectors[kind].project(perception))

    def admit(
        self,
        projected: ProjectedTurn,
        *,
        tokenize: Callable[[str], Sequence[object]],
        render_for_conversation: Callable[[str], str],
        current_kv_tokens: int,
        output_reserve_tokens: int = 128,
        user_new_limit: int = 32,
        engine_kv_limit: int = 1024,
    ) -> AdmittedTurn:
        rendered_user = projected.user_text
        try:
            new_user_tokens = len(tokenize(projected.user_text))
            rendered_tokens = len(tokenize(render_for_conversation(rendered_user)))
            admit_tokens(
                new_user_tokens=new_user_tokens,
                incremental_tokens=rendered_tokens,
                current_kv_tokens=current_kv_tokens,
                output_reserve_tokens=output_reserve_tokens,
                user_new_limit=user_new_limit,
                engine_kv_limit=engine_kv_limit,
            )
        except ContractViolation as error:
            code = (ReasonerCode.INPUT_TOO_LARGE if str(error) == "INPUT_TOO_LARGE"
                    else ReasonerCode.CONTEXT_LIMIT if str(error) == "CONTEXT_LIMIT"
                    else ReasonerCode.INVALID_INPUT)
            raise ReasonerError(code, str(error)) from error
        return AdmittedTurn(
            user_text=projected.user_text,
            rendered_user=rendered_user,
            new_user_tokens=new_user_tokens,
            rendered_tokens=rendered_tokens,
            rendered_input_tier="prefill_128" if rendered_tokens <= 128 else "prefill_1024",
        )

    @staticmethod
    def project_generation(semantic: object) -> dict[str, object]:
        try:
            return reasoner_projection(validate_semantic(semantic))
        except ContractViolation as error:
            raise ReasonerError(ReasonerCode.INVALID_OUTPUT, str(error)) from error
