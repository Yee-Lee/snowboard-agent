"""Project-owned MQTT wire peer for local development and integration tests."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

import paho.mqtt.client as mqtt

from sbd.core.config.models import MQTTConfig
from .wire import MQTTTopics, _ID, decode_object


class LocalTestPeer:
    MODES = frozenset({"empty", "success", "failure", "duplicate", "malformed"})

    def __init__(self, *, config: MQTTConfig, mode: str = "empty",
                 delay_seconds: float = 0.0,
                 logger: logging.Logger | None = None) -> None:
        if config.provider != "local_test" or mode not in self.MODES or delay_seconds < 0:
            raise ValueError("invalid local-test peer configuration")
        self.config = config
        self.mode = mode
        self.delay_seconds = delay_seconds
        self.topics = MQTTTopics.from_config(config)
        self._logger = logger or logging.getLogger(__name__)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: mqtt.Client | None = None
        self._ready = asyncio.Event()
        self._pending: set[asyncio.Task[None]] = set()
        self.received_commands: list[dict[str, object]] = []

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"{self.config.client_id}-peer",
            clean_session=True, protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        self._client = client

        def connected(_client, _userdata, _flags, reason_code, _properties) -> None:
            if getattr(reason_code, "value", reason_code) == 0:
                client.subscribe(self.topics.command, qos=1)

        def subscribed(_client, _userdata, _mid, _reason_codes, _properties) -> None:
            self._loop.call_soon_threadsafe(self._ready.set)

        def message(_client, _userdata, incoming) -> None:
            topic, payload = incoming.topic, bytes(incoming.payload)
            self._loop.call_soon_threadsafe(self._schedule, topic, payload)

        client.on_connect = connected
        client.on_subscribe = subscribed
        client.on_message = message
        try:
            await asyncio.to_thread(client.connect, self.config.host,
                                    self.config.port, self.config.keepalive_seconds)
            client.loop_start()
            await asyncio.wait_for(self._ready.wait(), timeout=5.0)
        except BaseException:
            await self.stop()
            raise

    def _schedule(self, topic: str, payload: bytes) -> None:
        task = asyncio.create_task(self._handle(topic, payload))
        self._pending.add(task)
        def completed(finished: asyncio.Task[None]) -> None:
            self._pending.discard(finished)
            if not finished.cancelled() and finished.exception() is not None:
                self._logger.warning("MQTT_PEER_PUBLISH_FAILED")
        task.add_done_callback(completed)

    async def _handle(self, topic: str, payload: bytes) -> None:
        try:
            command = decode_object(payload)
            if (topic != self.topics.command or set(command) !=
                    {"version", "request_id", "command"} or
                    type(command["version"]) is not int or command["version"] != 1 or
                    type(command["request_id"]) is not str or
                    not _ID.fullmatch(command["request_id"]) or
                    uuid.UUID(command["request_id"]).version != 4 or
                    command["command"] != "enable_remote_connection"):
                raise ValueError("invalid command")
        except (ValueError, KeyError, TypeError):
            self._logger.warning("MQTT_PEER_INVALID_COMMAND")
            return
        self.received_commands.append(command)
        if self.mode == "empty":
            return
        await asyncio.sleep(self.delay_seconds)
        if self.mode == "malformed":
            payload = b'{"version":1,"kind":"application_result"}'
        else:
            status = "failure" if self.mode == "failure" else "success"
            text = "遠端連線啟用失敗。" if status == "failure" else "遠端連線已成功啟用。"
            payload = json.dumps({"version": 1, "event_id": str(uuid.uuid4()),
                "kind": "application_result", "request_id": command["request_id"],
                "status": status, "text": text}, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")
        await self._publish(self.topics.result, payload)
        if self.mode == "duplicate":
            await self._publish(self.topics.result, payload)

    async def send_notification(self, text: str) -> None:
        payload = json.dumps({"version": 1, "event_id": str(uuid.uuid4()),
            "kind": "notification", "text": text}, ensure_ascii=False,
            separators=(",", ":")).encode("utf-8")
        await self._publish(self.topics.notification, payload)

    async def _publish(self, topic: str, payload: bytes) -> None:
        client = self._client
        if client is None or not client.is_connected():
            raise RuntimeError("local peer disconnected")
        info = client.publish(topic, payload=payload, qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError("local peer publish failed")
        await asyncio.to_thread(info.wait_for_publish, 5.0)
        if not info.is_published():
            raise RuntimeError("local peer publish timeout")

    async def stop(self) -> None:
        for task in tuple(self._pending):
            task.cancel()
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
        client, self._client = self._client, None
        if client is not None:
            await asyncio.to_thread(client.disconnect)
            await asyncio.to_thread(client.loop_stop)
