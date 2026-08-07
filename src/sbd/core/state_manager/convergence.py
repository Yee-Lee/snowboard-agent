"""Session Converger — Three-level cancellation convergence mechanism.

Defined per Ch 6 (docs/implement/ch06_cancel.md).
Handles parallel Level 1 abort() and Level 2 force_abort() escalation.
Aggregates destroyed backend keys for Resource Manager recovery.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol

from sbd.core.lifecycle import ForceAbortReport

logger = logging.getLogger(__name__)

ConvergenceTrigger = Literal["rest", "interrupt", "error", "shutdown"]


# ---------------------------------------------------------------------------
# Data Models & Exceptions
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConvergenceResult:
    """Aggregated result of session convergence."""

    destroyed_backends: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CancelTimeoutPolicy:
    """Timeout policies for abort and force_abort by operation kind."""

    abort_default_seconds: float = 2.0
    force_abort_default_seconds: float = 3.0
    abort_by_kind: Mapping[str, float] = field(default_factory=dict)
    force_abort_by_kind: Mapping[str, float] = field(default_factory=dict)

    def abort_for(self, kind: str) -> float:
        return self.abort_by_kind.get(kind, self.abort_default_seconds)

    def force_abort_for(self, kind: str) -> float:
        return self.force_abort_by_kind.get(kind, self.force_abort_default_seconds)


class ConvergenceError(RuntimeError):
    """Base exception for convergence failures."""

    pass


class ConvergenceContractViolation(ConvergenceError):
    """Raised when a caller or worker breaks convergence invariants."""

    pass


class ConvergenceFatalError(ConvergenceError):
    """Level 3 fatal exception raised when Level 2 force_abort fails."""

    def __init__(
        self,
        *,
        correlation_id: int,
        kind: str,
        phase: str,
        stage: str,
        cause: BaseException,
    ) -> None:
        self.correlation_id = correlation_id
        self.kind = kind
        self.phase = phase
        self.stage = stage
        self.cause = cause
        super().__init__(
            f"Convergence fatal at stage={stage} for correlation_id={correlation_id} "
            f"kind={kind} phase={phase}: {cause}"
        )

    @classmethod
    def from_target(
        cls, target: Any, stage: str, cause: BaseException
    ) -> ConvergenceFatalError:
        return cls(
            correlation_id=getattr(target, "correlation_id", 0),
            kind=getattr(target, "kind", "unknown"),
            phase=getattr(target, "phase", "unknown"),
            stage=stage,
            cause=cause,
        )


# ---------------------------------------------------------------------------
# Converger Interface & Implementation
# ---------------------------------------------------------------------------

class SessionConverger(Protocol):
    async def converge(
        self,
        records: tuple[Any, ...],
        trigger: ConvergenceTrigger,
    ) -> ConvergenceResult: ...


@dataclass
class _Level1Outcome:
    target: Any
    escalate: bool
    reason: str = ""
    error: Exception | None = None


class DefaultSessionConverger:
    """Default implementation of SessionConverger.

    Executes parallel Level 1 abort() and Level 2 force_abort() on in-flight records.
    """

    def __init__(
        self,
        *,
        timeouts: CancelTimeoutPolicy,
        logger_instance: logging.Logger | None = None,
    ) -> None:
        self.timeouts = timeouts
        self.logger = logger_instance or logger
        self._active = False

    async def converge(
        self,
        records: tuple[Any, ...],
        trigger: ConvergenceTrigger,
    ) -> ConvergenceResult:
        if self._active:
            raise ConvergenceContractViolation("SessionConverger reentry is forbidden")

        if not records:
            return ConvergenceResult()

        self._active = True
        try:
            # 1. Preflight validation
            cid_set = set()
            for r in records:
                cid = getattr(r, "correlation_id", None)
                if cid is None or cid in cid_set:
                    raise ConvergenceContractViolation(
                        f"Duplicate or missing correlation_id in records: {cid}"
                    )
                cid_set.add(cid)

            # Sort targets deterministically by correlation_id
            sorted_records = tuple(sorted(records, key=lambda r: r.correlation_id))

            # Filter records that still need cancellation vs already done
            active_targets: list[Any] = []
            for r in sorted_records:
                task = getattr(r, "task", None)
                if task is not None and not task.done():
                    active_targets.append(r)
                else:
                    # Harvest completed task exception if any (for logging context)
                    if task is not None and task.done() and not task.cancelled():
                        _ = task.exception()

            if not active_targets:
                return ConvergenceResult()

            # 2. Level 1: Parallel cooperative abort()
            l1_tasks = [self._run_abort(target) for target in active_targets]
            l1_outcomes: list[_Level1Outcome] = await asyncio.gather(*l1_tasks)

            escalated_targets = [out.target for out in l1_outcomes if out.escalate]

            if not escalated_targets:
                return ConvergenceResult()

            # 3. Level 2: Parallel forced force_abort()
            l2_tasks = [self._run_force_abort(target) for target in escalated_targets]
            l2_results: list[tuple[Any, ForceAbortReport]] = await asyncio.gather(*l2_tasks)

            # 4. Report aggregation
            destroyed: list[str] = []
            for target, report in l2_results:
                if not isinstance(report, ForceAbortReport):
                    raise ConvergenceContractViolation(
                        f"force_abort() must return ForceAbortReport, got {type(report)}"
                    )
                for key in report.destroyed_backends:
                    if not isinstance(key, str) or not key.strip():
                        raise ConvergenceContractViolation(
                            f"Invalid destroyed_backend key: {repr(key)}"
                        )
                    destroyed.append(key)

            # Deduplicate and sort lexicographically
            sorted_destroyed = tuple(sorted(set(destroyed)))
            return ConvergenceResult(destroyed_backends=sorted_destroyed)

        finally:
            self._active = False

    async def _run_abort(self, target: Any) -> _Level1Outcome:
        kind = getattr(target, "kind", "unknown")
        timeout = self.timeouts.abort_for(kind)
        worker = getattr(target, "worker", None)
        task = getattr(target, "task", None)

        try:
            async with asyncio.timeout(timeout):
                if worker is not None and hasattr(worker, "abort"):
                    await worker.abort()
                if task is not None:
                    await asyncio.shield(task)
        except TimeoutError:
            self.logger.warning(
                "Level 1 abort timed out for correlation_id=%s kind=%s",
                getattr(target, "correlation_id", 0),
                kind,
            )
            return _Level1Outcome(target, escalate=True, reason="timeout")
        except (asyncio.CancelledError, ConvergenceError):
            raise
        except Exception as exc:
            self.logger.warning(
                "Level 1 abort error for correlation_id=%s kind=%s: %s",
                getattr(target, "correlation_id", 0),
                kind,
                exc,
            )
            return _Level1Outcome(target, escalate=True, reason="abort_error", error=exc)

        return _Level1Outcome(target, escalate=False)

    async def _run_force_abort(self, target: Any) -> tuple[Any, ForceAbortReport]:
        kind = getattr(target, "kind", "unknown")
        timeout = self.timeouts.force_abort_for(kind)
        worker = getattr(target, "worker", None)
        task = getattr(target, "task", None)

        try:
            async with asyncio.timeout(timeout):
                if worker is not None and hasattr(worker, "force_abort"):
                    report = await worker.force_abort()
                else:
                    report = ForceAbortReport()

                if task is not None:
                    await asyncio.shield(task)
        except TimeoutError as exc:
            raise ConvergenceFatalError.from_target(
                target, stage="force_abort_timeout", cause=exc
            ) from exc
        except (asyncio.CancelledError, ConvergenceError):
            raise
        except Exception as exc:
            raise ConvergenceFatalError.from_target(
                target, stage="force_abort_error", cause=exc
            ) from exc

        return target, report
