"""Linearizable in-memory external-message buffer."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from sbd.core.events import ExternalMessageArrived
from sbd.input_events.external_message.models import (
    ExternalMessage,
    _BufferedMessage,
    _ReadWindow,
)


class ExternalMessageError(RuntimeError):
    pass


class ExternalMessageUnavailable(ExternalMessageError):
    pass


class ExternalMessageBufferFull(ExternalMessageError):
    pass


class ExternalMessageDropped(ExternalMessageError):
    def __init__(self, *, policy: str) -> None:
        self.policy = policy
        super().__init__(f"external message dropped by {policy} policy")


class ExternalMessageNotFound(ExternalMessageError):
    pass


class ExternalMessageOwnershipError(ExternalMessageError):
    pass


class ExternalMessageValidationError(ValueError):
    pass


class ExternalMessageBuffer:
    """Own message ordering, session/turn ownership, and read windows."""

    def __init__(
        self,
        *,
        max_items: int,
        overflow_policy: Literal["drop_oldest", "drop_newest", "reject"],
        publish_signal: Callable[[ExternalMessageArrived], Awaitable[None]],
        logger: logging.Logger | None = None,
    ) -> None:
        if type(max_items) is not int or max_items <= 0:
            raise ValueError("max_items must be a positive integer")
        if overflow_policy not in {"drop_oldest", "drop_newest", "reject"}:
            raise ValueError("unknown overflow policy")
        self._max_items = max_items
        self._overflow_policy = overflow_policy
        self._publish_signal = publish_signal
        self._logger = logger or logging.getLogger(__name__)
        self._items: dict[str, _BufferedMessage] = {}
        self._order: deque[str] = deque()
        self._read_windows: dict[str, _ReadWindow] = {}
        self._lock = asyncio.Lock()
        self._changed = asyncio.Condition(self._lock)

    async def store(
        self,
        *,
        channel: str,
        arrived_at: float,
        text: str,
        metadata: dict[str, Any],
        id_factory: Callable[[], str],
        sequence_factory: Callable[[], int],
    ) -> ExternalMessage:
        """Accept and allocate identity atomically after overflow permits it."""
        async with self._changed:
            self._apply_overflow_locked()
            value = ExternalMessage(
                message_id=id_factory(),
                channel=channel,
                arrived_at=arrived_at,
                sequence=sequence_factory(),
                text=text,
                metadata=metadata,
            )
            self._items[value.message_id] = _BufferedMessage(value=value)
            self._order.append(value.message_id)
            self._changed.notify_all()
            return value

    async def assign_to_session(self, message_id: str, session_id: str) -> None:
        async with self._changed:
            item = self._item_locked(message_id)
            if item.state == "session" and item.session_id == session_id:
                return
            if item.state != "queued":
                raise ExternalMessageOwnershipError("message has another owner")
            item.state = "session"
            item.session_id = session_id
            item.turn_id = None
            self._changed.notify_all()

    async def mark_pending(self, message_id: str, session_id: str) -> None:
        async with self._changed:
            item = self._item_locked(message_id)
            if item.state == "pending" and item.session_id == session_id:
                return
            if item.state not in {"queued", "session"}:
                raise ExternalMessageOwnershipError("message has another owner")
            if item.session_id not in {None, session_id}:
                raise ExternalMessageOwnershipError("message belongs to another session")
            item.state = "pending"
            item.session_id = session_id
            item.turn_id = None
            self._changed.notify_all()

    async def assign_to_turn(
        self,
        message_id: str,
        session_id: str,
        turn_id: int,
    ) -> None:
        async with self._changed:
            item = self._item_locked(message_id)
            if (
                item.state == "turn"
                and item.session_id == session_id
                and item.turn_id == turn_id
            ):
                return
            if item.state not in {"queued", "session", "pending"}:
                raise ExternalMessageOwnershipError("message has another owner")
            if item.session_id not in {None, session_id}:
                raise ExternalMessageOwnershipError("message belongs to another session")
            window = self._read_windows.get(session_id)
            if window is None or window.turn_id != turn_id:
                raise ExternalMessageOwnershipError("read window does not exist")
            item.session_id = session_id
            if window.state == "active":
                item.state = "turn"
                item.turn_id = turn_id
            else:
                item.state = "pending"
                item.turn_id = None
            self._changed.notify_all()

    async def begin_read(self, session_id: str, turn_id: int) -> tuple[str, ...]:
        async with self._changed:
            previous = self._read_windows.get(session_id)
            if previous is not None and previous.state == "active":
                if previous.turn_id != turn_id:
                    raise ExternalMessageOwnershipError("session has an active read window")
            else:
                self._read_windows[session_id] = _ReadWindow(session_id, turn_id)
            for message_id in self._order:
                item = self._items[message_id]
                if (
                    item.session_id == session_id
                    and item.state in {"session", "pending"}
                ):
                    item.state = "turn"
                    item.turn_id = turn_id
            selected = self._matching_ids_locked(session_id, turn_id)
            self._changed.notify_all()
            return selected

    async def close_read(self, session_id: str, turn_id: int) -> None:
        async with self._changed:
            self._close_read_locked(session_id, turn_id)
            self._changed.notify_all()

    async def pending_ids(self, session_id: str) -> tuple[str, ...]:
        async with self._lock:
            return tuple(
                message_id
                for message_id in self._order
                if self._items[message_id].state == "pending"
                and self._items[message_id].session_id == session_id
            )

    async def consume_for_read(
        self,
        *,
        session_id: str,
        turn_id: int,
        timeout_seconds: float,
    ) -> tuple[ExternalMessage, ...]:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        try:
            async with asyncio.timeout(timeout_seconds):
                async with self._changed:
                    window = self._read_windows.get(session_id)
                    if window is None or window.turn_id != turn_id:
                        raise ExternalMessageOwnershipError(
                            "read window does not exist"
                        )
                    while (
                        not self._matching_ids_locked(session_id, turn_id)
                        and window.state == "active"
                    ):
                        await self._changed.wait()
                        window = self._read_windows.get(session_id)
                        if window is None or window.turn_id != turn_id:
                            return ()
                    ids = self._matching_ids_locked(session_id, turn_id)
                    if not ids:
                        return ()
                    values = tuple(self._items[message_id].value for message_id in ids)
                    self._delete_locked(ids)
                    window.state = "closed"
                    self._changed.notify_all()
                    return values
        except TimeoutError:
            await self._restore_after_read(session_id, turn_id)
            return ()
        except asyncio.CancelledError:
            cleanup = asyncio.create_task(
                self._restore_after_read(session_id, turn_id)
            )
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    continue
            cleanup.result()
            raise

    async def flush_to_wake(self) -> None:
        async with self._changed:
            snapshot: list[ExternalMessageArrived] = []
            for message_id in self._order:
                item = self._items[message_id]
                item.state = "queued"
                item.session_id = None
                item.turn_id = None
                snapshot.append(
                    ExternalMessageArrived(
                        channel=item.value.channel,
                        arrived_at=item.value.arrived_at,
                        message_id=item.value.message_id,
                    )
                )
            self._read_windows.clear()
            self._changed.notify_all()
        for signal in snapshot:
            await self._publish_signal(signal)

    async def discard(self) -> None:
        async with self._changed:
            for window in self._read_windows.values():
                window.state = "closed"
            self._items.clear()
            self._order.clear()
            self._read_windows.clear()
            self._changed.notify_all()

    async def _restore_after_read(self, session_id: str, turn_id: int) -> None:
        async with self._changed:
            window = self._read_windows.get(session_id)
            if window is not None and window.turn_id == turn_id:
                self._close_read_locked(session_id, turn_id)
                self._changed.notify_all()

    def _apply_overflow_locked(self) -> None:
        if len(self._items) < self._max_items:
            return
        if self._overflow_policy == "reject":
            raise ExternalMessageBufferFull("external message buffer is full")
        if self._overflow_policy == "drop_newest":
            raise ExternalMessageDropped(policy="drop_newest")
        evict = next(
            (
                message_id
                for message_id in self._order
                if self._items[message_id].state != "turn"
            ),
            None,
        )
        if evict is None:
            raise ExternalMessageDropped(policy="drop_newest")
        item = self._items.pop(evict)
        self._order.remove(evict)
        self._logger.warning(
            "external message evicted id=%s channel=%s state=%s",
            item.value.message_id,
            item.value.channel,
            item.state,
        )

    def _item_locked(self, message_id: str) -> _BufferedMessage:
        try:
            return self._items[message_id]
        except KeyError as exc:
            raise ExternalMessageNotFound("external message not found") from exc

    def _matching_window_locked(self, session_id: str, turn_id: int) -> _ReadWindow:
        window = self._read_windows.get(session_id)
        if window is None or window.turn_id != turn_id:
            raise ExternalMessageOwnershipError("read window does not exist")
        return window

    def _matching_ids_locked(self, session_id: str, turn_id: int) -> tuple[str, ...]:
        return tuple(
            message_id
            for message_id in self._order
            if self._items[message_id].state == "turn"
            and self._items[message_id].session_id == session_id
            and self._items[message_id].turn_id == turn_id
        )

    def _close_read_locked(self, session_id: str, turn_id: int) -> None:
        window = self._matching_window_locked(session_id, turn_id)
        if window.state == "closed":
            return
        window.state = "closed"
        for message_id in self._matching_ids_locked(session_id, turn_id):
            item = self._items[message_id]
            item.state = "pending"
            item.turn_id = None

    def _delete_locked(self, message_ids: tuple[str, ...]) -> None:
        remove = set(message_ids)
        for message_id in remove:
            self._items.pop(message_id, None)
        self._order = deque(
            message_id for message_id in self._order if message_id not in remove
        )
