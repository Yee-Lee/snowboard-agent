"""M2-MSG external-message buffer contract and race tests."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from sbd.core.event_bus import EventBus
from sbd.core.events import ExternalMessageArrived
from sbd.input_events.external_message import (
    ExternalMessageBufferFull,
    ExternalMessageDropped,
    ExternalMessageNotFound,
    ExternalMessageOwnershipError,
    ExternalMessageSource,
    ExternalMessageUnavailable,
    ExternalMessageValidationError,
)


def _source(
    *,
    max_items: int = 32,
    policy: str = "drop_oldest",
    ids: list[str] | None = None,
) -> tuple[ExternalMessageSource, list[ExternalMessageArrived]]:
    bus = EventBus()
    signals: list[ExternalMessageArrived] = []

    async def record(event: ExternalMessageArrived) -> None:
        signals.append(event)

    bus.subscribe(ExternalMessageArrived, record)
    kwargs = {}
    if ids is not None:
        kwargs["id_factory"] = lambda: ids.append(str(uuid.uuid4())) or ids[-1]
    source = ExternalMessageSource(
        bus=bus,
        max_items=max_items,
        overflow_policy=policy,
        **kwargs,
    )
    return source, signals


def test_m2_msg_001_store_precedes_signal_and_preserves_arrival_order() -> None:
    async def run() -> None:
        bus = EventBus()
        observed: list[str] = []
        source = ExternalMessageSource(bus=bus)

        async def assign_on_signal(event: ExternalMessageArrived) -> None:
            await source.control.assign_to_session(event.message_id, "session-a")
            observed.append(event.message_id)

        bus.subscribe(ExternalMessageArrived, assign_on_signal)
        await source.start()
        first = await source.ingest(
            channel="fixture",
            text="first",
            metadata={"nested": [1, True]},
            arrived_at=1.0,
        )
        second = await source.ingest(
            channel="fixture",
            text="second",
            arrived_at=2.0,
        )
        assert observed == [first, second]
        assert uuid.UUID(first).version == uuid.UUID(second).version == 4

        await source.control.mark_pending(first, "session-a")
        await source.control.mark_pending(second, "session-a")
        assert await source.control.pending_ids("session-a") == (first, second)
        assert await source.control.begin_read("session-a", 1) == (first, second)
        messages = await source.consumer.consume_for_read(
            session_id="session-a", turn_id=1, timeout_seconds=1.0
        )
        assert tuple(message.text for message in messages) == ("first", "second")
        assert messages[0].metadata == {"nested": [1, True]}
        with pytest.raises(ExternalMessageNotFound):
            await source.control.assign_to_session(first, "session-a")
        await source.stop()

    asyncio.run(run())


def test_m2_msg_001_invalid_input_allocates_no_id_or_signal() -> None:
    async def run() -> None:
        ids: list[str] = []
        source, signals = _source(ids=ids)
        await source.start()
        invalid = (
            {"channel": "fixture", "text": " "},
            {"channel": "", "text": "message"},
            {"channel": "fixture", "text": "message", "metadata": {"bad": b"x"}},
        )
        for payload in invalid:
            with pytest.raises(ExternalMessageValidationError):
                await source.ingest(**payload)
        assert ids == []
        assert signals == []
        await source.stop()

    asyncio.run(run())


def test_m2_msg_002_read_window_is_atomic_and_late_arrival_stays_pending() -> None:
    async def run() -> None:
        source, _ = _source()
        await source.start()
        first = await source.ingest(channel="fixture", text="first")
        await source.control.assign_to_session(first, "session-a")
        assert await source.control.begin_read("session-a", 7) == (first,)
        consumed = await source.consumer.consume_for_read(
            session_id="session-a", turn_id=7, timeout_seconds=1.0
        )
        assert tuple(item.message_id for item in consumed) == (first,)

        late = await source.ingest(channel="fixture", text="late")
        await source.control.assign_to_turn(late, "session-a", 7)
        assert await source.control.pending_ids("session-a") == (late,)
        assert await source.consumer.consume_for_read(
            session_id="session-a", turn_id=7, timeout_seconds=1.0
        ) == ()
        await source.stop()

    asyncio.run(run())


def test_m2_msg_002_cancel_timeout_discard_and_notify_before_wait_restore() -> None:
    async def run() -> None:
        source, _ = _source()
        await source.start()

        before = await source.ingest(channel="fixture", text="already assigned")
        await source.control.assign_to_session(before, "notify-session")
        await source.control.begin_read("notify-session", 1)
        immediate = await source.consumer.consume_for_read(
            session_id="notify-session", turn_id=1, timeout_seconds=1.0
        )
        assert tuple(item.message_id for item in immediate) == (before,)

        timed = await source.ingest(channel="fixture", text="timeout restore")
        await source.control.assign_to_session(timed, "timeout-session")
        await source.control.begin_read("timeout-session", 2)
        await source.control.close_read("timeout-session", 2)
        assert await source.control.pending_ids("timeout-session") == (timed,)

        await source.control.begin_read("cancel-session", 3)
        entered = asyncio.Event()

        async def consume() -> tuple:
            entered.set()
            return await source.consumer.consume_for_read(
                session_id="cancel-session", turn_id=3, timeout_seconds=60.0
            )

        task = asyncio.create_task(consume())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await source.control.close_read("cancel-session", 3)

        await source.control.begin_read("discard-session", 4)
        discard_entered = asyncio.Event()
        async def wait_for_discard() -> tuple:
            discard_entered.set()
            return await source.consumer.consume_for_read(
                session_id="discard-session", turn_id=4, timeout_seconds=60.0
            )
        waiting = asyncio.create_task(wait_for_discard())
        await discard_entered.wait()
        await source.control.discard()
        assert await waiting == ()
        await source.stop()

    asyncio.run(run())


@pytest.mark.parametrize("policy,error", [
    ("drop_newest", ExternalMessageDropped),
    ("reject", ExternalMessageBufferFull),
])
def test_m2_msg_004_rejected_newest_allocates_no_id_or_signal(policy, error) -> None:
    async def run() -> None:
        ids: list[str] = []
        source, signals = _source(max_items=1, policy=policy, ids=ids)
        await source.start()
        first = await source.ingest(channel="fixture", text="first")
        with pytest.raises(error):
            await source.ingest(channel="fixture", text="second")
        assert ids == [first]
        assert tuple(signal.message_id for signal in signals) == (first,)
        await source.stop()

    asyncio.run(run())


def test_m2_msg_004_drop_oldest_never_evicts_turn_owned_item() -> None:
    async def run() -> None:
        ids: list[str] = []
        source, signals = _source(max_items=1, ids=ids)
        await source.start()
        first = await source.ingest(channel="fixture", text="first")
        await source.control.assign_to_session(first, "session-a")
        await source.control.begin_read("session-a", 1)
        with pytest.raises(ExternalMessageDropped) as captured:
            await source.ingest(channel="fixture", text="second")
        assert captured.value.policy == "drop_newest"
        assert ids == [first]
        assert tuple(signal.message_id for signal in signals) == (first,)
        consumed = await source.consumer.consume_for_read(
            session_id="session-a", turn_id=1, timeout_seconds=1.0
        )
        assert tuple(item.message_id for item in consumed) == (first,)
        await source.stop()

    asyncio.run(run())


def test_m2_msg_005_flush_reuses_ids_and_stop_converges_waiters() -> None:
    async def run() -> None:
        source, signals = _source()
        await source.start()
        first = await source.ingest(channel="fixture", text="first", arrived_at=1.0)
        second = await source.ingest(channel="fixture", text="second", arrived_at=2.0)
        await source.control.assign_to_session(first, "session-a")
        await source.control.mark_pending(first, "session-a")
        await source.control.assign_to_session(second, "session-a")
        signals.clear()
        await source.control.flush_to_wake()
        assert tuple(signal.message_id for signal in signals) == (first, second)
        assert tuple(signal.arrived_at for signal in signals) == (1.0, 2.0)

        await source.control.begin_read("stop-session", 9)
        stop_entered = asyncio.Event()
        async def wait_for_stop() -> tuple:
            stop_entered.set()
            return await source.consumer.consume_for_read(
                session_id="stop-session", turn_id=9, timeout_seconds=60.0
            )
        waiter = asyncio.create_task(wait_for_stop())
        await stop_entered.wait()
        await source.stop()
        assert await waiter == ()
        await source.stop()
        with pytest.raises(ExternalMessageUnavailable):
            await source.ingest(channel="fixture", text="after stop")

    asyncio.run(run())
