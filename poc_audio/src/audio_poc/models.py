"""Stable result types shared by the M1 harness and later candidate adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class TerminalStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FORCE_ABORTED = "force_aborted"


@dataclass(frozen=True, slots=True)
class CleanupProof:
    child_processes: int
    threads: int
    iterators: int
    streams: int
    device_owners: int

    @property
    def clean(self) -> bool:
        return all(value == 0 for value in asdict(self).values())


@dataclass(frozen=True, slots=True)
class RunResult:
    schema_version: str
    run_id: str
    source_sha: str
    candidate_id: str
    candidate_kind: str
    scenario: str
    started_at_utc: str
    duration_ms: float
    terminal_status: TerminalStatus
    worker_exit_code: int | None
    error_code: str | None
    force_abort_used: bool
    cleanup: CleanupProof

    def to_dict(self) -> dict[str, Any]:
        document = asdict(self)
        document["terminal_status"] = self.terminal_status.value
        document["cleanup"]["clean"] = self.cleanup.clean
        return document
