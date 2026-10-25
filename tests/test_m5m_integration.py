"""M5M-PEER-001 / M5M-NET-001: MQTT 3.1.1 broker round trips."""

import asyncio
import socket
import ssl
import subprocess
import uuid
from dataclasses import replace
from pathlib import Path

from amqtt.broker import Broker
from argon2 import PasswordHasher

from sbd.core.config.models import MQTTConfig
from sbd.core.config.models import SecretValue
from sbd.core.event_bus import EventBus
from sbd.core.events import ExternalMessageArrived, PerceptionResult, ShutdownRequested
from sbd.input_events.external_message import ExternalMessageSource
from sbd.input_events.mqtt import MQTTClient, MQTTIngress, MQTTSendError
from sbd.input_events.mqtt.local_peer import LocalTestPeer
from sbd.action.tool.mqtt_command import MQTTCommandTool
from sbd.core.config.validate import validate_config
from tests.test_m5m_config import _mqtt_config
from tests.test_state_manager import make_sm, start_perception, wait
from sbd.perception.read import Read


def _broker_config(port):
    return {"listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
            "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True}}}


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _until(predicate, timeout=5.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.02)


def test_m5m_peer_001_real_broker_modes_and_notification():
    async def run():
        port = _free_port()
        broker = Broker(_broker_config(port))
        await broker.start()
        config = replace(MQTTConfig(), port=port)
        bus = EventBus()
        arrivals = []
        async def record(event):
            arrivals.append(event)
        bus.subscribe(ExternalMessageArrived, record)
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_items=8, overflow_policy="drop_newest", max_read_batch=1)
        ingress = MQTTIngress(config=config, source=source)
        client = MQTTClient(config=config, ingress=ingress)
        await source.start()
        await client.start()
        try:
            await _until(client.is_connected)
            for mode, delta in (("empty", 0), ("success", 1), ("failure", 1),
                                ("duplicate", 1), ("malformed", 0)):
                peer = LocalTestPeer(config=config, mode=mode)
                await peer.start()
                try:
                    before = len(arrivals)
                    if mode == "empty":
                        assert await MQTTCommandTool(client).handle(
                            {"message": "啟用遠端連線"}) == {}
                        request_id = None
                    else:
                        request_id = await client.publish_command()
                    await _until(lambda: len(peer.received_commands) == 1)
                    command = peer.received_commands[0]
                    assert command == {"version": 1,
                        "request_id": command["request_id"] if request_id is None else request_id,
                        "command": "enable_remote_connection"}
                    assert uuid.UUID(command["request_id"]).version == 4
                    if delta:
                        await _until(lambda: len(arrivals) == before + delta)
                        message_id = arrivals[-1].message_id
                        await source.control.assign_to_session(message_id, "session")
                        await source.control.begin_read("session", before + 1)
                        messages = await source.consumer.consume_for_read(
                            session_id="session", turn_id=before + 1,
                            timeout_seconds=1.0)
                        assert len(messages) == 1
                        assert messages[0].metadata["status"] == (
                            "failure" if mode == "failure" else "success")
                    else:
                        await asyncio.sleep(0.1)
                        assert len(arrivals) == before
                finally:
                    await peer.stop()
            peer = LocalTestPeer(config=config)
            await peer.start()
            try:
                before = len(arrivals)
                await peer.send_notification("服務即將維護。")
                await _until(lambda: len(arrivals) == before + 1)
                message_id = arrivals[-1].message_id
                await source.control.assign_to_session(message_id, "session")
                await source.control.begin_read("session", before + 1)
                messages = await source.consumer.consume_for_read(
                    session_id="session", turn_id=before + 1,
                    timeout_seconds=1.0)
                assert messages[0].metadata["status"] == "notice"
            finally:
                await peer.stop()
        finally:
            await client.stop()
            await source.stop()
            await broker.shutdown()
    asyncio.run(run())


def test_m5m_peer_001_broker_notification_reaches_idle_read_and_speak():
    async def run():
        port = _free_port()
        broker = Broker(_broker_config(port))
        await broker.start()
        config = replace(MQTTConfig(), port=port)
        bus, sm, listen, _, reasoner, _, speak = make_sm(
            action_kind="speak", action_payload={"text": "外部通知：服務維護。"},
            next_perceptions=("listen",))
        sm._mqtt_read_only = True
        listen.publish_fact = False
        listen.hold_after_fact = True
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}),
            max_read_batch=1)
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        observed, spoken = [], []
        async def record(fact):
            observed.append(fact)
        bus.subscribe(PerceptionResult, record)
        original_reason = reasoner.reason
        async def reason(*args, **kwargs):
            results = args[3]
            assert len(results) == 1 and results[0].kind == "read"
            assert results[0].extra["messages"] == ({
                "kind": "notification", "status": "notice", "text": "服務維護。"},)
            await original_reason(*args, **kwargs)
        reasoner.reason = reason
        original_speak = speak.execute
        async def execute(*args):
            spoken.append(args[-1]["text"])
            await original_speak(*args)
        speak.execute = execute
        ingress = MQTTIngress(config=config, source=source)
        client = MQTTClient(config=config, ingress=ingress)
        peer = LocalTestPeer(config=config)
        await source.start()
        await client.start()
        await sm.start()
        sm.set_conversation_lifecycle(sm._test_conversation_control)
        try:
            await _until(client.is_connected)
            await peer.start()
            await peer.send_notification("服務維護。")
            await _until(lambda: sm._session is not None)
            from sbd.core.state_manager.notices import _WakeAckElapsed
            sm._inbox.put_nowait(_WakeAckElapsed(sm._session.session_id))
            await wait(speak.started)
            assert [fact.kind for fact in observed] == ["read"]
            assert spoken == ["外部通知：服務維護。"]
            assert not listen.started.is_set()
            speak.release.set()
            await wait(listen.started)
        finally:
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await sm.stop()
            await client.stop()
            await source.stop()
            await peer.stop()
            await broker.shutdown()
    asyncio.run(run())


def test_m5m_net_001_disconnect_no_queue_and_reconnect():
    async def run():
        port = _free_port()
        broker = Broker(_broker_config(port))
        await broker.start()
        config = replace(MQTTConfig(), port=port)
        bus, sm, listen, _, _, _, speak = make_sm(
            action_kind="speak", action_payload={"text": "一般回答。"},
            next_perceptions=("listen",))
        sm._mqtt_read_only = True
        arrivals = []
        async def record(event):
            arrivals.append(event)
        bus.subscribe(ExternalMessageArrived, record)
        source = ExternalMessageSource(bus=bus, allowed_channels=frozenset({"mqtt"}))
        sm.set_external_message_control(source.control)
        sm._workers._perceptions["read"] = Read(consumer=source.consumer, bus=bus)
        ingress = MQTTIngress(config=config, source=source)
        client = MQTTClient(config=config, ingress=ingress)
        await source.start()
        await client.start()
        try:
            await _until(client.is_connected)
            await broker.shutdown()
            await _until(lambda: not client.is_connected())
            listen.publish_fact = True
            await start_perception(bus, sm, listen)
            await wait(speak.started)
            assert sm.state == "ACTION"
            await bus.publish(ShutdownRequested())
            await sm.wait_stopped()
            await sm.stop()
            try:
                await client.publish_command()
            except MQTTSendError as exc:
                assert exc.code == "MQTT_SEND_NOT_CONNECTED"
            else:
                assert False, "disconnected publish reported success"
            broker = Broker(_broker_config(port))
            await broker.start()
            await _until(client.is_connected, timeout=8.0)
            peer = LocalTestPeer(config=config, mode="empty")
            await peer.start()
            try:
                await peer.send_notification("重新連線後的通知。")
                await _until(lambda: len(arrivals) == 1)
                assert peer.received_commands == []
            finally:
                await peer.stop()
        finally:
            await client.stop()
            await source.stop()
            await broker.shutdown()
    asyncio.run(run())


def test_m5m_net_001_external_unavailable_does_not_fall_back_to_local_peer(tmp_path, caplog):
    async def run():
        local_port, unavailable_port = _free_port(), _free_port()
        while unavailable_port == local_port:
            unavailable_port = _free_port()
        broker = Broker(_broker_config(local_port))
        await broker.start()
        local = replace(MQTTConfig(), port=local_port)
        peer = LocalTestPeer(config=local)
        await peer.start()
        hostname = socket.gethostname()
        base = _mqtt_config(tmp_path)
        external = replace(base,
            adaptors=replace(base.adaptors,
                mqtt=replace(MQTTConfig(), policy=replace(MQTTConfig().policy, enabled=True),
                    provider="external", host=hostname, port=unavailable_port,
                    tls_enabled=True, ca_path=Path(ssl.get_default_verify_paths().cafile),
                    username="user", password=SecretValue("private"))))
        validate_config(external)
        source = ExternalMessageSource(bus=EventBus(), allowed_channels=frozenset({"mqtt"}))
        await source.start()
        client = MQTTClient(config=external.adaptors.mqtt,
            ingress=MQTTIngress(config=external.adaptors.mqtt, source=source))
        await client.start()
        try:
            await _until(lambda: client.last_error_code == "MQTT_BROKER_UNAVAILABLE", timeout=8)
            assert not client.is_connected()
            try:
                await client.publish_command()
            except MQTTSendError as exc:
                assert exc.code == "MQTT_SEND_NOT_CONNECTED"
            else:
                assert False, "unavailable external target reported success"
            assert peer.received_commands == []
            assert "MQTT_EXTERNAL_NO_FALLBACK" in caplog.text
            assert "private" not in caplog.text
        finally:
            await client.stop()
            await source.stop()
            await peer.stop()
            await broker.shutdown()
    asyncio.run(run())


def test_m5m_net_001_auth_rejection_uses_stable_code(tmp_path, caplog):
    async def run():
        port = _free_port()
        password_file = tmp_path / "passwords"
        password_file.write_text("user:" + PasswordHasher().hash("correct") + "\n")
        broker = Broker({"listeners": {"default": {"type": "tcp",
            "bind": f"127.0.0.1:{port}"}}, "plugins": {
            "amqtt.plugins.authentication.FileAuthPlugin": {
                "password_file": str(password_file)}}})
        await broker.start()
        config = replace(MQTTConfig(), provider="external", host="127.0.0.1",
            port=port, username="user", password=SecretValue("WRONG_SECRET"))
        source = ExternalMessageSource(bus=EventBus(), allowed_channels=frozenset({"mqtt"}))
        await source.start()
        client = MQTTClient(config=config, ingress=MQTTIngress(config=config, source=source))
        await client.start()
        try:
            await _until(lambda: client.last_error_code == "MQTT_AUTH_REJECTED")
            assert not client.is_connected()
            assert "MQTT_EXTERNAL_NO_FALLBACK reason=MQTT_AUTH_REJECTED" in caplog.text
            assert "WRONG_SECRET" not in caplog.text
        finally:
            await client.stop()
            await source.stop()
            await broker.shutdown()
    asyncio.run(run())


def test_m5m_net_001_tls_verification_failure_uses_stable_code(tmp_path, caplog):
    async def run():
        cert, key = tmp_path / "self-signed.pem", tmp_path / "private.key"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = _free_port()
        broker = Broker({"listeners": {"default": {"type": "tcp",
            "bind": f"127.0.0.1:{port}", "ssl": True,
            "certfile": str(cert), "keyfile": str(key)}},
            "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True}}})
        await broker.start()
        config = replace(MQTTConfig(), provider="external", host="localhost",
            port=port, tls_enabled=True,
            ca_path=Path(ssl.get_default_verify_paths().cafile))
        source = ExternalMessageSource(bus=EventBus(), allowed_channels=frozenset({"mqtt"}))
        await source.start()
        client = MQTTClient(config=config, ingress=MQTTIngress(config=config, source=source))
        await client.start()
        try:
            await _until(lambda: client.last_error_code == "MQTT_TLS_ERROR")
            assert not client.is_connected()
            assert "MQTT_EXTERNAL_NO_FALLBACK reason=MQTT_TLS_ERROR" in caplog.text
        finally:
            await client.stop()
            await source.stop()
            await broker.shutdown()
    asyncio.run(run())
