"""M5M-SM-001: publish is exactly once, QoS 1, and honest about local outcome."""

import asyncio
import json
import uuid

from sbd.core.config.models import MQTTConfig
from sbd.input_events.mqtt import MQTTClient, MQTTSendError


def test_m5m_sm_001_publish_success_reject_and_timeout():
    async def run():
        class Info:
            def __init__(self, rc, published):
                self.rc = rc
                self.published = published
            def wait_for_publish(self, timeout):
                assert timeout == 2.0
            def is_published(self):
                return self.published

        class Transport:
            def __init__(self, info):
                self.info = info
                self.calls = []
            def is_connected(self):
                return True
            def publish(self, topic, *, payload, qos, retain):
                self.calls.append((topic, json.loads(payload), qos, retain))
                return self.info

        for rc, published, expected in ((0, True, None),
                                         (1, False, "MQTT_SEND_REJECTED"),
                                         (0, False, "MQTT_SEND_TIMEOUT")):
            client = MQTTClient(config=MQTTConfig(), ingress=object())
            transport = Transport(Info(rc, published))
            client._client = transport
            client._connected = True
            try:
                result = await client.publish_command()
            except MQTTSendError as exc:
                assert exc.code == expected
            else:
                assert expected is None
                assert uuid.UUID(result).version == 4
            assert len(transport.calls) == 1
            topic, payload, qos, retain = transport.calls[0]
            assert topic == "snowboard/dev-01/commands/remote-connection"
            assert set(payload) == {"version", "request_id", "command"}
            assert payload["version"] == 1
            assert payload["command"] == "enable_remote_connection"
            assert uuid.UUID(payload["request_id"]).version == 4
            assert (qos, retain) == (1, False)
    asyncio.run(run())


def test_m5m_net_001_old_client_callbacks_cannot_change_new_connection():
    async def run():
        client = MQTTClient(config=MQTTConfig(), ingress=object())
        transports = []
        second_started = asyncio.Event()

        class Transport:
            def connect(self, *_args):
                return None
            def loop_start(self):
                if len(transports) == 1:
                    client._emit(self, "connected")
                else:
                    client._emit(transports[0], "connected")
                    second_started.set()
            def disconnect(self):
                return None
            def loop_stop(self):
                return None
            def is_connected(self):
                return True

        def make_client():
            transport = Transport()
            transports.append(transport)
            return transport

        client._make_client = make_client
        await client.start()
        try:
            async with asyncio.timeout(3):
                while not client.is_connected():
                    await asyncio.sleep(0)
            client._emit(transports[0], "MQTT_BROKER_UNAVAILABLE")
            await asyncio.wait_for(second_started.wait(), timeout=3)
            await asyncio.sleep(0.05)
            assert not client.is_connected()
            client._emit(transports[1], "connected")
            async with asyncio.timeout(3):
                while not client.is_connected():
                    await asyncio.sleep(0)
            client._emit(transports[0], "MQTT_BROKER_UNAVAILABLE")
            await asyncio.sleep(0.05)
            assert client.is_connected()
        finally:
            await client.stop()

    asyncio.run(run())
