"""Minimal async pub/sub event bus.

Design goals (see docs/arch.md §4.5):
- Subscribers keyed by event type
- Handler errors are isolated: one failure does not affect other handlers
- Unknown/unsubscribed event types log a warning but do not raise
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, TypeVar

log = logging.getLogger(__name__)

E = TypeVar("E")
Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        self._subs[event_type].append(handler)  # type: ignore[arg-type]

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        if handler in self._subs.get(event_type, []):
            self._subs[event_type].remove(handler)  # type: ignore[arg-type]

    async def publish(self, event: Any) -> None:
        handlers = self._subs.get(type(event), [])
        if not handlers:
            log.warning("Event %s has no subscriber", type(event).__name__)
            return

        results = await asyncio.gather(
            *(self._safe_call(h, event) for h in handlers),
            return_exceptions=False,
        )
        del results

    async def _safe_call(self, handler: Handler, event: Any) -> None:
        try:
            await handler(event)
        except Exception:
            log.exception(
                "Handler %s raised while processing %s",
                getattr(handler, "__qualname__", repr(handler)),
                type(event).__name__,
            )
