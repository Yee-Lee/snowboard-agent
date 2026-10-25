"""M5 MQTT wire v1 validation before external-message ingest."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import deque
from dataclasses import dataclass

from sbd.cognition.semantic import SemanticError, normalize_text
from sbd.core.config.models import MQTTConfig
from sbd.input_events.external_message import ExternalMessageSource
from sbd.input_events.external_message.buffer import ExternalMessageBufferFull, ExternalMessageDropped

MQTT_MAX_PAYLOAD_BYTES = 2048
MQTT_TEXT_MAX_CODEPOINTS = 32
_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}\Z")


@dataclass(frozen=True, slots=True)
class MQTTTopics:
    command: str
    result: str
    notification: str

    @classmethod
    def from_config(cls, config: MQTTConfig) -> "MQTTTopics":
        root = f"{config.topic_prefix}/{config.device_id}"
        return cls(f"{root}/{config.command_topic_suffix}",
                   f"{root}/{config.result_topic_suffix}",
                   f"{root}/{config.notification_topic_suffix}")


class _InvalidPayload(ValueError):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise _InvalidPayload("schema")
        result[name] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise _InvalidPayload("json")


def decode_object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or len(payload) > MQTT_MAX_PAYLOAD_BYTES:
        raise _InvalidPayload("size")
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"),
                           object_pairs_hook=_unique, parse_constant=_invalid_constant)
    except _InvalidPayload:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise _InvalidPayload("json") from None
    if type(value) is not dict:
        raise _InvalidPayload("schema")
    return value


def _valid_id(value: object) -> bool:
    return type(value) is str and bool(_ID.fullmatch(value))


class MQTTIngress:
    """Deduplicate only messages the Ch 7 source actually accepted."""

    def __init__(self, *, config: MQTTConfig, source: ExternalMessageSource,
                 logger: logging.Logger | None = None) -> None:
        self.topics = MQTTTopics.from_config(config)
        self._source = source
        self._logger = logger or logging.getLogger(__name__)
        self._seen: set[str] = set()
        self._order: deque[str] = deque()
        self._lock = asyncio.Lock()

    async def ingest(self, topic: str, payload: bytes) -> bool:
        category = "schema"
        suffix = "unknown"
        try:
            if topic == self.topics.result:
                suffix = "results/remote-connection"
                expected = {"version", "event_id", "kind", "request_id", "status", "text"}
                kind = "application_result"
            elif topic == self.topics.notification:
                suffix = "notifications"
                expected = {"version", "event_id", "kind", "text"}
                kind = "notification"
            else:
                raise _InvalidPayload("topic_kind")
            value = decode_object(payload)
            if (set(value) != expected or type(value["version"]) is not int or
                    value["version"] != 1 or not _valid_id(value["event_id"]) or
                    type(value["text"]) is not str):
                raise _InvalidPayload("schema")
            if value["kind"] != kind:
                raise _InvalidPayload("topic_kind")
            if kind == "application_result":
                if (not _valid_id(value["request_id"]) or
                        type(value["status"]) is not str or
                        value["status"] not in {"success", "failure"}):
                    raise _InvalidPayload("schema")
                status = value["status"]
                request_id = value["request_id"]
            else:
                status, request_id = "notice", None
            try:
                normalized = normalize_text(value["text"])
            except SemanticError:
                raise _InvalidPayload("text") from None
            if not normalized or len(normalized) > MQTT_TEXT_MAX_CODEPOINTS:
                raise _InvalidPayload("text")
            event_id = value["event_id"]
            async with self._lock:
                if event_id in self._seen:
                    self._logger.debug("MQTT_DUPLICATE_EVENT")
                    return False
                try:
                    await self._source.ingest(channel="mqtt", text=normalized,
                        metadata={"kind": kind, "status": status,
                                  "event_id": event_id, "request_id": request_id})
                except ExternalMessageDropped:
                    # Source owns EXTERNAL_MESSAGE_DROPPED logging.
                    return False
                except ExternalMessageBufferFull:
                    self._logger.warning("EXTERNAL_MESSAGE_DROPPED policy=reject")
                    return False
                self._seen.add(event_id)
                self._order.append(event_id)
                if len(self._order) > 64:
                    self._seen.remove(self._order.popleft())
            return True
        except _InvalidPayload as exc:
            category = exc.category
        self._logger.warning("MQTT_INVALID_PAYLOAD topic_suffix=%s category=%s", suffix, category)
        return False
