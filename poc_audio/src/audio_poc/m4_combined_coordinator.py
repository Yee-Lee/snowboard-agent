"""Artifact-independent orchestration for the formal M4 20-session pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class PersistentDomain(Protocol):
    async def start(self) -> None: ...

    async def run(self, session: dict[str, Any]) -> dict[str, Any]: ...

    async def stop(self) -> None: ...


class P9Overlap(Protocol):
    async def begin(self, request_id: str) -> dict[str, Any]: ...

    async def complete(self, request_id: str, token: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class CombinedSessionResult:
    session_id: str
    asr_fixture_id: str
    tts_fixture_id: str
    vad: dict[str, Any]
    asr: dict[str, Any]
    reasoner: dict[str, Any]
    tts: dict[str, Any]
    p9: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "asr_fixture_id": self.asr_fixture_id,
            "tts_fixture_id": self.tts_fixture_id,
            "vad": self.vad,
            "asr": self.asr,
            "reasoner": self.reasoner,
            "tts": self.tts,
            "p9": self.p9,
        }


class M4CombinedCoordinator:
    """Run all locked sessions while keeping every finalist resident exactly once."""

    def __init__(self, vad: PersistentDomain, asr: PersistentDomain, tts: PersistentDomain) -> None:
        self._domains = {"vad": vad, "asr": asr, "tts": tts}

    async def run(
        self,
        fixture_lock: dict[str, Any],
        p9: P9Overlap | None = None,
    ) -> list[dict[str, Any]]:
        records = fixture_lock.get("records")
        if not isinstance(records, list) or len(records) != 20:
            raise ValueError("M4 coordinator requires the locked 20-session catalog")
        started: list[PersistentDomain] = []
        try:
            for name in ("vad", "asr", "tts"):
                domain = self._domains[name]
                await domain.start()
                started.append(domain)
            results: list[dict[str, Any]] = []
            for record in records:
                result = await self._run_one(record, p9)
                results.append(result.to_dict())
            return results
        finally:
            failures: list[BaseException] = []
            for domain in reversed(started):
                try:
                    await domain.stop()
                except BaseException as error:
                    failures.append(error)
            if failures:
                raise RuntimeError("M4 persistent domain cleanup failed") from failures[0]

    async def _run_one(
        self,
        record: dict[str, Any],
        p9: P9Overlap | None,
    ) -> CombinedSessionResult:
        _validate_record(record)
        session_id = record["session_id"]
        p9_token = await p9.begin(session_id) if p9 is not None else None
        try:
            vad = await self._domains["vad"].run(record)
            _validate_stage(vad, "vad", session_id)
            asr_input = {**record, "bounded_wav": vad["bounded_wav"]}
            asr = await self._domains["asr"].run(asr_input)
            _validate_stage(asr, "asr", session_id)
            if asr.get("terminal") != "SUCCESS" or asr.get("nonempty") is not True:
                raise RuntimeError(f"M4 ASR terminal result is unusable: {session_id}")
            reasoner = {
                "terminal": "SUCCESS",
                "mapping": "SESSION_ID_TO_FROZEN_TTS_ID_NO_TRANSCRIPT_MUTATION",
                "tts_fixture_id": record["tts_fixture_id"],
            }
            tts_input = {**record, "reasoner": reasoner}
            tts = await self._domains["tts"].run(tts_input)
            _validate_stage(tts, "tts", session_id)
            if tts.get("playback_complete") is not True:
                raise RuntimeError(f"M4 TTS playback did not complete: {session_id}")
            p9_result = await p9.complete(session_id, p9_token) if p9 is not None else None
            return CombinedSessionResult(
                session_id=session_id,
                asr_fixture_id=record["fixture_id"],
                tts_fixture_id=record["tts_fixture_id"],
                vad=_sanitize_vad(vad),
                asr=_sanitize_asr(asr),
                reasoner=reasoner,
                tts=_sanitize_tts(tts),
                p9=p9_result,
            )
        except BaseException:
            # A partial P9 interval must never be represented as completed evidence.
            raise


def _validate_record(record: object) -> None:
    required = {"session_id", "fixture_id", "tts_fixture_id", "filename", "sha256"}
    if not isinstance(record, dict) or not required <= set(record):
        raise ValueError("M4 fixture-lock record is incomplete")
    if not all(isinstance(record[name], str) and record[name] for name in required):
        raise ValueError("M4 fixture-lock record has invalid values")


def _validate_stage(stage: object, domain: str, session_id: str) -> None:
    if not isinstance(stage, dict) or stage.get("session_id") != session_id:
        raise RuntimeError(f"M4 {domain} stage session identity mismatch")
    if stage.get("terminal") != "SUCCESS":
        raise RuntimeError(f"M4 {domain} stage did not terminate successfully")


def _sanitize_vad(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal": "SUCCESS",
        "bounded_sha256": stage["bounded_sha256"],
        "capture_intervals_ms": stage["capture_intervals_ms"],
    }


def _sanitize_asr(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal": "SUCCESS",
        "hypothesis_sha256": stage["hypothesis_sha256"],
        "nonempty": True,
        "latency_ms": stage["latency_ms"],
    }


def _sanitize_tts(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal": "SUCCESS",
        "pcm_sha256": stage["pcm_sha256"],
        "sample_count": stage["sample_count"],
        "playback_complete": True,
    }
