"""In-memory child-process seam for M4a parent adapter regressions."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Mapping
from typing import Any

from sbd.adaptor.framed_child import ChildState


class ScriptedChild:
    def __init__(
        self,
        events: list[dict[str, Any]] | None = None,
        *,
        payload: bytes = b"",
        cancel_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.events = list(events or [])
        self.cancel_events = list(cancel_events or [])
        self.payload = payload
        self.state = ChildState.STOPPED
        self.messages: list[tuple[dict[str, Any], bytes | None]] = []
        self.start_count = 0
        self.stop_count = 0
        self.force_count = 0
        self.request_id = 0
        self.receive_entered = asyncio.Event()
        self.receive_release = asyncio.Event()
        self.active_receivers = 0
        self.max_active_receivers = 0

    async def start(self) -> None:
        if self.state is ChildState.READY:
            return
        self.start_count += 1
        self.state = ChildState.READY

    async def stop(self) -> None:
        if self.state is ChildState.STOPPED:
            return
        self.stop_count += 1
        self.state = ChildState.STOPPED

    async def force_terminate(self) -> None:
        self.force_count += 1
        self.state = ChildState.DESTROYED

    def allocate_request_id(self) -> int:
        assert self.state is ChildState.READY
        self.request_id += 1
        self.state = ChildState.BUSY
        return self.request_id

    async def send(self, value: Mapping[str, Any], payload: bytes | None = None) -> None:
        self.messages.append((dict(value), payload))
        if value.get("op") == "CANCEL" and self.cancel_events:
            self.events.extend(self.cancel_events)
            self.cancel_events.clear()
            self.receive_release.set()

    async def receive(self) -> dict[str, Any]:
        self.active_receivers += 1
        self.max_active_receivers = max(self.max_active_receivers, self.active_receivers)
        try:
            self.receive_entered.set()
            if not self.events:
                await self.receive_release.wait()
            if not self.events:
                raise EOFError("scripted child has no event")
            event = self.events.pop(0)
            if not self.events:
                self.receive_release.clear()
            return event
        finally:
            self.active_receivers -= 1

    async def read_payload(self, payload_bytes: int, expected_sha256: str) -> bytes:
        assert payload_bytes == len(self.payload)
        return self.payload

    def operation_finished(self) -> None:
        assert self.state is ChildState.BUSY
        self.state = ChildState.READY


def asr_ack(request_id: int, sequence: int) -> dict[str, Any]:
    return {"protocol": 1, "event": "FRAME_ACCEPTED", "request_id": request_id, "sequence": sequence}


def asr_endpoint(request_id: int, captured_frames: int = 2) -> dict[str, Any]:
    bounded = b"\x00" * (captured_frames * 640)
    return {
        "protocol": 1, "event": "ENDPOINT", "request_id": request_id,
        "captured_frames": captured_frames, "bounded_samples": captured_frames * 320,
        "bounded_pcm_sha256": hashlib.sha256(bounded).hexdigest(),
    }


def asr_result(request_id: int, text: str = "測試") -> dict[str, Any]:
    return {"protocol": 1, "event": "RESULT", "request_id": request_id, "text": text, "language": "zh-TW", "latency_ms": 1.5}
