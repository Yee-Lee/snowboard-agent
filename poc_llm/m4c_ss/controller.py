"""Bounded fragment admission contract for one logical streaming-speak operation.

This module deliberately has no LiteRT-LM, TTS, Audio or Core imports.  It is
the deterministic ownership boundary shared by the future fake and target
adapters; it does not execute a prototype or publish a product Fact.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib


MAX_PENDING_FRAGMENTS = 2
MAX_PENDING_UTF8_BYTES = 256


class FragmentChannelError(RuntimeError):
    """Stable fail-closed error without fragment or terminal content."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Fragment:
    sequence: int
    text: str

    @property
    def utf8_bytes(self) -> int:
        return len(self.text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class TerminalProof:
    fragment_count: int
    normalized_utf8_bytes: int
    normalized_text_sha256: str
    admission_closed: bool
    queue_empty: bool
    no_inflight_fragment: bool


@dataclass(frozen=True, slots=True)
class CleanupProof:
    terminal_state: str
    queue_empty: bool
    pending_utf8_bytes: int
    no_inflight_fragment: bool


class FragmentChannel:
    """Serialize one operation while bounding only not-yet-consumed fragments.

    ``feed`` backpressures before admission, so a producer that is cancelled
    while waiting cannot leave a ledger entry without a corresponding queue
    item.  ``receive`` permits one active fragment at a time; a mapping adapter
    must acknowledge it only after that fragment's synthesis/playback has
    completed.  Terminal validation closes admission but success remains
    unavailable until all admitted fragments have been acknowledged.
    """

    def __init__(self, operation_id: str) -> None:
        if type(operation_id) is not str or not operation_id:
            raise FragmentChannelError("INVALID_OPERATION_ID")
        self._operation_id = operation_id
        self._condition = asyncio.Condition()
        self._pending: deque[Fragment] = deque()
        self._pending_bytes = 0
        self._inflight: tuple[Fragment, ...] = ()
        self._admitted: list[str] = []
        self._acknowledged: list[str] = []
        self._next_sequence = 0
        self._state = "OPEN"
        self._terminal_text: str | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def pending_utf8_bytes(self) -> int:
        return self._pending_bytes

    @property
    def inflight_sequence(self) -> int | None:
        return None if not self._inflight else self._inflight[0].sequence

    async def feed(self, operation_id: str, sequence: int, text: str) -> None:
        fragment = self._validate_candidate(operation_id, sequence, text)
        if fragment.utf8_bytes > MAX_PENDING_UTF8_BYTES:
            raise FragmentChannelError("FRAGMENT_TOO_LARGE")
        async with self._condition:
            while (
                self._state == "OPEN"
                and (
                    len(self._pending) >= MAX_PENDING_FRAGMENTS
                    or self._pending_bytes + fragment.utf8_bytes > MAX_PENDING_UTF8_BYTES
                )
            ):
                await self._condition.wait()
            self._require_operation(operation_id)
            self._require_open()
            if sequence != self._next_sequence:
                raise FragmentChannelError("FRAGMENT_SEQUENCE")
            self._pending.append(fragment)
            self._pending_bytes += fragment.utf8_bytes
            self._admitted.append(text)
            self._next_sequence += 1
            self._condition.notify_all()

    async def receive(self) -> Fragment | None:
        group = await self.receive_group(coalesce_available=False)
        return None if group is None else group[0]

    async def receive_group(self, *, coalesce_available: bool) -> tuple[Fragment, ...] | None:
        """Take one fragment, plus one already-queued look-ahead when requested."""

        async with self._condition:
            while True:
                if self._state in {"FAILED", "CANCELLED"}:
                    raise FragmentChannelError("OPERATION_CLOSED")
                if self._inflight:
                    await self._condition.wait()
                    continue
                if self._pending:
                    fragments = [self._pending.popleft()]
                    if coalesce_available and self._pending:
                        fragments.append(self._pending.popleft())
                    for fragment in fragments:
                        self._pending_bytes -= fragment.utf8_bytes
                    self._inflight = tuple(fragments)
                    self._condition.notify_all()
                    return self._inflight
                if self._state == "TERMINAL_VALID":
                    return None
                await self._condition.wait()

    async def acknowledge(self, operation_id: str, sequence: int) -> None:
        await self.acknowledge_group(operation_id, (sequence,))

    async def acknowledge_group(self, operation_id: str, sequences: tuple[int, ...]) -> None:
        async with self._condition:
            self._require_operation(operation_id)
            if self._state in {"FAILED", "CANCELLED"}:
                raise FragmentChannelError("OPERATION_CLOSED")
            if not self._inflight or tuple(item.sequence for item in self._inflight) != sequences:
                raise FragmentChannelError("ACK_SEQUENCE")
            self._acknowledged.extend(item.text for item in self._inflight)
            self._inflight = ()
            self._condition.notify_all()

    async def finish(
        self,
        operation_id: str,
        terminal_text: str,
        *,
        semantic_valid: bool = True,
    ) -> None:
        async with self._condition:
            self._require_operation(operation_id)
            self._require_open()
            if type(terminal_text) is not str:
                self._fail_locked()
                raise FragmentChannelError("INVALID_TERMINAL")
            if not semantic_valid:
                self._fail_locked()
                raise FragmentChannelError("INVALID_TERMINAL")
            if "".join(self._admitted) != terminal_text:
                self._fail_locked()
                raise FragmentChannelError("TERMINAL_PREFIX_MISMATCH")
            self._terminal_text = terminal_text
            self._state = "TERMINAL_VALID"
            self._condition.notify_all()

    async def cancel(self, operation_id: str) -> None:
        async with self._condition:
            self._require_operation(operation_id)
            if self._state == "COMPLETED":
                raise FragmentChannelError("OPERATION_CLOSED")
            self._state = "CANCELLED"
            self._pending.clear()
            self._pending_bytes = 0
            self._condition.notify_all()

    async def abort_inflight(self, operation_id: str, sequence: int) -> None:
        await self.abort_inflight_group(operation_id, (sequence,))

    async def abort_inflight_group(self, operation_id: str, sequences: tuple[int, ...]) -> None:
        """Record adapter proof that cancelled/failed active output has stopped."""

        async with self._condition:
            self._require_operation(operation_id)
            if self._state not in {"FAILED", "CANCELLED"}:
                raise FragmentChannelError("ABORT_NOT_REQUIRED")
            if not self._inflight or tuple(item.sequence for item in self._inflight) != sequences:
                raise FragmentChannelError("ACK_SEQUENCE")
            self._inflight = ()
            self._condition.notify_all()

    async def cleanup_proof(self, operation_id: str) -> CleanupProof:
        async with self._condition:
            self._require_operation(operation_id)
            if self._state not in {"FAILED", "CANCELLED"}:
                raise FragmentChannelError("CLEANUP_NOT_TERMINAL")
            if self._pending or self._pending_bytes or self._inflight:
                raise FragmentChannelError("CLEANUP_NOT_CONVERGED")
            return CleanupProof(
                terminal_state=self._state,
                queue_empty=True,
                pending_utf8_bytes=0,
                no_inflight_fragment=True,
            )

    async def complete(self, operation_id: str) -> TerminalProof:
        async with self._condition:
            self._require_operation(operation_id)
            if self._state != "TERMINAL_VALID":
                raise FragmentChannelError("TERMINAL_NOT_VALID")
            if self._pending or self._inflight:
                raise FragmentChannelError("OUTPUT_NOT_DRAINED")
            spoken = "".join(self._acknowledged)
            if spoken != self._terminal_text:
                self._fail_locked()
                raise FragmentChannelError("SPOKEN_TEXT_MISMATCH")
            self._state = "COMPLETED"
            terminal = self._terminal_text.encode("utf-8")
            return TerminalProof(
                fragment_count=len(self._acknowledged),
                normalized_utf8_bytes=len(terminal),
                normalized_text_sha256=hashlib.sha256(terminal).hexdigest(),
                admission_closed=True,
                queue_empty=True,
                no_inflight_fragment=True,
            )

    def _validate_candidate(self, operation_id: str, sequence: int, text: str) -> Fragment:
        self._require_operation(operation_id)
        if type(sequence) is not int or sequence < 0:
            raise FragmentChannelError("FRAGMENT_SEQUENCE")
        if type(text) is not str or not text or "\x00" in text:
            raise FragmentChannelError("INVALID_FRAGMENT")
        return Fragment(sequence, text)

    def _require_operation(self, operation_id: str) -> None:
        if operation_id != self._operation_id:
            raise FragmentChannelError("STALE_OPERATION")

    def _require_open(self) -> None:
        if self._state != "OPEN":
            raise FragmentChannelError("ADMISSION_CLOSED")

    def _fail_locked(self) -> None:
        self._state = "FAILED"
        self._pending.clear()
        self._pending_bytes = 0
        self._condition.notify_all()
