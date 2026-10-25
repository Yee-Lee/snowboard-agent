"""MQTT 3.1.1 QoS 1 adaptor with one configured target and no offline queue."""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import uuid

import paho.mqtt.client as mqtt

from sbd.action.tool.registry import ToolRegistryError
from sbd.core.config.models import MQTTConfig
from .wire import MQTTIngress, MQTTTopics


class MQTTSourceUnavailable(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MQTTSendError(ToolRegistryError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MQTTClient:
    """One Paho client per connection, so failed sends cannot replay on reconnect."""

    def __init__(self, *, config: MQTTConfig, ingress: MQTTIngress,
                 logger: logging.Logger | None = None) -> None:
        self.config = config
        self.topics = MQTTTopics.from_config(config)
        self._ingress = ingress
        self._logger = logger or logging.getLogger(__name__)
        self._client: mqtt.Client | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._events: asyncio.Queue[tuple[mqtt.Client, str]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False
        self._stopping = False
        self.last_error_code: str | None = None

    def is_connected(self) -> bool:
        return self._connected and self._client is not None and self._client.is_connected()

    async def start(self) -> None:
        if self._run_task is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._events = asyncio.Queue()
        self._stopping = False
        self._run_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopping = True
        self._connected = False
        if self._run_task is not None:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None

    def _emit(self, client: mqtt.Client, code: str) -> None:
        loop, events = self._loop, self._events
        if loop is not None and events is not None and not loop.is_closed():
            loop.call_soon_threadsafe(events.put_nowait, (client, code))

    def _make_client(self) -> mqtt.Client:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.config.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        client.connect_timeout = min(max(self.config.send_timeout_seconds, 1.0), 5.0)
        if self.config.username is not None:
            client.username_pw_set(self.config.username,
                self.config.password.reveal() if self.config.password is not None else None)
        if self.config.tls_enabled:
            client.tls_set(ca_certs=str(self.config.ca_path), cert_reqs=ssl.CERT_REQUIRED)
            client.tls_insecure_set(False)

        def on_connect(_client, _userdata, _flags, reason_code, _properties) -> None:
            if getattr(reason_code, "value", reason_code) != 0:
                self._emit(client, "MQTT_AUTH_REJECTED" if getattr(reason_code, "value", reason_code) in {4, 5, 134, 135} else "MQTT_BROKER_UNAVAILABLE")
                return
            result, _mid = client.subscribe([
                (self.topics.result, 1), (self.topics.notification, 1)])
            if result != mqtt.MQTT_ERR_SUCCESS:
                self._emit(client, "MQTT_BROKER_UNAVAILABLE")

        def on_subscribe(_client, _userdata, _mid, reason_codes, _properties) -> None:
            if (len(reason_codes) != 2 or
                    any(getattr(code, "value", code) != 1 for code in reason_codes)):
                self._emit(client, "MQTT_BROKER_UNAVAILABLE")
            else:
                self._emit(client, "connected")

        def on_disconnect(_client, _userdata, _flags, _reason_code, _properties) -> None:
            self._emit(client, "MQTT_BROKER_UNAVAILABLE")

        def on_message(_client, _userdata, message) -> None:
            loop = self._loop
            if (self._client is client and not self._stopping and
                    loop is not None and not loop.is_closed()):
                topic, payload = message.topic, bytes(message.payload)
                loop.call_soon_threadsafe(lambda: asyncio.create_task(
                    self._receive(topic, payload)))

        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        return client

    async def _receive(self, topic: str, payload: bytes) -> None:
        try:
            await self._ingress.ingest(topic, payload)
        except Exception:
            self._logger.warning("MQTT_INGEST_UNAVAILABLE")

    def _report(self, code: str) -> None:
        self.last_error_code = code
        if self.config.provider == "external":
            self._logger.warning("MQTT_EXTERNAL_NO_FALLBACK reason=%s", code)
        else:
            self._logger.warning("%s", code)

    async def _run(self) -> None:
        delay = 1.0
        try:
            while not self._stopping:
                client = None
                try:
                    client = self._make_client()
                    self._client = client
                    await asyncio.to_thread(client.connect, self.config.host,
                                            self.config.port, self.config.keepalive_seconds)
                    client.loop_start()
                    assert self._events is not None
                    while not self._stopping:
                        event_client, code = await asyncio.wait_for(
                            self._events.get(), timeout=None if self._connected else 5.0)
                        if event_client is not client:
                            continue
                        if code == "connected":
                            self._connected = True
                            self.last_error_code = None
                            delay = 1.0
                            continue
                        self._connected = False
                        self._report(code)
                        break
                except asyncio.CancelledError:
                    raise
                except (ssl.SSLError, ssl.CertificateError):
                    self._connected = False
                    self._report("MQTT_TLS_ERROR")
                except (OSError, TimeoutError, ValueError):
                    self._connected = False
                    self._report("MQTT_BROKER_UNAVAILABLE")
                finally:
                    self._connected = False
                    if client is not None:
                        await asyncio.to_thread(client.disconnect)
                        await asyncio.to_thread(client.loop_stop)
                    if self._client is client:
                        self._client = None
                    if self._events is not None:
                        while not self._events.empty():
                            self._events.get_nowait()
                if not self._stopping:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30.0)
        except asyncio.CancelledError:
            raise

    async def publish_command(self) -> str:
        client = self._client
        if client is None or not self.is_connected():
            self._report("MQTT_SEND_NOT_CONNECTED")
            raise MQTTSendError("MQTT_SEND_NOT_CONNECTED")
        request_id = str(uuid.uuid4())
        payload = json.dumps({"version": 1, "request_id": request_id,
                              "command": "enable_remote_connection"},
                             ensure_ascii=False, separators=(",", ":"))
        try:
            info = client.publish(self.topics.command, payload=payload, qos=1, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                self._report("MQTT_SEND_REJECTED")
                raise MQTTSendError("MQTT_SEND_REJECTED")
            await asyncio.wait_for(asyncio.to_thread(info.wait_for_publish,
                self.config.send_timeout_seconds), timeout=self.config.send_timeout_seconds + 0.1)
            if not info.is_published():
                self._report("MQTT_SEND_TIMEOUT")
                raise MQTTSendError("MQTT_SEND_TIMEOUT")
        except MQTTSendError:
            raise
        except (TimeoutError, RuntimeError, ValueError):
            self._report("MQTT_SEND_TIMEOUT")
            raise MQTTSendError("MQTT_SEND_TIMEOUT") from None
        return request_id
