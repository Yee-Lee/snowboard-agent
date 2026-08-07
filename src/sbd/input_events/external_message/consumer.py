"""Narrow read-consumer view over the external-message buffer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sbd.input_events.external_message.models import ExternalMessage


@runtime_checkable
class ReadMessageConsumer(Protocol):
    async def consume_for_read(
        self,
        *,
        session_id: str,
        turn_id: int,
        timeout_seconds: float,
    ) -> tuple[ExternalMessage, ...]: ...
