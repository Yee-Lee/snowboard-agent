"""Artifact-independent Gate 2B Audio -> LLM -> Audio coordinator."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any, Awaitable, Callable, Protocol

from poc_llm.harness.gate2_errors_v1 import CandidateViolation, CleanupViolation


class PersistentDomain(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def residency_identity(self) -> dict[str, Any]: ...


class VadDomain(PersistentDomain, Protocol):
    async def run(self, session: dict[str, Any]) -> dict[str, Any]: ...


class AsrDomain(PersistentDomain, Protocol):
    async def run(self, session: dict[str, Any]) -> dict[str, Any]: ...


class LlmDomain(PersistentDomain, Protocol):
    async def run(
        self, session_id: str, transcript: str, nonce: str, trap: str
    ) -> dict[str, Any]: ...


class TtsDomain(PersistentDomain, Protocol):
    async def run(self, session: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class CombinedSession:
    session_id: str
    audio_fixture_id: str
    tts_fixture_id: str
    vad: dict[str, Any]
    asr: dict[str, Any]
    llm: dict[str, Any]
    tts: dict[str, Any]
    timings_ms: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "audio_fixture_id": self.audio_fixture_id,
            "tts_fixture_id": self.tts_fixture_id,
            "vad": self.vad,
            "asr": self.asr,
            "llm": self.llm,
            "tts": self.tts,
            "timings_ms": self.timings_ms,
        }


class Gate2BCombinedCoordinator:
    """Keep all four accepted domains resident for exactly twenty sessions."""

    def __init__(
        self,
        vad: VadDomain,
        asr: AsrDomain,
        llm: LlmDomain,
        tts: TtsDomain,
        *,
        pause: Callable[[float], Awaitable[None]],
        group_absent: Callable[[int], bool] | None = None,
        force_cleanup: Callable[[str, int], dict[str, Any]] | None = None,
    ) -> None:
        self._domains: dict[str, PersistentDomain] = {
            "vad": vad,
            "asr": asr,
            "tts": tts,
            "llm": llm,
        }
        self._vad = vad
        self._asr = asr
        self._llm = llm
        self._tts = tts
        self._pause = pause
        self._group_absent = group_absent
        self._force_cleanup = force_cleanup
        self.trace: list[dict[str, Any]] = []
        self.stop_order: list[str] = []
        self.cadence_pause_elapsed_ms: list[float] = []
        self.total_elapsed_ms: float | None = None
        self.started_roots: dict[str, int] = {}
        self.cleanup_proofs: dict[str, dict[str, Any]] = {}
        self.session_stage_windows: list[dict[str, Any]] = []

    async def run(
        self,
        records: list[dict[str, Any]],
        *,
        cadence_s: float = 5.0,
        on_resident: Callable[[], None] | None = None,
        before_shutdown: Callable[[], None] | None = None,
        after_session: Callable[[int], None] | None = None,
    ) -> list[dict[str, Any]]:
        return await self._run_records(
            records,
            expected_count=20,
            cadence_s=cadence_s,
            on_resident=on_resident,
            before_shutdown=before_shutdown,
            after_session=after_session,
        )

    async def run_single_diagnostic(
        self,
        record: dict[str, Any],
        *,
        on_resident: Callable[[], None] | None = None,
        before_shutdown: Callable[[], None] | None = None,
        after_session: Callable[[int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Exercise the exact combined boundary once without formal credit."""

        return await self._run_records(
            [record],
            expected_count=1,
            cadence_s=0.0,
            on_resident=on_resident,
            before_shutdown=before_shutdown,
            after_session=after_session,
        )

    async def _run_records(
        self,
        records: list[dict[str, Any]],
        *,
        expected_count: int,
        cadence_s: float,
        on_resident: Callable[[], None] | None,
        before_shutdown: Callable[[], None] | None,
        after_session: Callable[[int], None] | None,
    ) -> list[dict[str, Any]]:
        if len(records) != expected_count or cadence_s < 0:
            raise ValueError(
                f"Gate 2B requires exactly {expected_count} sessions and nonnegative cadence"
            )
        session_ids = [record.get("session_id") for record in records]
        if len(set(session_ids)) != expected_count:
            raise ValueError("Gate 2B session IDs must be unique")
        started: list[tuple[str, PersistentDomain]] = []
        run_started = time.monotonic()
        try:
            for name in ("vad", "asr", "tts", "llm"):
                domain = self._domains[name]
                started.append((name, domain))
                try:
                    await domain.start()
                finally:
                    identity = domain.residency_identity()
                    pid = identity.get("pid")
                    if identity.get("alive") is True and isinstance(pid, int) and pid > 0:
                        self.started_roots[name] = pid
                identity = domain.residency_identity()
                if identity.get("alive") is not True or name not in self.started_roots:
                    raise RuntimeError(f"Gate 2B {name} did not become resident")
            self._require_resident()
            if on_resident is not None:
                on_resident()
            results: list[dict[str, Any]] = []
            for index, record in enumerate(records):
                results.append((await self._run_one(record, index)).to_dict())
                if after_session is not None:
                    after_session(index + 1)
                if index != len(records) - 1:
                    pause_started = time.monotonic()
                    await self._pause(cadence_s)
                    self.cadence_pause_elapsed_ms.append(_elapsed_ms(pause_started))
            self.total_elapsed_ms = _elapsed_ms(run_started)
            return results
        finally:
            failures: list[BaseException] = []
            if before_shutdown is not None:
                try:
                    before_shutdown()
                except BaseException as error:
                    failures.append(error)
            cleanup_failed = False
            for name, domain in reversed(started):
                root = self.started_roots.get(name)
                identity_before_stop = domain.residency_identity()
                identity_pid = identity_before_stop.get("pid")
                if (
                    root is None
                    and identity_before_stop.get("alive") is True
                    and isinstance(identity_pid, int)
                    and identity_pid > 0
                ):
                    root = identity_pid
                    self.started_roots[name] = root
                cooperative_ok = True
                error_type: str | None = None
                try:
                    await domain.stop()
                except BaseException as error:
                    cooperative_ok = False
                    cleanup_failed = True
                    error_type = type(error).__name__
                self.stop_order.append(name)
                if root is not None and self._group_absent is not None:
                    absent = self._group_absent(root)
                else:
                    identity = domain.residency_identity()
                    absent = identity.get("alive") is False
                fallback: dict[str, Any] | None = None
                if not absent and root is not None and self._force_cleanup is not None:
                    try:
                        fallback = self._force_cleanup(name, root)
                        absent = fallback.get("process_group_absent") is True
                    except BaseException as error:
                        fallback = {"process_group_absent": False}
                        error_type = error_type or type(error).__name__
                        absent = False
                if not absent:
                    cleanup_failed = True
                self.cleanup_proofs[name] = {
                    "root_pid": root,
                    "cooperative_stop": cooperative_ok,
                    "fallback_used": fallback is not None,
                    "process_group_absent": absent,
                    "error_type": error_type,
                }
            if cleanup_failed:
                failures.append(CleanupViolation("Gate 2B bounded owner cleanup failed"))
            if failures:
                raise failures[0]

    def residency_roots(self) -> dict[str, int]:
        identities = self._require_resident()
        return {name: int(identity["pid"]) for name, identity in identities.items()}

    def _require_resident(self) -> dict[str, dict[str, Any]]:
        identities = {
            name: domain.residency_identity()
            for name, domain in self._domains.items()
        }
        if any(
            identity.get("alive") is not True
            or not isinstance(identity.get("pid"), int)
            or identity["pid"] <= 0
            for identity in identities.values()
        ):
            raise RuntimeError("Gate 2B requires all four domains resident and owned")
        return identities

    async def _run_one(
        self, record: dict[str, Any], index: int
    ) -> CombinedSession:
        _validate_record(record)
        session_id = record["session_id"]
        trace: dict[str, Any] = {
            "session_id": session_id,
            "completed_stages": [],
            "timings_ms": {},
        }
        self.trace.append(trace)
        session_started = time.monotonic()
        stage_window: dict[str, Any] = {
            "session_id": session_id,
            "start_monotonic_s": session_started,
            "stage_ends_monotonic_s": {},
        }
        self.session_stage_windows.append(stage_window)
        try:
            started = time.monotonic()
            vad = await self._vad.run(record)
            _validate_stage(vad, "vad", session_id)
            trace["timings_ms"]["vad"] = _elapsed_ms(started)
            trace["completed_stages"].append("vad")
            stage_window["stage_ends_monotonic_s"]["vad"] = time.monotonic()

            started = time.monotonic()
            asr = await self._asr.run({**record, "bounded_wav": vad["bounded_wav"]})
            _validate_stage(asr, "asr", session_id)
            transcript = asr.get("transcript")
            if not isinstance(transcript, str) or not transcript.strip():
                raise RuntimeError("Gate 2B ASR transcript is unusable")
            transcript_sha256 = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
            if asr.get("transcript_sha256") != transcript_sha256:
                raise CandidateViolation("Gate 2B ASR transcript identity mismatch")
            trace["timings_ms"]["asr"] = _elapsed_ms(started)
            trace["completed_stages"].append("asr")
            stage_window["stage_ends_monotonic_s"]["asr"] = time.monotonic()

            nonce = f"G2BN{index + 1:04d}"
            trap = f"G2BT{index + 1:04d}"
            started = time.monotonic()
            llm = await self._llm.run(session_id, transcript, nonce, trap)
            _validate_stage(llm, "llm", session_id)
            speech = llm.get("speech_text")
            if not isinstance(speech, str) or not speech.strip():
                raise RuntimeError("Gate 2B LLM did not produce speak text")
            speech_sha256 = hashlib.sha256(speech.encode("utf-8")).hexdigest()
            if (
                llm.get("speech_sha256") != speech_sha256
                or llm.get("prior_marker_leaked") is not False
                or llm.get("current_marker_present_once") is not True
                or llm.get("current_trap_absent") is not True
            ):
                raise CandidateViolation("Gate 2B LLM history or response identity failure")
            trace["timings_ms"]["llm"] = _elapsed_ms(started)
            trace["completed_stages"].append("llm")
            stage_window["stage_ends_monotonic_s"]["llm"] = time.monotonic()

            started = time.monotonic()
            tts = await self._tts.run({
                **record,
                "failure_text": speech,
                "llm_speech_sha256": speech_sha256,
            })
            _validate_stage(tts, "tts", session_id)
            if tts.get("playback_complete") is not True:
                raise CandidateViolation("Gate 2B TTS playback did not complete")
            trace["timings_ms"]["tts_playback"] = _elapsed_ms(started)
            trace["completed_stages"].append("tts_playback")
            stage_window["stage_ends_monotonic_s"]["tts_playback"] = time.monotonic()
            trace["timings_ms"]["end_to_end"] = _elapsed_ms(session_started)
            return CombinedSession(
                session_id=session_id,
                audio_fixture_id=record["fixture_id"],
                tts_fixture_id=record["tts_fixture_id"],
                vad={
                    "terminal": "SUCCESS",
                    "bounded_sha256": vad["bounded_sha256"],
                },
                asr={
                    "terminal": "SUCCESS",
                    "transcript_sha256": transcript_sha256,
                    "latency_ms": asr["latency_ms"],
                },
                llm={
                    "terminal": "SUCCESS",
                    "request_id": llm["request_id"],
                    "response_sha256": llm["response_sha256"],
                    "speech_sha256": speech_sha256,
                    "prior_marker_leaked": False,
                    "current_marker_present_once": True,
                    "current_trap_absent": True,
                    "metrics": llm["metrics"],
                },
                tts={
                    "terminal": "SUCCESS",
                    "pcm_sha256": tts["pcm_sha256"],
                    "sample_count": tts["sample_count"],
                    "playback_complete": True,
                    "input_speech_sha256": speech_sha256,
                },
                timings_ms=dict(trace["timings_ms"]),
            )
        except BaseException as error:
            trace["error_type"] = type(error).__name__
            trace["timings_ms"]["elapsed_before_error"] = _elapsed_ms(session_started)
            raise


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _elapsed_ms(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 3)


def _validate_record(record: object) -> None:
    required = {
        "session_id", "fixture_id", "tts_fixture_id", "filename", "sha256",
        "wav_path",
    }
    if not isinstance(record, dict) or not required <= set(record):
        raise ValueError("Gate 2B Audio fixture-lock record is incomplete")


def _validate_stage(stage: object, name: str, session_id: str) -> None:
    if (
        not isinstance(stage, dict)
        or stage.get("session_id") != session_id
        or stage.get("terminal") != "SUCCESS"
    ):
        raise CandidateViolation(f"Gate 2B {name} stage identity/terminal mismatch")
