from __future__ import annotations

from dataclasses import dataclass

import pytest

from sbd.core.event_bus import EventBus


@dataclass(frozen=True)
class Foo:
    value: int


@dataclass(frozen=True)
class Bar:
    label: str


async def test_publish_delivers_to_all_subscribers(bus: EventBus) -> None:
    received: list[int] = []

    async def handler_a(evt: Foo) -> None:
        received.append(evt.value * 1)

    async def handler_b(evt: Foo) -> None:
        received.append(evt.value * 10)

    bus.subscribe(Foo, handler_a)
    bus.subscribe(Foo, handler_b)

    await bus.publish(Foo(value=3))

    assert sorted(received) == [3, 30]


async def test_subscribers_are_keyed_by_type(bus: EventBus) -> None:
    foo_hits: list[Foo] = []
    bar_hits: list[Bar] = []

    async def on_foo(evt: Foo) -> None:
        foo_hits.append(evt)

    async def on_bar(evt: Bar) -> None:
        bar_hits.append(evt)

    bus.subscribe(Foo, on_foo)
    bus.subscribe(Bar, on_bar)

    await bus.publish(Foo(value=1))
    await bus.publish(Bar(label="x"))

    assert len(foo_hits) == 1 and len(bar_hits) == 1


async def test_handler_error_does_not_block_other_handlers(
    bus: EventBus, caplog: pytest.LogCaptureFixture
) -> None:
    good_calls: list[int] = []

    async def bad_handler(evt: Foo) -> None:
        raise RuntimeError("boom")

    async def good_handler(evt: Foo) -> None:
        good_calls.append(evt.value)

    bus.subscribe(Foo, bad_handler)
    bus.subscribe(Foo, good_handler)

    with caplog.at_level("ERROR"):
        await bus.publish(Foo(value=7))

    assert good_calls == [7]
    assert any("boom" in rec.message or "boom" in str(rec.exc_info) for rec in caplog.records)


async def test_unsubscribed_event_type_warns(
    bus: EventBus, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        await bus.publish(Foo(value=1))

    assert any("no subscriber" in rec.message for rec in caplog.records)


async def test_unsubscribe_removes_handler(bus: EventBus) -> None:
    calls: list[int] = []

    async def handler(evt: Foo) -> None:
        calls.append(evt.value)

    bus.subscribe(Foo, handler)
    await bus.publish(Foo(value=1))
    bus.unsubscribe(Foo, handler)
    await bus.publish(Foo(value=2))

    assert calls == [1]
