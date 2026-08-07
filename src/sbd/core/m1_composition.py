"""Pure-Python M1 bootstrap composition.

These deterministic workers exist only to exercise the M1 lifecycle,
supervision, and shutdown contracts.  Product mock/null backends remain M2.
"""
from __future__ import annotations

from typing import Any

from sbd.core.config.models import AppConfig
from sbd.core.event_bus import EventBus
from sbd.core.events import ActionCompleted, LLMResponse, PerceptionResult
from sbd.core.lifecycle import ForceAbortReport
from sbd.core.resource_manager import ResourceManager, ResourceSpec, StartPhase


class _M1Worker:
    def __init__(self, bus: EventBus, kind: str) -> None:
        self._bus = bus
        self._kind = kind

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def abort(self) -> None:
        return None

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        await self._bus.publish(PerceptionResult(
            self._kind,  # type: ignore[arg-type]
            "timeout",
            None,
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        ))

    async def reason(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        perception_results: tuple[Any, ...],
        pending_message_ids: tuple[str, ...],
    ) -> None:
        await self._bus.publish(LLMResponse(
            "rest",
            {},
            (),
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        ))

    async def execute(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        payload: dict[str, Any],
    ) -> None:
        await self._bus.publish(ActionCompleted(
            self._kind,  # type: ignore[arg-type]
            "ok",
            session_id=session_id,
            turn_id=turn_id,
            correlation_id=correlation_id,
        ))


def register_m1_resources(
    rm: ResourceManager,
    bus: EventBus,
    config: AppConfig,
) -> None:
    """Register a hardware/network-free graph for M1 process acceptance."""
    perception_policies = {
        "listen": config.perception.listen,
        "read": config.perception.read,
        "look": config.perception.look,
    }
    for kind, policy in perception_policies.items():
        if policy.enabled:
            rm.register(ResourceSpec(
                key=f"worker.perception.{kind}",  # type: ignore[arg-type]
                phase=StartPhase.WORKER,
                factory=lambda resolver, kind=kind: _M1Worker(bus, kind),
                required=policy.required,
                capability_kind=kind,  # type: ignore[arg-type]
            ))

    rm.register(ResourceSpec(
        key="worker.cognition.reasoner",  # type: ignore[arg-type]
        phase=StartPhase.WORKER,
        factory=lambda resolver: _M1Worker(bus, "reasoner"),
        required=True,
    ))

    action_policies = {
        "speak": config.action.speak,
        "tool": config.action.tool,
        "rest": config.action.rest,
    }
    for kind, policy in action_policies.items():
        if policy.enabled:
            rm.register(ResourceSpec(
                key=f"worker.action.{kind}",  # type: ignore[arg-type]
                phase=StartPhase.WORKER,
                factory=lambda resolver, kind=kind: _M1Worker(bus, kind),
                required=policy.required,
                capability_kind=kind if kind != "rest" else None,  # type: ignore[arg-type]
            ))
