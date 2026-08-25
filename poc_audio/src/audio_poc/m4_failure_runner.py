"""Artifact-independent orchestration for M4 failure injection and recovery."""

from __future__ import annotations

import time
from typing import Any, Protocol

from .m4_failure import FORCE_ABORT_SOURCE, TERMINALS
from .m4_packet import FAILURE_ROWS


class FailureDomain(Protocol):
    """One candidate-specific, evidence-producing failure adapter.

    ``inject`` owns the candidate process until it reaches the named terminal
    state. ``recover`` must start a fresh instance of that same finalist and
    execute the supplied controlled probe successfully. Neither method may
    return raw audio or transcript content.
    """

    async def inject(self, scenario: str, probe: dict[str, Any]) -> dict[str, Any]: ...

    async def recover(self, probe: dict[str, Any]) -> dict[str, Any]: ...


class M4FailureRunner:
    def __init__(self, domains: dict[str, FailureDomain]) -> None:
        if set(domains) != {"vad", "asr", "tts"}:
            raise ValueError("M4 failure runner requires exactly VAD, ASR and TTS adapters")
        self._domains = domains

    async def run(self, probes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        if set(probes) != {"vad", "asr", "tts"}:
            raise ValueError("M4 failure runner requires one controlled probe per domain")
        cases: list[dict[str, Any]] = []
        for test_id, domain_name, scenario in FAILURE_ROWS:
            started = time.monotonic()
            domain = self._domains[domain_name]
            injected = await domain.inject(scenario, probes[domain_name])
            recovered = await domain.recover(probes[domain_name])
            cases.append(_case(
                test_id, domain_name, scenario, injected, recovered,
                round((time.monotonic() - started) * 1000, 3),
            ))
        return cases


def _case(
    test_id: str,
    domain: str,
    scenario: str,
    injected: object,
    recovered: object,
    duration_ms: float,
) -> dict[str, Any]:
    if not isinstance(injected, dict) or not isinstance(recovered, dict):
        raise RuntimeError(f"M4 failure adapter returned an invalid result: {test_id}")
    terminal = TERMINALS[scenario]
    if injected.get("terminal_status") != terminal or injected.get("injection_observed") is not True:
        raise RuntimeError(f"M4 failure adapter did not reach {terminal}: {test_id}")
    expected_source = FORCE_ABORT_SOURCE if scenario == "force_abort" else "ACTUAL_FINALIST"
    if injected.get("injection_source") != expected_source:
        raise RuntimeError(f"M4 failure adapter source is invalid: {test_id}")
    if injected.get("force_abort_used") != (scenario == "force_abort"):
        raise RuntimeError(f"M4 failure adapter force-abort proof is invalid: {test_id}")
    if recovered.get("terminal_status") != "SUCCESS" or recovered.get("same_finalist") is not True:
        raise RuntimeError(f"M4 failure adapter recovery failed: {test_id}")
    return {
        "test_id": test_id, "domain": domain, "scenario": scenario,
        "terminal_status": terminal, "injection_source": expected_source,
        "injection_observed": True, "duration_ms": duration_ms,
        "force_abort_used": scenario == "force_abort", "cleanup": injected.get("cleanup"),
        "recovery": {
            "attempted": True, "terminal_status": "SUCCESS", "same_finalist": True,
            "cleanup": recovered.get("cleanup"),
        },
    }
