"""Validated external-message InputSource and Signal publisher."""

from __future__ import annotations

import asyncio
import copy
import itertools
import logging
import time
from collections.abc import Callable, Mapping
from typing import Any, Literal

from sbd.action.payload_validator import validate_json_value
from sbd.core.event_bus import EventBus
from sbd.core.events import ExternalMessageArrived, new_message_id
from sbd.input_events.external_message.buffer import (
    ExternalMessageBuffer,
    ExternalMessageUnavailable,
    ExternalMessageValidationError,
)


class ExternalMessageSource:
    """Own the in-memory store and publish payload-free arrival signals."""

    def __init__(
        self,
        *,
        bus: EventBus,
        allowed_channels: frozenset[str],
        max_items: int = 32,
        overflow_policy: Literal["drop_oldest", "drop_newest", "reject"] = "drop_oldest",
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.monotonic,
        id_factory: Callable[[], str] = new_message_id,
    ) -> None:
        self._bus = bus
        self._allowed_channels = frozenset(allowed_channels)
        self._logger = logger or logging.getLogger(__name__)
        self._clock = clock
        self._id_factory = id_factory
        self._sequence = itertools.count()
        self._lifecycle_lock = asyncio.Lock()
        self._started = False
        self._stopped = False
        self._buffer = ExternalMessageBuffer(
            max_items=max_items,
            overflow_policy=overflow_policy,
            publish_signal=self._bus.publish,
            logger=self._logger,
        )

    @property
    def control(self) -> ExternalMessageBuffer:
        """Narrow StateManager control face."""
        return self._buffer

    @property
    def consumer(self) -> ExternalMessageBuffer:
        """Narrow ReadMessageConsumer face."""
        return self._buffer

    async def start(self) -> None:
        async with self._lifecycle_lock:
            if self._stopped:
                raise ExternalMessageUnavailable("external source cannot restart")
            self._started = True

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            if self._stopped:
                return
            self._started = False
            self._stopped = True
            await self._buffer.discard()

    def is_available(self) -> bool:
        return self._started and not self._stopped

    async def ingest(
        self,
        *,
        channel: str,
        text: str,
        metadata: Mapping[str, Any] | None = None,
        arrived_at: float | None = None,
    ) -> str:
        async with self._lifecycle_lock:
            if not self.is_available():
                raise ExternalMessageUnavailable("external source is unavailable")
            if channel not in self._allowed_channels:
                raise ExternalMessageValidationError(f"unknown channel: {channel}")
            normalized = self._validate(channel=channel, text=text, metadata=metadata)
            value = await self._buffer.store(
                channel=channel,
                arrived_at=self._clock() if arrived_at is None else arrived_at,
                text=text,
                metadata=normalized,
                id_factory=self._id_factory,
                sequence_factory=lambda: next(self._sequence),
            )
            await self._bus.publish(
                ExternalMessageArrived(
                    channel=value.channel,
                    arrived_at=value.arrived_at,
                    message_id=value.message_id,
                )
            )
            return value.message_id

    @staticmethod
    def _validate(
        *,
        channel: str,
        text: str,
        metadata: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if type(channel) is not str or not channel.strip():
            raise ExternalMessageValidationError("channel must be non-empty")
        if type(text) is not str or not text.strip():
            raise ExternalMessageValidationError("text must be non-empty")
        if metadata is None:
            return {}
        try:
            normalized = dict(metadata)
            validate_json_value(normalized, path="$.metadata")
            return copy.deepcopy(normalized)
        except Exception as exc:
            raise ExternalMessageValidationError(
                "metadata must be JSON-compatible"
            ) from exc
