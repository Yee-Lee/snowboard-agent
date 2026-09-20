"""Explicit, one-shot fault injection for same-bytes Raspberry Pi verification.

Production composition never constructs this controller.  A verification runner
must supply it directly to a supported owner, declare the expected backend
identity, and consume the single configured checkpoint.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock
from types import MappingProxyType
from typing import Final, TypeAlias


IdentityValue: TypeAlias = str | int | bool

FAULT_POINTS: Final = frozenset({
    "alsa.capture.read",
    "alsa.playback.drain",
    "gpio.button.callback",
    "gpio.edge.read",
    "asr.inference.rejected",
    "asr.child.exit",
    "llm.child.exit",
    "llm.cleanup.unproven",
    "tts.child.exit",
})


class FaultInjectionError(RuntimeError):
    """The verification seam was malformed or identity-mismatched."""


@dataclass(frozen=True, slots=True)
class FaultInjectionEvidence:
    point: str
    backend_identity: Mapping[str, IdentityValue]


class DeterministicFaultInjector:
    """Validate one live backend identity and fire one declared checkpoint."""

    def __init__(
        self,
        point: str,
        *,
        expected_identity: Mapping[str, IdentityValue],
    ) -> None:
        if point not in FAULT_POINTS:
            raise ValueError("fault injection point is not in the closed set")
        if not expected_identity or any(
            type(key) is not str or not key or type(value) not in {str, int, bool}
            for key, value in expected_identity.items()
        ):
            raise ValueError("expected backend identity must be a non-empty scalar mapping")
        self._point = point
        self._expected = dict(expected_identity)
        self._evidence: FaultInjectionEvidence | None = None
        self._lock = Lock()

    @property
    def point(self) -> str:
        return self._point

    @property
    def fired(self) -> bool:
        return self._evidence is not None

    @property
    def evidence(self) -> FaultInjectionEvidence:
        evidence = self._evidence
        if evidence is None:
            raise FaultInjectionError("fault injection has not fired")
        return evidence

    def fire(
        self,
        point: str,
        backend_identity: Mapping[str, IdentityValue],
    ) -> bool:
        """Return true exactly once at the configured, identity-bound point."""

        if point != self._point:
            return False
        with self._lock:
            if self._evidence is not None:
                return False
            actual = dict(backend_identity)
            if any(
                type(key) is not str or not key or type(value) not in {str, int, bool}
                for key, value in actual.items()
            ):
                raise FaultInjectionError("actual backend identity is not a scalar mapping")
            if actual.get("live") is not True:
                raise FaultInjectionError("fault injection requires a live actual backend")
            mismatches = tuple(
                key for key, value in self._expected.items() if actual.get(key) != value
            )
            if mismatches:
                raise FaultInjectionError(
                    "actual backend identity differs at: " + ",".join(sorted(mismatches))
                )
            self._evidence = FaultInjectionEvidence(
                point=point,
                backend_identity=MappingProxyType(dict(sorted(actual.items()))),
            )
        return True


__all__ = [
    "DeterministicFaultInjector",
    "FAULT_POINTS",
    "FaultInjectionError",
    "FaultInjectionEvidence",
    "IdentityValue",
]
