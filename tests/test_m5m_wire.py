"""M5M-WIRE-001 and M5M-REG-001: real source/buffer/read projection."""

import asyncio
import json
import logging

from sbd.core.event_bus import EventBus
from sbd.core.events import ExternalMessageArrived, PerceptionResult
from sbd.input_events.external_message import ExternalMessageSource
from sbd.input_events.mqtt import MQTTIngress
from sbd.core.config.models import MQTTConfig
from sbd.perception.read import Read


def _payload(event_id="evt-1", text="遠端連線已啟用。", status="success"):
    return json.dumps({"version": 1, "event_id": event_id,
        "kind": "application_result", "request_id": "req-1",
        "status": status, "text": text}, ensure_ascii=False).encode()


def test_m5m_wire_001_rejects_invalid_and_duplicate_then_reads_safe_fields(caplog):
    async def run():
        bus = EventBus()
        arrivals = []
        facts = []
        async def record_arrival(event):
            arrivals.append(event)
        async def record_fact(fact):
            facts.append(fact)
        bus.subscribe(ExternalMessageArrived, record_arrival)
        bus.subscribe(PerceptionResult, record_fact)
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_items=8, overflow_policy="drop_newest", max_read_batch=1)
        await source.start()
        ingress = MQTTIngress(config=MQTTConfig(), source=source)
        bad = [
            b'{"version":1,"version":1,"text":"RAW_SENTINEL","password":"SECRET_SENTINEL"}',
            _payload(text="   "),
            b" " * 2049,
            _payload(text="甲" * 33),
            _payload(text="wrong"),
        ]
        with caplog.at_level(logging.WARNING):
            for payload in bad[:4]:
                assert await ingress.ingest(ingress.topics.result, payload) is False
            assert await ingress.ingest(ingress.topics.notification, bad[4]) is False
        assert len(arrivals) == 0
        assert caplog.text.count("MQTT_INVALID_PAYLOAD") == 5
        assert await ingress.ingest(ingress.topics.result, _payload(text="甲" * 32))
        assert not await ingress.ingest(ingress.topics.result, _payload(text="甲" * 32))
        assert len(arrivals) == 1
        first = arrivals[0].message_id
        await source.control.assign_to_session(first, "session")
        await source.control.begin_read("session", 1)
        read = Read(consumer=source.consumer, bus=bus)
        await read.perceive("session", 1, 1, 1.0)
        assert len(facts) == 1
        assert facts[0].extra["messages"] == ({"kind": "application_result",
            "status": "success", "text": "甲" * 32},)
        assert "req-1" not in str(facts[0].extra)
        assert "evt-1" not in str(facts[0].extra)
        assert "甲" * 32 not in caplog.text
        assert "req-1" not in caplog.text
        assert "RAW_SENTINEL" not in caplog.text
        assert "SECRET_SENTINEL" not in caplog.text
        boundary = _payload(event_id="evt-2048", text="ok")
        boundary += b" " * (2048 - len(boundary))
        assert len(boundary) == 2048
        assert await ingress.ingest(ingress.topics.result, boundary)
        await source.stop()
    asyncio.run(run())


def test_m5m_reg_001_drop_newest_and_one_read_per_turn(caplog):
    async def run():
        bus = EventBus()
        arrivals = []
        async def record_arrival(event):
            arrivals.append(event)
        bus.subscribe(ExternalMessageArrived, record_arrival)
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_items=8, overflow_policy="drop_newest", max_read_batch=1)
        await source.start()
        ingress = MQTTIngress(config=MQTTConfig(), source=source)
        for index in range(8):
            assert await ingress.ingest(ingress.topics.result, _payload(f"evt-{index}"))
        with caplog.at_level(logging.WARNING):
            assert not await ingress.ingest(ingress.topics.result, _payload("evt-8"))
        assert "EXTERNAL_MESSAGE_DROPPED" in caplog.text
        assert len(arrivals) == 8
        for arrival in arrivals:
            await source.control.mark_pending(arrival.message_id, "session")
        for turn in range(1, 9):
            selected = await source.control.begin_read("session", turn)
            assert selected == (arrivals[turn - 1].message_id,)
            messages = await source.consumer.consume_for_read(
                session_id="session", turn_id=turn, timeout_seconds=1)
            assert len(messages) == 1
        await source.stop()
    asyncio.run(run())
