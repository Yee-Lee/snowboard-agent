"""Reasoner — single cognition module and Ch 9 response normalizer."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Callable

from sbd.adaptor.errors import AdapterRejected, AdapterTimeout
from sbd.cognition.llm import LLMEngineAdapter
from sbd.cognition.llm_child_protocol import (
    ReasoningInputContractError,
    ReasoningInputTooLarge,
)
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, LLMResponse, PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.worker_runtime import WorkerRuntime


if TYPE_CHECKING:
    from sbd.action.payload_validator import ActionPayloadValidator


logger = logging.getLogger(__name__)
_PERCEPTION_KINDS = ("listen", "read", "look")
_ACTION_KINDS = ("speak", "tool")
_DEFAULT_PERCEPTIONS = ("listen",)
_REASON_TIMEOUT_SECONDS = 30.0
_APOLOGY = "抱歉，我現在無法完成回應，請再試一次。"


class Reasoner(WorkerRuntime):
    """Drive one stateless LLM turn and publish exactly one terminal Fact."""

    def __init__(
        self,
        llm: LLMEngineAdapter,
        prompt_builder: PromptBuilder,
        bus: EventBus,
        capability_of: Callable[[str], bool],
        action_validator: ActionPayloadValidator,
        reason_timeout_seconds: float = _REASON_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._bus = bus
        self._capability_of = capability_of
        self._action_validator = action_validator
        self._reason_timeout_seconds = reason_timeout_seconds

    async def start(self) -> None:
        await self._llm.start()

    async def stop(self) -> None:
        await self.abort()
        await self._llm.stop()

    async def abort(self) -> None:
        await super().abort()

    async def force_abort(self) -> ForceAbortReport:
        return await super().force_abort()

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[PerceptionResult, ...],
        pending_message_ids: tuple[str, ...],
    ) -> None:
        async def body() -> None:
            unexpected: Exception | None = None
            response: LLMResponse | None = None
            try:
                value = self._prompt_builder.build(
                    perceptions=perception_results,
                    pending_message_count=len(pending_message_ids),
                    available_perceptions=self._available(_PERCEPTION_KINDS),
                    available_actions=self._available(_ACTION_KINDS),
                )
                try:
                    async with asyncio.timeout(self._reason_timeout_seconds):
                        generation = await self._await_operation(
                            self._llm.generate(value)
                        )
                    response = self._normalize(
                        generation.response,
                        session_id,
                        turn_id,
                        correlation_id,
                    )
                except TimeoutError:
                    await self._llm.abort()
                    response = self._fallback(
                        session_id, turn_id, correlation_id
                    )
                except ReasoningInputContractError:
                    raise
                except (
                    ReasoningInputTooLarge,
                    AdapterRejected,
                    AdapterTimeout,
                    ValueError,
                    TypeError,
                ):
                    response = self._fallback(
                        session_id, turn_id, correlation_id
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                unexpected = exc

            if unexpected is not None:
                await self._bus.publish(
                    ErrorOccurred(
                        where="cognition.reasoner",
                        error="reasoner failed",
                        exception_type=type(unexpected).__name__,
                    )
                )
                raise unexpected
            if response is not None and self._may_publish():
                await self._bus.publish(response)

        await self._run_call(body)

    def _normalize(
        self,
        raw: Mapping[str, object],
        session_id: str,
        turn_id: int,
        correlation_id: int,
    ) -> LLMResponse:
        if type(raw) is not dict or set(raw) != {
            "action_kind",
            "action_payload",
            "next_perceptions",
        }:
            logger.warning(
                "LLM response schema rejected path=$ reason=exact fields"
            )
            raise ValueError("invalid model response")
        action_kind = raw["action_kind"]
        payload = raw["action_payload"]
        requested = raw["next_perceptions"]
        if type(action_kind) is not str or type(payload) is not dict:
            raise ValueError("invalid model response")
        if type(requested) is not list or any(
            type(kind) is not str for kind in requested
        ):
            raise ValueError("invalid model response")
        if len(requested) != len(set(requested)):
            raise ValueError("duplicate next perception")
        self._action_validator.validate(action_kind, payload)
        if action_kind == "rest":
            if requested:
                raise ValueError("rest cannot request a perception")
            return LLMResponse(
                "rest", {}, (), session_id, turn_id, correlation_id
            )
        if action_kind not in _ACTION_KINDS or not self._capability_of(action_kind):
            raise ValueError("unavailable action")
        if not requested or any(not self._capability_of(kind) for kind in requested):
            raise ValueError("no available next perception")
        next_perceptions = tuple(requested)
        return LLMResponse(
            action_kind,
            payload,
            next_perceptions,
            session_id,
            turn_id,
            correlation_id,
        )

    def _fallback(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
    ) -> LLMResponse:
        next_perceptions = self._dedupe_available(_DEFAULT_PERCEPTIONS)
        if self._capability_of("speak") and next_perceptions:
            payload = {"text": _APOLOGY}
            self._action_validator.validate("speak", payload)
            return LLMResponse(
                "speak",
                payload,
                next_perceptions,
                session_id,
                turn_id,
                correlation_id,
            )
        payload: dict[str, object] = {}
        self._action_validator.validate("rest", payload)
        return LLMResponse(
            "rest", payload, (), session_id, turn_id, correlation_id
        )

    def _available(self, kinds: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(kind for kind in kinds if self._capability_of(kind))

    def _dedupe_available(
        self,
        kinds: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        return tuple(
            kind
            for kind in kinds
            if kind not in seen
            and not seen.add(kind)
            and self._capability_of(kind)
        )

    async def _abort_resources(self) -> None:
        await self._llm.abort()

    async def _force_abort_resources(self) -> ForceAbortReport:
        return await self._llm.force_abort()
