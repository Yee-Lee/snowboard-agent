"""Read external-message perception worker."""

from __future__ import annotations

import asyncio

from sbd.core.event_bus import EventBus
from sbd.core.events import ErrorOccurred, PerceptionResult
from sbd.core.worker_runtime import WorkerRuntime
from sbd.input_events.external_message import ExternalMessageError, ReadMessageConsumer


class Read(WorkerRuntime):
    def __init__(self, *, consumer: ReadMessageConsumer, bus: EventBus) -> None:
        super().__init__()
        self._consumer = consumer
        self._bus = bus

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        await self.abort()

    async def perceive(
        self,
        session_id: str,
        turn_id: int,
        correlation_id: int,
        timeout_seconds: float,
    ) -> None:
        async def body() -> None:
            try:
                messages = await self._await_operation(
                    self._consumer.consume_for_read(
                        session_id=session_id,
                        turn_id=turn_id,
                        timeout_seconds=timeout_seconds,
                    )
                )
                if messages:
                    result = PerceptionResult(
                        "read",
                        "ok",
                        "\n".join(message.text for message in messages),
                        {
                            "message_ids": tuple(message.message_id for message in messages),
                            "channels": tuple(message.channel for message in messages),
                        },
                        session_id,
                        turn_id,
                        correlation_id,
                    )
                else:
                    result = PerceptionResult(
                        "read", "timeout", None, {},
                        session_id, turn_id, correlation_id,
                    )
            except ExternalMessageError:
                result = PerceptionResult(
                    "read", "error", None, {},
                    session_id, turn_id, correlation_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._bus.publish(
                    ErrorOccurred(
                        where="perception.read",
                        error="read worker failed",
                        exception_type=type(exc).__name__,
                    )
                )
                raise
            if self._may_publish():
                await self._bus.publish(result)

        await self._run_call(body)

    async def _abort_resources(self) -> None:
        pass
