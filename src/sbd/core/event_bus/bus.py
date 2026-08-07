"""Event Bus implementation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NoReturn, TypeVar
import re

from sbd.core.events import (ActionCompleted, ButtonPressed, ErrorOccurred, Event,
    ExternalMessageArrived, InterruptRequested, LLMResponse, PerceptionResult,
    ShutdownRequested, StateChanged, WakeWordDetected)

E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], Awaitable[None]]

logger = logging.getLogger(__name__)


_CONCRETE_EVENT_KINDS = frozenset({PerceptionResult, LLMResponse, ActionCompleted,
    ErrorOccurred, StateChanged, ButtonPressed, ExternalMessageArrived,
    WakeWordDetected, InterruptRequested, ShutdownRequested})

def _handler_identity(handler: EventHandler[Event]) -> tuple[object, object]:
    return (getattr(handler, "__self__", None), getattr(handler, "__func__", handler))

def _safe_handler_name(handler: EventHandler[Event], supplied: str | None) -> str:
    raw = supplied or f"{handler.__module__}.{handler.__qualname__}"
    parts = []
    for part in raw.split("."):
        token = re.sub(r"[^a-z0-9_]+", "_", part.lower())
        token = re.sub(r"_+", "_", token).strip("_")
        token = token or "anonymous"
        if not ("a" <= token[0] <= "z"):
            token = f"handler_{token}"
        parts.append(token)
    return ".".join(parts)


@dataclass(frozen=True, slots=True, eq=False)
class Subscription:
    """Opaque identity token created by EventBus."""
    pass


class FatalDispatchError(RuntimeError):
    def __init__(
        self,
        *,
        event: ErrorOccurred,
        handler_name: str,
        root_cause: Exception,
    ) -> None:
        self.event = event
        self.event_type = type(event).__name__
        self.handler_name = handler_name
        self.root_cause = root_cause
        super().__init__(
            f"fatal dispatch: event={self.event_type} handler={handler_name}"
        )


@dataclass(frozen=True, slots=True)
class _SubscriptionRecord:
    token: Subscription
    kind: type[Event]
    handler: EventHandler[Event]
    name: str


@dataclass(frozen=True, slots=True)
class _HandlerFailure:
    record: _SubscriptionRecord
    exc: Exception


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[_SubscriptionRecord]] = {}
        self._by_token: dict[Subscription, _SubscriptionRecord] = {}

        self._fatal_error: FatalDispatchError | None = None
        self._fatal_ready: asyncio.Event = asyncio.Event()

    def subscribe(
        self,
        kind: type[E],
        handler: EventHandler[E],
        *,
        name: str | None = None,
    ) -> Subscription:
        if kind not in _CONCRETE_EVENT_KINDS:
            raise TypeError("subscribe() requires a concrete event dataclass")
        name = _safe_handler_name(handler, name)
        # Check for duplicate handler for the same kind
        kind_records = self._subscribers.setdefault(kind, [])
        for record in kind_records:
            if _handler_identity(record.handler) == _handler_identity(handler):
                raise ValueError(f"Duplicate handler for {kind.__name__}")

        token = Subscription()
        # The cast is needed because we store generic event types in _subscribers
        record = _SubscriptionRecord(
            token=token,
            kind=kind,
            handler=handler,  # type: ignore
            name=name,
        )

        kind_records.append(record)
        self._by_token[token] = record
        return token

    def unsubscribe(self, subscription: Subscription) -> None:
        record = self._by_token.pop(subscription, None)
        if record is None:
            return

        kind_records = self._subscribers.get(record.kind)
        if kind_records is not None:
            try:
                kind_records.remove(record)
                if not kind_records:
                    del self._subscribers[record.kind]
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        if self._fatal_error is not None:
            raise self._fatal_error

        event_type = type(event)
        snapshot = tuple(self._subscribers.get(event_type, ()))

        if not snapshot:
            logger.warning("No subscriber for event type: %s", event_type.__name__)
            return

        if isinstance(event, ErrorOccurred):
            await self._dispatch_error(event, snapshot)
        else:
            await self._dispatch_regular(event, snapshot)

    async def _dispatch_regular(
        self,
        event: Event,
        snapshot: tuple[_SubscriptionRecord, ...],
    ) -> None:
        failures: list[_HandlerFailure] = []

        for record in snapshot:
            try:
                await record.handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failures.append(_HandlerFailure(record, exc))

        # Fan-out complete. Now publish ErrorOccurred for any failures
        for failure in failures:
            error_event = ErrorOccurred(
                where=f"bus.dispatch.{failure.record.name}",
                error=repr(failure.exc),
                exception_type=type(failure.exc).__name__,
            )
            await self.publish(error_event)

    async def _dispatch_error(
        self,
        event: ErrorOccurred,
        snapshot: tuple[_SubscriptionRecord, ...],
    ) -> None:
        for record in snapshot:
            try:
                await record.handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Fatal! ErrorOccurred handler failed
                fatal = self._trip_fatal(event, record, exc)
                raise fatal from exc

    def _trip_fatal(
        self,
        event: ErrorOccurred,
        record: _SubscriptionRecord,
        cause: Exception,
    ) -> FatalDispatchError:
        fatal = FatalDispatchError(
            event=event,
            handler_name=record.name,
            root_cause=cause,
        )
        if self._fatal_error is None:
            self._fatal_error = fatal
            self._fatal_ready.set()
        return self._fatal_error

    async def wait_fatal(self) -> NoReturn:
        await self._fatal_ready.wait()
        # assert self._fatal_error is not None
        raise self._fatal_error  # type: ignore
