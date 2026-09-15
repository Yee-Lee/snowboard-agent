#!/usr/bin/env python3
"""Canonical M4B single-PV runner and independent product-verification commands."""
from __future__ import annotations

import argparse
import asyncio
from array import array
import io
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import Mapping
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.m4b_measurement import (_Components, _DiagnosticAudioInput,
    _DiagnosticRecorder, _MeasurementObserver, _native_cleanup_proven)
from sbd.core.events import ActionCompleted, ErrorOccurred, LLMResponse, PerceptionResult

TARGET_ID = "pi5-4gb-debian13-aarch64-cp3135"
PV_TEST_IDS = (
    "M4B-PI-ATT-001", "M4B-PI-SEM-001", "M4B-PI-CONV-001",
    "M4B-PI-MEM-001", "M4B-PI-WAKE-001", "M4B-PI-TIME-001",
    "M4B-PI-RES-001",
)
DEVELOPER_REVIEW_CATEGORIES = {
    "M4B-PI-ATT-001": ("target_facts", "file_identity", "prompt_schema_profile", "ready"),
    "M4B-PI-CONV-001": ("inputs_outputs", "token_metrics", "lifecycle_identity", "cleanup"),
    "M4B-PI-MEM-001": ("resource_samples", "lifecycle_boundaries", "formula", "estimates"),
    "M4B-PI-WAKE-001": ("trace_events", "timestamps", "barriers", "component_activity"),
    "M4B-PI-TIME-001": ("clock_mapping", "timestamps_deltas", "pipeline_outputs", "null_reasons"),
    "M4B-PI-RES-001": ("network", "resource_values", "process_cleanup_recovery", "privacy_persistence"),
}
SEMANTIC_CASES = {
    "S01-IDENTITY": "你是誰？",
    "S02-ENGLISH": "想要英文進步應該怎麼做？",
    "S03-SEVEN-DAYS": "為什麼一個星期有七天？",
}
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
AGGREGATE_CASES = {
    "M4B-PI-WAKE-001": (
        "W01-OPEN-FIRST", "W02-ACK-FIRST", "W03-SLOW-OPEN",
        "W04-INTERRUPT-OPEN",
    ),
    "M4B-PI-RES-001": (
        "R01-OFFLINE", "R02-HEALTH", "R03-PID", "R04-NORMAL-CLOSE",
        "R05-RECOVERY", "R06-FORCED-CLEANUP", "R07-SHUTDOWN",
        "R08-PRIVACY",
    ),
}


class PVError(RuntimeError):
    pass


class _QuarterVolumeAudioOutput:
    """Runner-only 25% gain for 16 kHz mono S16_LE TTS playback."""

    def __init__(self, source: object) -> None:
        self._source = source

    @property
    def _observe(self):
        return self._source._observe

    @_observe.setter
    def _observe(self, value) -> None:
        self._source._observe = value

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    @staticmethod
    def _scale(chunk: bytes) -> bytes:
        if type(chunk) is not bytes or len(chunk) % 2:
            raise ValueError("PV audio gain requires complete S16_LE samples")
        samples = array("h")
        samples.frombytes(chunk)
        if sys.byteorder != "little":
            samples.byteswap()
        for index, sample in enumerate(samples):
            samples[index] = sample // 4 if sample >= 0 else -((-sample) // 4)
        if sys.byteorder != "little":
            samples.byteswap()
        return samples.tobytes()

    async def play(self, pcm) -> None:
        async def scaled():
            async for chunk in pcm:
                yield self._scale(chunk)

        await self._source.play(scaled())


class _DiagnosticResourceSampler:
    """Preserve sampler failures in the private PV partition before fail-closed redaction."""

    def __init__(self, sampler: object, recorder: _DiagnosticRecorder) -> None:
        self._sampler = sampler
        self._recorder = recorder

    def _call(self, method: str, **kwargs):
        try:
            return getattr(self._sampler, method)(**kwargs)
        except BaseException as error:
            self._recorder.error("resource_sample_failed", error)
            raise

    def sample(self, *, child_pid: int, child_pgid: int):
        return self._call("sample", child_pid=child_pid, child_pgid=child_pgid)

    def rebase_llm_owner(self, *, child_pid: int, child_pgid: int):
        return self._call("rebase_llm_owner", child_pid=child_pid, child_pgid=child_pgid)

    def validate_sample(self, sample: object, previous: object) -> None:
        try:
            self._sampler.validate_sample(sample, previous)
        except BaseException as error:
            self._recorder.error("resource_sample_validation_failed", error)
            raise

    def __getattr__(self, name: str):
        return getattr(self._sampler, name)


class _FixedAudioInput:
    """One-use, bound PCM WAV AudioInput for the automated TIME sub-run."""

    def __init__(self, path: Path, recorder: _DiagnosticRecorder) -> None:
        path = path.absolute()
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or not 44 <= info.st_size <= 32 * 1024**2:
                    raise ValueError
                raw = b""
                while len(raw) <= 32 * 1024**2:
                    block = os.read(descriptor, 1024 * 1024)
                    if not block:
                        break
                    raw += block
            finally:
                os.close(descriptor)
            with wave.open(io.BytesIO(raw), "rb") as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate(),
                        source.getcomptype()) != (1, 2, 16000, "NONE"):
                    raise ValueError
                frames = source.readframes(source.getnframes())
                if not frames or len(frames) % 640 or source.readframes(1):
                    raise ValueError
        except (OSError, EOFError, wave.Error, ValueError):
            raise PVError("M4B_PV_AUDIO_FIXTURE_INVALID") from None
        self.path = path
        self.raw = raw
        self.pcm = frames
        self.recorder = recorder
        self.started = False
        self.used = False
        self.frame_pull_count = 0

    async def start(self) -> None:
        if self.started or self.used:
            raise PVError("M4B_PV_AUDIO_FIXTURE_INVALID")
        self.started = True
        self.recorder.record("fixed_audio_ready", size_bytes=len(self.raw),
                             sha256=hashlib.sha256(self.raw).hexdigest())

    async def stop(self) -> None:
        self.started = False

    def frames(self):
        if not self.started or self.used:
            raise PVError("M4B_PV_AUDIO_FIXTURE_INVALID")
        self.used = True

        async def stream():
            pulled = 0
            try:
                for offset in range(0, len(self.pcm), 640):
                    chunk = self.pcm[offset:offset + 640]
                    pulled += len(chunk)
                    self.frame_pull_count += 1
                    yield chunk
            finally:
                self.recorder.record("fixed_audio_consumed",
                    pcm_bytes=pulled, frames=self.frame_pull_count,
                    complete=pulled == len(self.pcm))

        return stream()


class _WakeTrace:
    """Private, monotonic trace for the production wake-path barrier assertions."""

    ACTIVITY_STAGES = frozenset({
        "listen_started", "audio_frame_pull", "asr_started",
        "perception_fact", "reasoner_admission",
    })

    def __init__(self, recorder: _DiagnosticRecorder) -> None:
        self.recorder = recorder
        self.rows: list[dict[str, object]] = []
        self.activity: list[dict[str, object]] = []
        self.changed = asyncio.Event()

    def mark(self, stage: str, **values: object) -> int:
        monotonic_ns = time.monotonic_ns()
        row = {"stage": stage, "monotonic_ns": monotonic_ns, **values}
        self.rows.append(row)
        if stage in self.ACTIVITY_STAGES:
            self.activity.append(row)
        self.recorder.record("wake_trace", trace=row)
        self.changed.set()
        return monotonic_ns


class _WakeFrameStream:
    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace
        self._pulled = False

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if not self._pulled:
            self._trace.mark("audio_frame_pull")
            self._pulled = True
        return await anext(self._source)

    async def aclose(self) -> None:
        close = getattr(self._source, "aclose", None)
        if callable(close):
            await close()


class _WakeAudioInput:
    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace

    @property
    def _executor(self):
        return self._source._executor

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    def frames(self):
        return _WakeFrameStream(self._source.frames(), self._trace)


class _WakeASR:
    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    async def abort(self) -> None:
        await self._source.abort()

    async def force_abort(self):
        return await self._source.force_abort()

    async def transcribe(self, frames):
        self._trace.mark("asr_started")
        return await self._source.transcribe(frames)

    def __getattr__(self, name: str):
        return getattr(self._source, name)


class _WakeListen:
    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    async def abort(self) -> None:
        await self._source.abort()

    async def force_abort(self):
        return await self._source.force_abort()

    async def perceive(self, *args, **kwargs) -> None:
        self._trace.mark("listen_started")
        await self._source.perceive(*args, **kwargs)


class _WakeReasoner:
    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace
        self._product = getattr(source, "_product", False)

    async def start(self) -> None:
        await self._source.start()

    async def stop(self) -> None:
        await self._source.stop()

    async def abort(self) -> None:
        await self._source.abort()

    async def force_abort(self):
        return await self._source.force_abort()

    async def reason(self, *args, **kwargs) -> None:
        self._trace.mark("reasoner_admission")
        await self._source.reason(*args, **kwargs)


class _WakeConversationControl:
    """Hold only the existing OPEN start/join barriers; delegate all product work."""

    def __init__(self, source, trace: _WakeTrace) -> None:
        self._source = source
        self._trace = trace
        self.start_release = asyncio.Event()
        self.join_release = asyncio.Event()
        self.open_started = asyncio.Event()
        self.native_ready = asyncio.Event()
        self.joined = asyncio.Event()
        self.interrupt_closed = asyncio.Event()
        self._claim: tuple[str, int] | None = None
        self._ready = None
        self._interrupted = False
        self._close_lock = asyncio.Lock()
        self._close_proof = None

    @property
    def recovery_pending(self):
        return getattr(self._source, "recovery_pending", False)

    async def open_conversation(self, session_id: str, generation: int):
        self._claim = (session_id, generation)
        self._trace.mark("open_started", generation=generation)
        self.open_started.set()
        await self.start_release.wait()
        ready = await self._source.open_conversation(session_id, generation)
        self._ready = ready
        self._trace.mark("conversation_native_ready", generation=generation)
        self.native_ready.set()
        await self.join_release.wait()
        if self._interrupted:
            await self._close_once("session_interrupt")
            self.interrupt_closed.set()
            return ready
        self._trace.mark("conversation_joined", generation=generation)
        self.joined.set()
        return ready

    async def _close_once(self, reason: str):
        async with self._close_lock:
            if self._close_proof is None:
                if self._claim is None:
                    raise PVError("M4B_PV_WAKE_CLOSE_UNPROVEN")
                self._close_proof = await self._source.close_conversation(
                    *self._claim, reason)
                self._trace.mark("conversation_closed", reason=reason)
            return self._close_proof

    async def close_conversation(self, session_id: str, generation: int, reason: str):
        if self._claim != (session_id, generation):
            raise PVError("M4B_PV_WAKE_CLOSE_UNPROVEN")
        return await self._close_once(reason)

    async def authorize_recovery(self, *args, **kwargs):
        return await self._source.authorize_recovery(*args, **kwargs)

    async def abort(self) -> None:
        if self.native_ready.is_set() and not self.joined.is_set():
            self._interrupted = True
            self.join_release.set()
            await self.interrupt_closed.wait()
            return
        self.start_release.set()
        self.join_release.set()
        await self._source.abort()

    async def force_abort(self):
        self.start_release.set()
        self.join_release.set()
        return await self._source.force_abort()


def _identifier(value: str, name: str) -> str:
    if type(value) is not str or ID_PATTERN.fullmatch(value) is None:
        raise PVError(f"M4B_PV_{name}_INVALID")
    return value


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _write_json(path: Path, value: object, *, mode: int) -> None:
    path = path.absolute()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_bytes(path: Path, value: bytes, *, mode: int) -> None:
    path = path.absolute()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_json(path: Path, *, max_bytes: int = 1024 * 1024) -> dict[str, object]:
    if max_bytes not in {1024 * 1024, 16 * 1024 * 1024}:
        raise PVError("M4B_PV_INSPECTION_CATALOG_INVALID")
    error_code = ("M4B_PV_BINDING_INVALID" if max_bytes == 1024 * 1024
                  else "M4B_PV_INSPECTION_CATALOG_INVALID")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= max_bytes:
            raise PVError(error_code)
        raw = b""
        while len(raw) <= max_bytes:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(descriptor)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PVError(error_code) from None
    if type(value) is not dict:
        raise PVError(error_code)
    return value


def _json_value(value: object):
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_json_value(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    return value


def _empty_directory(path: Path, *, private: bool) -> Path:
    path = path.absolute()
    if path.exists():
        if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
            raise PVError("M4B_PV_PARTITION_NOT_EMPTY")
    else:
        path.mkdir(parents=True, mode=0o700 if private else 0o755)
    mode = stat.S_IMODE(path.stat().st_mode)
    if private and mode & 0o077:
        raise PVError("M4B_PV_PRIVATE_PERMISSIONS_INVALID")
    if not private and mode & 0o022:
        raise PVError("M4B_PV_PUBLIC_PERMISSIONS_INVALID")
    return path.resolve(strict=True)


def _target_paths() -> dict[str, str]:
    value = os.environ.get("SBD_M4B_PV_TARGET_ROOT")
    if not value:
        raise PVError("M4B_PV_TARGET_ROOT_MISSING")
    target = Path(value).resolve(strict=True)
    paths = {
        "target_root": target,
        "audio_config": target / "input/audio-config.yaml",
        "runtime_python": target / "input/llm-runtime/bin/python",
        "model": target / "input/gemma-4-E2B-it.litertlm",
        "artifact_lock": target / "input/llm-runtime/llm-artifacts.json",
        "product_profile": ROOT / "requirements/m4b/product-profile.json",
    }
    for name, path in paths.items():
        if name == "target_root":
            continue
        if path.is_symlink() or not path.is_file():
            raise PVError("M4B_PV_TARGET_INPUT_MISSING")
    return {name: str(path) for name, path in paths.items()}


def _target_facts() -> dict[str, object]:
    try:
        system = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines()
                      if "=" in line)
        model = Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
        memory = Path("/proc/meminfo").read_text()
        total = int(re.search(r"^MemTotal:\s+(\d+) kB$", memory, re.MULTILINE).group(1)) * 1024
        facts = {
            "target_identity": TARGET_ID,
            "board": model,
            "os_id": system["ID"].strip('"'),
            "os_version": system["VERSION_ID"].strip('"'),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "mem_total_bytes": total,
        }
        if ("Raspberry Pi 5" not in model or facts["os_id"] != "debian"
                or facts["os_version"] != "13" or facts["machine"] != "aarch64"
                or facts["python"] != "3.13.5" or facts["implementation"] != "CPython"
                or not 3 * 1024**3 <= total <= 4 * 1024**3):
            raise ValueError
        return facts
    except Exception:
        raise PVError("M4B_PV_TARGET_IDENTITY_INVALID") from None


def _expected_tuple(profile: Mapping[str, object]) -> dict[str, object]:
    from sbd.cognition.litert_lm.measurement import protected_content_digest
    return {
        "schema_version": 1,
        "harness_sha256": _sha256(Path(__file__)),
        "content_sha256": protected_content_digest(ROOT),
        "profile_sha256": profile["profile_sha256"],
        "target_identity": TARGET_ID,
    }


def _attest(paths: Mapping[str, str], private_directory: Path):
    from sbd.cognition.factory import _validate_shape
    from sbd.cognition.litert_lm.lock import LLMArtifactLock, load_product_profile
    from sbd.cognition.litert_lm.measurement import MeasurementGrant
    from sbd.core.config.models import LLMConfig
    profile = load_product_profile(Path(paths["product_profile"]), allow_measurement=True)
    if (profile["profile_stage"] != "measurement"
            or profile["min_mem_available_speak_bytes"] is not None
            or profile["min_mem_available_generate_bytes"] is not None):
        raise PVError("M4B_PV_PROFILE_INVALID")
    expected = _expected_tuple(profile)
    grant = MeasurementGrant.pv(expected_tuple=expected, profile=profile,
                                private_directory=private_directory)
    cfg = LLMConfig(driver="litert_lm", runtime_python=Path(paths["runtime_python"]),
        model_path=Path(paths["model"]), product_profile_path=Path(paths["product_profile"]),
        artifact_lock_path=Path(paths["artifact_lock"]), profile_id=profile["profile_id"])
    _validate_shape(cfg)
    lock = LLMArtifactLock.load(Path(paths["artifact_lock"]), repo_root=ROOT)
    lock.runtime_closure.verify_install(Path(paths["runtime_python"]).parent.parent /
                                        "lib/python3.13/site-packages")
    verified = lock.verify_config_paths(cfg, allow_measurement=True)
    if verified["profile_sha256"] != profile["profile_sha256"]:
        raise PVError("M4B_PV_PROFILE_INVALID")
    return profile, expected, grant, cfg, replace(lock,
        identity=lock.ready_identity(profile), product_profile=profile)


def _init(args) -> int:
    pv_run_id = _identifier(args.pv_run_id, "RUN_ID")
    public_root = _empty_directory(args.public_root, private=False)
    private_root = _empty_directory(args.private_root, private=True)
    binding_path = args.binding_manifest.absolute()
    if binding_path.exists() or binding_path.is_relative_to(ROOT):
        raise PVError("M4B_PV_BINDING_INVALID")
    if binding_path.parent.resolve(strict=True) not in {private_root, private_root.parent}:
        raise PVError("M4B_PV_BINDING_INVALID")
    paths = _target_paths()
    profile, expected, _grant, _cfg, lock = _attest(paths, private_root)
    facts = _target_facts()
    try:
        base_sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=15, check=True, text=True).stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", base_sha) is None:
            raise ValueError
    except Exception:
        raise PVError("M4B_PV_CONTENT_IDENTITY_INVALID") from None
    binding = {
        "schema_version": 1,
        "pv_run_id": pv_run_id,
        "public_root": str(public_root),
        "private_root": str(private_root),
        "paths": paths,
        "expected_tuple": expected,
        "target_facts": facts,
        "artifact_lock_sha256": lock.digest,
        "base_sha": base_sha,
        "status": "Initialized",
    }
    _write_json(binding_path, binding, mode=0o600)
    public = {key: binding[key] for key in ("schema_version", "pv_run_id", "expected_tuple",
                                             "target_facts", "artifact_lock_sha256", "base_sha", "status")}
    _write_json(public_root / "pv-init.json", public, mode=0o644)
    print(json.dumps({"status": "Initialized", "pv_run_id": pv_run_id,
                      "binding_manifest": str(binding_path),
                      "public_card": str(public_root / "pv-init.json")}, sort_keys=True))
    return 0


def _load_binding(args) -> tuple[dict[str, object], Path, Path]:
    binding = _read_json(args.binding_manifest.absolute())
    required = {"schema_version", "pv_run_id", "public_root", "private_root", "paths",
                "expected_tuple", "target_facts", "artifact_lock_sha256", "base_sha", "status"}
    if (set(binding) != required or binding["schema_version"] != 1
            or binding["status"] != "Initialized" or binding["pv_run_id"] != args.pv_run_id):
        raise PVError("M4B_PV_BINDING_INVALID")
    public_root = Path(binding["public_root"]).resolve(strict=True)
    private_root = Path(binding["private_root"]).resolve(strict=True)
    if (stat.S_IMODE(private_root.stat().st_mode) & 0o077
            or stat.S_IMODE(public_root.stat().st_mode) & 0o022):
        raise PVError("M4B_PV_BINDING_INVALID")
    if _target_facts() != binding["target_facts"]:
        raise PVError("M4B_PV_TARGET_IDENTITY_INVALID")
    profile, expected, _grant, _cfg, lock = _attest(binding["paths"], private_root)
    if expected != binding["expected_tuple"] or lock.digest != binding["artifact_lock_sha256"]:
        raise PVError("M4B_PV_BINDING_DRIFT")
    return binding, public_root, private_root


def _partition(path: Path, root: Path, *, private: bool) -> Path:
    value = path.absolute()
    if not value.is_relative_to(root):
        raise PVError("M4B_PV_PARTITION_OUTSIDE_ROOT")
    return _empty_directory(value, private=private)


def _build_components(binding: Mapping[str, object], private: Path,
                      recorder: _DiagnosticRecorder, *, recovery=None):
    from sbd.action.payload_validator import ActionPayloadValidator
    from sbd.action.speak import make_tts_adapter
    from sbd.action.speak.speaker import Speak
    from sbd.action.tool.registry import ToolRegistry
    from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
    from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler
    from sbd.cognition.prompt_builder import ListenProjector
    from sbd.cognition.reasoner import Reasoner
    from sbd.core._m4b_resource_binding import _M4BResourceBinding, _pi_temperature, _pi_throttled
    from sbd.core.audio import make_audio_input, make_audio_output
    from sbd.core.config.loader import load_config
    from sbd.core.event_bus import EventBus
    from sbd.perception.listen import make_asr_adapter
    from sbd.perception.listen.listener import Listen
    paths = binding["paths"]
    config = load_config(local_path=Path(paths["audio_config"]), dotenv_path=Path("/dev/null"), environ={})
    if (config.cognition.llm.driver != "mock" or config.core.audio.driver != "alsa"
            or config.perception.default_perceptions != ("listen",)
            or not config.perception.listen.enabled or config.perception.read.enabled
            or config.perception.look.enabled or not config.action.speak.enabled
            or not config.action.rest.enabled or config.action.tool.enabled
            or config.perception.listen.adapter.driver != "whispercpp"
            or config.action.tts.driver != "sherpa_matcha"):
        raise PVError("M4B_PV_AUDIO_CONFIG_INVALID")
    profile, expected, grant, cfg, lock = _attest(paths, private)
    audio_input = make_audio_input(config.core.audio)
    audio_output = _QuarterVolumeAudioOutput(make_audio_output(config.core.audio))
    audio_input = _DiagnosticAudioInput(audio_input, recorder)
    asr = make_asr_adapter(config.perception.listen.adapter)
    tts = make_tts_adapter(config.action.tts)
    binding_owner = _M4BResourceBinding(asr=asr, tts=tts, native_asr=True, native_tts=True)
    sampler = _DiagnosticResourceSampler(ProcLLMResourceSampler(
        ownership_registry=binding_owner,
        temperature=_pi_temperature, throttled=_pi_throttled), recorder)
    observer, bus = _MeasurementObserver(), EventBus()

    def forbidden_recovery(*_args, **_kwargs):
        raise PVError("M4B_PV_UNEXPECTED_RECOVERY")

    schedule_recovery = (forbidden_recovery if recovery is None
                         else recovery.begin_recovery)
    wait_recovery = forbidden_recovery if recovery is None else recovery.wait_recovery
    adapter = LiteRTLMAdapter(cfg, lock=lock, schedule_recovery=schedule_recovery,
        wait_recovery=wait_recovery, resource_sampler=sampler,
        observer=observer, measurement_grant=grant)
    if recovery is not None:
        recovery.bind(adapter)
    binding_owner.bind_llm(adapter)
    audio_output._observe = observer.mark
    listener = Listen(audio_input=audio_input, asr=asr, bus=bus, observe=observer.mark)
    speaker = Speak(tts=tts, audio_output=audio_output, bus=bus, observe=observer.mark)
    tools = ToolRegistry()
    tools.seal()
    reasoner = Reasoner(adapter, ListenProjector(), bus, lambda name: name in {"listen", "speak"},
        ActionPayloadValidator(tools=tools), observer=observer)
    return (_Components(adapter, listener, reasoner, speaker, audio_input, audio_output,
                        asr, tts, bus, sampler, observer),
            config.perception.timeout_seconds.listen, expected)


class _WakePathSession:
    """Exercise production wake preparation while controlling only its two barriers."""

    def __init__(self, components: _Components, config, recorder: _DiagnosticRecorder,
                 *, case_id: str, listen_timeout: float) -> None:
        from sbd.action.rest import Rest
        from sbd.core.display import DisplayArbiter, Oled128Renderer, make_display
        from sbd.core.display.status_bar import StatusBar
        from sbd.core.gpio.mock.driver import MockGPIO
        from sbd.core.config.models import GPIOPinConfig
        from sbd.core.resource_manager.catalog import WorkerCatalog
        from sbd.core.state_manager.manager import StateManager
        from sbd.input_events.button import ButtonInputSource
        from sbd.input_events.mock import MockWakeWordInputSource
        from sbd.perception.listen.listener import Listen

        self.c = components
        self.config = config
        self.recorder = recorder
        self.case_id = case_id
        self.listen_timeout = listen_timeout
        self.trace = _WakeTrace(recorder)
        self.control = _WakeConversationControl(components.adapter.control, self.trace)

        # The general PV builder adds a diagnostic recorder for human/semantic
        # runs. WAKE is automated and must neither prompt for speech nor persist
        # ambient PCM, so trace the real production AudioInput directly.
        production_audio_input = getattr(components.audio_input, "_source",
                                         components.audio_input)
        audio_input = _WakeAudioInput(production_audio_input, self.trace)
        asr = _WakeASR(components.asr, self.trace)
        listener = _WakeListen(Listen(audio_input=audio_input, asr=asr,
            bus=components.bus, observe=components.observer.mark), self.trace)
        reasoner = _WakeReasoner(components.reasoner, self.trace)
        components.audio_input = audio_input
        components.listener = listener
        components.reasoner = reasoner

        workers = WorkerCatalog()
        workers.register_perception("listen", listener)
        workers.set_reasoner(reasoner)
        workers.register_action("speak", components.speaker)
        self.rest = Rest(bus=components.bus)
        workers.register_action("rest", self.rest)
        workers.seal(("listen", "speak"))
        controlled_config = replace(config, wake=replace(config.wake, ack_seconds=60.0))
        self.sm = StateManager(config=controlled_config, bus=components.bus, workers=workers,
            action_validator=getattr(reasoner._source, "_action_validator"))

        self.gpio = MockGPIO()
        self.pin = GPIOPinConfig(pin=17, active_low=True, debounce_ms=5)
        self.button = ButtonInputSource(gpio=self.gpio, bus=components.bus,
            config=config.input_sources.button, pin_config=self.pin)
        self.wake = MockWakeWordInputSource(bus=components.bus)
        self.display = make_display(config.core.display)
        self.arbiter = DisplayArbiter(self.display, Oled128Renderer())
        self.status_bar = StatusBar(self.arbiter, components.bus)
        self.subscriptions = []
        self.native_started = []
        self.aux_started = []
        self.sm_started = False
        self.cleanup_proven = False
        self.product_facts: list[object] = []
        self.barrier_ns: dict[str, int] = {}

    async def _collect(self, event) -> None:
        from sbd.core.events import StateChanged
        if isinstance(event, StateChanged):
            self.trace.mark("state_changed", old=event.old, new=event.new)
        else:
            self.product_facts.append(event)
            self.trace.mark("product_fact", event_type=type(event).__name__)
            if isinstance(event, PerceptionResult):
                self.trace.mark("perception_fact", status=event.status)

    async def _wait(self, predicate, code: str, *, timeout: float = 15.0) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while not predicate():
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise PVError(code)
            self.trace.changed.clear()
            try:
                await asyncio.wait_for(self.trace.changed.wait(), min(remaining, 0.25))
            except TimeoutError:
                pass

    async def _wake_session(self) -> tuple[str, int]:
        await self._wait(lambda: self.sm.state == "WAKE" and self.sm._session is not None,
                         "M4B_PV_WAKE_NOT_OBSERVED")
        session = self.sm._session
        assert session is not None
        return session.session_id, session.conversation_generation

    async def _ack(self, session_id: str) -> int:
        from sbd.core.state_manager.notices import _WakeAckElapsed
        # This is the production barrier notice normally emitted by the SM timer;
        # the harness controls its ordering without changing SM/session state.
        self.sm._inbox.put_nowait(_WakeAckElapsed(session_id))
        await self._wait(lambda: self.sm._session is not None
                         and self.sm._session.wake_ack_ready,
                         "M4B_PV_WAKE_ACK_MISSING")
        value = self.trace.mark("wake_acknowledged")
        self.barrier_ns["wake_acknowledged"] = value
        return value

    async def _trigger(self, *, voice: bool) -> None:
        if voice:
            self.trace.mark("voice_wake_stimulus")
            await self.wake.emit()
            return
        self.trace.mark("gpio_wake_stimulus", pin=self.pin.pin)
        if not await self.gpio.simulate_event(self.pin.pin, "falling", at=1.0):
            raise PVError("M4B_PV_WAKE_GPIO_FAILED")
        if not await self.gpio.simulate_event(self.pin.pin, "rising", at=1.1):
            raise PVError("M4B_PV_WAKE_GPIO_FAILED")
        await self.gpio.wait_callbacks()

    def _assert_no_activity(self) -> None:
        if self.trace.activity:
            raise PVError("M4B_PV_WAKE_PREMATURE_ACTIVITY")

    async def _wait_active_path(self) -> None:
        required = _WakeTrace.ACTIVITY_STAGES
        await self._wait(lambda: required.issubset(
            {row["stage"] for row in self.trace.activity}),
            "M4B_PV_WAKE_ACTIVITY_MISSING", timeout=self.listen_timeout + 15.0)
        barrier = max(self.barrier_ns.values())
        if any(int(row["monotonic_ns"]) < barrier for row in self.trace.activity):
            raise PVError("M4B_PV_WAKE_PREMATURE_ACTIVITY")

    async def _wait_joined(self) -> int:
        await self._wait(lambda: self.control.joined.is_set()
                         and self.sm._session is not None
                         and self.sm._session.conversation_state == "ready",
                         "M4B_PV_WAKE_JOIN_MISSING")
        row = next(row for row in reversed(self.trace.rows)
                   if row["stage"] == "conversation_joined")
        value = int(row["monotonic_ns"])
        self.barrier_ns["conversation_joined"] = value
        return value

    async def _interrupt_to_idle(self) -> None:
        from sbd.core.events import InterruptRequested
        await self.c.bus.publish(InterruptRequested())
        await self._wait(lambda: self.sm.state == "IDLE" and self.sm._session is None,
                         "M4B_PV_WAKE_DRAIN_FAILED", timeout=20.0)

    def _display_proof(self) -> dict[str, object]:
        model = self.arbiter.snapshot()
        slots = [slot for slot, _hint in model.status_slots]
        if (slots != ["state"] or model.main is not None or model.fullscreen is not None
                or not self.arbiter._started or not self.arbiter._rendering_enabled):
            raise PVError("M4B_PV_WAKE_DISPLAY_CONTENT_INVALID")
        return {"device_class": type(self.display).__name__,
                "arbiter_class": type(self.arbiter).__name__,
                "status_owner_class": type(self.status_bar).__name__,
                "state_slot_only": True, "session_content_added": False}

    async def _start(self) -> None:
        from sbd.core.events import StateChanged
        for kind in (StateChanged, PerceptionResult, LLMResponse,
                     ActionCompleted, ErrorOccurred):
            self.subscriptions.append(self.c.bus.subscribe(
                kind, self._collect, name="m4b.pv.wake.collect"))
        for name, owner in (("audio_input", self.c.audio_input),
                            ("audio_output", self.c.audio_output),
                            ("listen", self.c.listener), ("speak", self.c.speaker),
                            ("reasoner", self.c.reasoner), ("rest", self.rest)):
            self.recorder.announce("WAKE_OWNER_STARTING", owner=name)
            self.native_started.append(owner)
            await owner.start()
            self.recorder.announce("WAKE_OWNER_READY", owner=name)
        for name, owner in (("display", self.display), ("display_arbiter", self.arbiter),
                            ("status_bar", self.status_bar), ("gpio", self.gpio),
                            ("button", self.button), ("voice_wake", self.wake)):
            self.aux_started.append(owner)
            await owner.start()
            self.trace.mark("aux_owner_ready", owner=name)
        self.sm.set_wake_listener(self.wake.control)
        await self.sm.start()
        self.sm_started = True
        self.sm.set_conversation_lifecycle(self.control)
        await self.button.arm()
        await self.wake.arm()
        self.sm.mark_input_producers_armed()

    async def _shutdown(self) -> None:
        from sbd.core.events import InterruptRequested, ShutdownRequested
        clean = True
        handles = [child for native in (self.c.asr, self.c.tts, self.c.adapter)
                   if (child := getattr(native, "_child", None)) is not None]
        if self.sm_started:
            try:
                if self.sm.state != "IDLE" or self.sm._session is not None:
                    await self.c.bus.publish(InterruptRequested())
                    await self._wait(lambda: self.sm.state == "IDLE"
                                     and self.sm._session is None,
                                     "M4B_PV_WAKE_DRAIN_FAILED", timeout=20.0)
                await self.c.bus.publish(ShutdownRequested())
                await asyncio.wait_for(self.sm.wait_stopped(), 10.0)
                await self.sm.stop()
            except BaseException as error:
                clean = False
                if not isinstance(error, asyncio.CancelledError):
                    self.recorder.error("wake_sm_stop_failed", error)
        for owner in reversed(self.aux_started):
            try:
                await owner.stop()
            except BaseException as error:
                clean = False
                if not isinstance(error, asyncio.CancelledError):
                    self.recorder.error("wake_aux_stop_failed", error)
        for owner in reversed(self.native_started):
            try:
                await owner.stop()
            except BaseException as error:
                clean = False
                if not isinstance(error, asyncio.CancelledError):
                    self.recorder.error("wake_owner_stop_failed", error)
        for subscription in self.subscriptions:
            self.c.bus.unsubscribe(subscription)
        self.subscriptions.clear()
        self.cleanup_proven = (clean and bool(handles)
                               and _native_cleanup_proven(self.c, handles))
        self.trace.mark("cleanup_complete", cleanup_proven=self.cleanup_proven)

    async def run(self) -> dict[str, object]:
        from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
        active_error = None
        try:
            await self._start()
            if self.case_id == "W01-OPEN-FIRST":
                self.control.start_release.set()
                self.control.join_release.set()
                await self._trigger(voice=False)
                session_id, _generation = await self._wake_session()
                await self._wait(lambda: self.control.native_ready.is_set(),
                                 "M4B_PV_WAKE_OPEN_MISSING")
                native_row = next(row for row in reversed(self.trace.rows)
                                  if row["stage"] == "conversation_native_ready")
                self.barrier_ns["conversation_native_ready"] = int(native_row["monotonic_ns"])
                join_ns = await self._wait_joined()
                self._assert_no_activity()
                ack_ns = await self._ack(session_id)
                if not join_ns < ack_ns:
                    raise PVError("M4B_PV_WAKE_ORDER_INVALID")
            elif self.case_id in {"W02-ACK-FIRST", "W03-SLOW-OPEN"}:
                await self._trigger(voice=self.case_id == "W02-ACK-FIRST")
                session_id, _generation = await self._wake_session()
                await self._wait(lambda: self.control.open_started.is_set(),
                                 "M4B_PV_WAKE_OPEN_MISSING")
                ack_ns = await self._ack(session_id)
                self._assert_no_activity()
                if self.case_id == "W03-SLOW-OPEN":
                    delay_started = time.monotonic_ns()
                    await asyncio.sleep(0.2)
                    self._assert_no_activity()
                    self.barrier_ns["bounded_open_delay_ns"] = time.monotonic_ns() - delay_started
                self.control.start_release.set()
                self.control.join_release.set()
                await self._wait(lambda: self.control.native_ready.is_set(),
                                 "M4B_PV_WAKE_OPEN_MISSING")
                native_row = next(row for row in reversed(self.trace.rows)
                                  if row["stage"] == "conversation_native_ready")
                native_ns = int(native_row["monotonic_ns"])
                self.barrier_ns["conversation_native_ready"] = native_ns
                join_ns = await self._wait_joined()
                if not ack_ns < native_ns <= join_ns:
                    raise PVError("M4B_PV_WAKE_ORDER_INVALID")
            elif self.case_id == "W04-INTERRUPT-OPEN":
                self.control.start_release.set()
                await self._trigger(voice=True)
                await self._wake_session()
                await self._wait(lambda: self.control.native_ready.is_set(),
                                 "M4B_PV_WAKE_OPEN_MISSING")
                self._assert_no_activity()
                await self._interrupt_to_idle()
                if (self.control.joined.is_set() or not self.control.interrupt_closed.is_set()
                        or self.trace.activity):
                    raise PVError("M4B_PV_WAKE_INTERRUPT_INVALID")
            else:
                raise PVError("M4B_PV_WAKE_CASE_INVALID")

            if self.case_id != "W04-INTERRUPT-OPEN":
                await self._wait_active_path()
                await self._interrupt_to_idle()
            display = self._display_proof()
            ready = self.control._ready
            if (not isinstance(ready, ConversationReady)
                    or self.control._claim != (ready.session_id, ready.generation)):
                raise PVError("M4B_PV_WAKE_OPEN_UNPROVEN")
            if self.case_id == "W04-INTERRUPT-OPEN":
                proof = self.control._close_proof
                if (not isinstance(proof, ConversationCloseProof)
                        or not (proof.request_terminal_proven and proof.cleanup_proven
                                and proof.engine_usable)):
                    raise PVError("M4B_PV_WAKE_CLOSE_UNPROVEN")
            return {"case_id": self.case_id, "barriers": dict(self.barrier_ns),
                    "activity": list(self.trace.activity), "trace": list(self.trace.rows),
                    "display": display, "production_path": {
                        "state_manager": type(self.sm).__name__,
                        "button_source": type(self.button).__name__,
                        "voice_wake_source": type(self.wake).__name__,
                        "audio_input": type(self.c.audio_input._source).__name__,
                        "asr": type(self.c.asr).__name__,
                        "conversation_control": type(self.control._source).__name__,
                    }}
        except BaseException as error:
            active_error = error
            raise
        finally:
            await self._shutdown()
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("wake_cleanup_failed", cleanup_error)


class _ResourceStructuralSession:
    """One fresh real-owner structural turn with resource and cleanup evidence."""

    def __init__(self, components: _Components, recorder: _DiagnosticRecorder, *,
                 text: str, redact_content: bool = False) -> None:
        self.c = components
        self.recorder = recorder
        self.text = text
        self.redact_content = redact_content
        self.session_id = uuid.uuid4().hex
        self.events: list[object] = []
        self.started: list[object] = []
        self.subscriptions = []
        self.handles: list[object] = []
        self.samples: list[dict[str, object]] = []
        self.process_blobs: list[tuple[str, bytes]] = []
        self.workdirs: list[str] = []
        self.cleanup_proven = False

    async def _collect(self, event) -> None:
        summary = {"event_type": type(event).__name__}
        if isinstance(event, PerceptionResult):
            summary["status"] = event.status
        elif isinstance(event, LLMResponse):
            summary.update(action_kind=event.action_kind,
                           post_action_route=event.post_action_route)
        elif isinstance(event, ActionCompleted):
            summary.update(kind=event.kind, status=event.status)
        elif isinstance(event, ErrorOccurred):
            summary["error"] = event.error
        self.recorder.record("resource_bus_event", **summary)
        self.events.append(event)

    def _take(self, kind):
        events, self.events = self.events, []
        if (any(isinstance(event, ErrorOccurred) for event in events)
                or len(events) != 1 or not isinstance(events[0], kind)):
            raise PVError("M4B_PV_RESOURCE_WORKER_FAILED")
        return events[0]

    def _sample(self, label: str) -> dict[str, object]:
        from scripts.m4b_target_metrics import MEASUREMENT_SAFETY_FLOOR_BYTES
        child = self.c.adapter._child
        if child is None:
            raise PVError("M4B_PV_RESOURCE_OWNER_MISSING")
        sample = self.c.sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
        if sample.mem_available_bytes < MEASUREMENT_SAFETY_FLOOR_BYTES:
            raise PVError("M4B_PV_RESOURCE_HEALTH_UNSAFE")
        row = {"label": label, "sample": _json_value(asdict(sample))}
        self.samples.append(row)
        self.recorder.record("resource_case_sample", label=label,
                             sample=row["sample"])
        return row

    def _snapshot_process_surfaces(self) -> None:
        for child in self.handles:
            pid = getattr(child, "pid", None)
            if type(pid) is not int or pid <= 0:
                raise PVError("M4B_PV_RESOURCE_OWNER_MISSING")
            for name in ("cmdline", "environ"):
                try:
                    value = (Path("/proc") / str(pid) / name).read_bytes()
                except OSError:
                    raise PVError("M4B_PV_RESOURCE_OWNER_MISSING") from None
                self.process_blobs.append((f"proc/{pid}/{name}", value))
            workdir = getattr(child, "_workdir", None)
            if workdir is None:
                workdir = getattr(child, "workdir", None)
            if workdir is not None:
                self.workdirs.append(str(workdir))

    def _snapshot_workdir_surfaces(self) -> None:
        """Retain case-owned temporary bytes in memory for the privacy scan."""
        total = 0
        for value in self.workdirs:
            root = Path(value)
            if not root.exists():
                continue
            if root.is_symlink() or not root.is_dir():
                raise PVError("M4B_PV_RESOURCE_WORKDIR_UNSAFE")
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise PVError("M4B_PV_RESOURCE_WORKDIR_UNSAFE")
                if not path.is_file():
                    continue
                size = path.stat().st_size
                total += size
                if size > 32 * 1024**2 or total > 128 * 1024**2:
                    raise PVError("M4B_PV_RESOURCE_WORKDIR_UNSAFE")
                try:
                    blob = path.read_bytes()
                except OSError:
                    raise PVError("M4B_PV_RESOURCE_WORKDIR_UNSAFE") from None
                self.process_blobs.append((f"workdir/{root.name}/{path.relative_to(root)}",
                                           blob))

    async def _sampled_operation(self, label: str, operation):
        task = asyncio.create_task(operation)
        try:
            await asyncio.sleep(0)
            while not task.done():
                self._sample(label)
                done, _pending = await asyncio.wait({task}, timeout=0.05)
                if done:
                    break
            return await task
        except BaseException:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def _start(self) -> None:
        for kind in (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred):
            self.subscriptions.append(self.c.bus.subscribe(
                kind, self._collect, name="m4b.pv.resource.collect"))
        for name, owner in (("audio_input", self.c.audio_input),
                            ("audio_output", self.c.audio_output),
                            ("asr", self.c.listener), ("tts", self.c.speaker),
                            ("llm", self.c.reasoner)):
            self.recorder.announce("RESOURCE_OWNER_STARTING", owner=name)
            self.started.append(owner)
            await owner.start()
            self.recorder.announce("RESOURCE_OWNER_READY", owner=name)
        self.handles = [child for native in (self.c.asr, self.c.tts, self.c.adapter)
                        if (child := getattr(native, "_child", None)) is not None]
        if len(self.handles) != 3:
            raise PVError("M4B_PV_RESOURCE_OWNER_MISSING")
        self._snapshot_process_surfaces()

    async def _cleanup(self) -> None:
        clean = True
        for owner in reversed(self.started):
            try:
                await owner.stop()
            except BaseException as error:
                clean = False
                if not isinstance(error, asyncio.CancelledError):
                    self.recorder.error("resource_owner_stop_failed", error)
        for subscription in self.subscriptions:
            self.c.bus.unsubscribe(subscription)
        self.subscriptions.clear()
        self.events.clear()
        self.cleanup_proven = (clean and len(self.handles) >= 3
                               and _native_cleanup_proven(self.c, self.handles))
        self.recorder.record("resource_cleanup_complete",
                             cleanup_proven=self.cleanup_proven)

    async def run(self) -> dict[str, object]:
        from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
        active_error = None
        try:
            await self._start()
            self._sample("engine_ready")
            ready = await self.c.adapter.control.open_conversation(self.session_id, 1)
            if (not isinstance(ready, ConversationReady)
                    or (ready.session_id, ready.generation) != (self.session_id, 1)):
                raise PVError("M4B_PV_RESOURCE_OPEN_UNPROVEN")
            self._sample("conversation_ready")
            perception = PerceptionResult("listen", "ok", self.text,
                session_id=self.session_id, turn_id=1, correlation_id=1)
            self.c.observer.operation_index = 1
            self.c.observer.generated_this_turn = False
            await self._sampled_operation("during_generation",
                self.c.reasoner.reason(self.session_id, 1, 1, (perception,), (),
                                       conversation_generation=1))
            response = self._take(LLMResponse)
            if (not self.c.observer.generated_this_turn
                    or response.action_kind != "speak"
                    or not response.action_payload.get("text")):
                raise PVError("M4B_PV_RESOURCE_GENERATION_FAILED")
            self._sample("post_generation")
            await self._sampled_operation("during_audio",
                self.c.speaker.execute(self.session_id, 1, 1,
                                       response.action_payload))
            action = self._take(ActionCompleted)
            if action.kind != "speak" or action.status != "ok":
                raise PVError("M4B_PV_RESOURCE_ACTION_FAILED")
            self._sample("audio_complete")
            proof = await self.c.adapter.control.close_conversation(
                self.session_id, 1, "session_end")
            if (not isinstance(proof, ConversationCloseProof)
                    or (proof.session_id, proof.generation) != (self.session_id, 1)
                    or not (proof.request_terminal_proven and proof.cleanup_proven
                            and proof.engine_usable)):
                raise PVError("M4B_PV_RESOURCE_CLOSE_UNPROVEN")
            self._sample("conversation_closed")
            self._snapshot_workdir_surfaces()
            input_summary = {"codepoints": len(self.text),
                "sha256": hashlib.sha256(self.text.encode()).hexdigest()}
            answer = str(response.action_payload["text"])
            answer_summary = {"codepoints": len(answer),
                "sha256": hashlib.sha256(answer.encode()).hexdigest()}
            result = {"ready": asdict(ready), "input": input_summary,
                "answer": answer_summary, "action": {
                    "kind": action.kind, "status": action.status},
                "close_proof": asdict(proof), "samples": list(self.samples),
                "owner_pid_count": len({process["pid"]
                    for row in self.samples for process in row["sample"]["processes"]}),
                "workdir_count": len(self.workdirs)}
            if not self.redact_content:
                result["private_content"] = {"input": self.text, "answer": answer}
            return result
        except BaseException as error:
            active_error = error
            raise
        finally:
            await self._cleanup()
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("resource_cleanup_failed", cleanup_error)


class _ResourceOwnerSession(_ResourceStructuralSession):
    """Fresh owner-only paths for forced cleanup and final shutdown cases."""

    async def run_forced_cleanup(self) -> dict[str, object]:
        from scripts.m4b_target_metrics import process_group_members
        from sbd.core.lifecycle import ForceAbortReport
        active_error = None
        try:
            await self._start()
            self._sample("engine_ready")
            llm = self.c.adapter._child
            assert llm is not None
            old_pid, old_pgid = llm.pid, llm.pgid
            before = sorted(process_group_members(old_pgid))
            if old_pid not in before:
                raise PVError("M4B_PV_RESOURCE_OWNER_MISSING")
            report = await self.c.adapter.force_abort()
            if (not isinstance(report, ForceAbortReport)
                    or report.destroyed_backends != ("backend.cognition.reasoner.llm",)
                    or process_group_members(old_pgid)
                    or self.c.adapter._child is not None):
                raise PVError("M4B_PV_RESOURCE_FORCED_CLEANUP_FAILED")
            self.recorder.record("forced_cleanup_complete", old_pid=old_pid,
                                 old_pgid=old_pgid, member_count=len(before))
            return {"old_pid": old_pid, "old_pgid": old_pgid,
                    "initial_member_count": len(before), "remaining_members": 0,
                    "destroyed_backends": list(report.destroyed_backends),
                    "rebuild_attempted": False}
        except BaseException as error:
            active_error = error
            raise
        finally:
            await self._cleanup()
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("resource_cleanup_failed", cleanup_error)

    async def run_shutdown(self) -> dict[str, object]:
        active_error = None
        stop_sampler = asyncio.Event()
        first_sample = asyncio.Event()
        sampler_task = None
        result = None

        async def sample_until_shutdown() -> None:
            while not stop_sampler.is_set():
                self._sample("live_shutdown_sampler")
                first_sample.set()
                try:
                    await asyncio.wait_for(stop_sampler.wait(), 0.05)
                except TimeoutError:
                    pass

        try:
            await self._start()
            sampler_task = asyncio.create_task(sample_until_shutdown(),
                                               name="m4b-pv-resource-sampler")
            await asyncio.wait_for(first_sample.wait(), 5.0)
            if sampler_task.done() or self.c.adapter._child is None:
                raise PVError("M4B_PV_RESOURCE_SHUTDOWN_FAILED")
            sample = self.samples[0]
            pids = sorted(process["pid"] for process in sample["sample"]["processes"])
            result = {"live_owner_pids": pids, "live_sampler": True,
                "live_child_count": len(self.handles),
                "shutdown_invoked_with_sampler_live": True}
            return result
        except BaseException as error:
            active_error = error
            raise
        finally:
            stop_sampler.set()
            if sampler_task is not None:
                await asyncio.gather(sampler_task, return_exceptions=True)
            await self._cleanup()
            if result is not None:
                sampler_stopped = (sampler_task is not None and sampler_task.done()
                    and not sampler_task.cancelled() and sampler_task.exception() is None)
                result["sampler_stopped"] = sampler_stopped
                if not sampler_stopped and active_error is None:
                    raise PVError("M4B_PV_RESOURCE_SHUTDOWN_FAILED")
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("resource_cleanup_failed", cleanup_error)


class _RecoveryCoordinator:
    """Case-local recovery owner used only after the real SM authorizes recovery."""

    def __init__(self, recorder: _DiagnosticRecorder, ledger: list[dict[str, object]]) -> None:
        self.recorder = recorder
        self.ledger = ledger
        self.adapter = None
        self.generation = 0
        self.old_pid = self.old_pgid = self.new_pid = None

    def _mark(self, stage: str, **values: object) -> None:
        row = {"stage": stage, "monotonic_ns": time.monotonic_ns(), **values}
        self.ledger.append(row)
        self.recorder.record("resource_recovery_trace", trace=row)

    def bind(self, adapter) -> None:
        if self.adapter is not None:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        self.adapter = adapter

    def begin_recovery(self, keys: tuple[str, ...]):
        from sbd.core.resource_manager.models import RecoveryTicket
        if keys != ("backend.cognition.reasoner.llm",) or self.adapter is None:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        self.generation += 1
        ticket = RecoveryTicket(self.generation, keys)
        self._mark("recovery_ticket", generation=ticket.generation, keys=list(keys))
        return ticket

    async def wait_recovery(self, ticket) -> None:
        from scripts.m4b_target_metrics import process_group_members
        if (self.adapter is None or ticket.generation != self.generation
                or ticket.keys != ("backend.cognition.reasoner.llm",)):
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        child = self.adapter._child
        if child is None:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        self.old_pid, self.old_pgid = child.pid, child.pgid
        self._mark("rebuild_start", old_pid=self.old_pid, old_pgid=self.old_pgid)
        await self.adapter.rebuild()
        replacement = self.adapter._child
        if (replacement is None or replacement.pid == self.old_pid
                or process_group_members(self.old_pgid)):
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        self.new_pid = replacement.pid
        self._mark("new_ready", new_pid=replacement.pid, new_pgid=replacement.pgid,
                   old_group_remaining=0)


class _RecoveryConversationControl:
    def __init__(self, source, mark) -> None:
        self._source = source
        self._mark = mark
        self.readies = []
        self.close_proofs = []
        self.authorization_count = 0

    @property
    def recovery_pending(self):
        return self._source.recovery_pending

    async def open_conversation(self, session_id, generation):
        self._mark("conversation_open_start", session_id=session_id,
                   generation=generation)
        ready = await self._source.open_conversation(session_id, generation)
        self.readies.append(ready)
        self._mark("conversation_ready", session_id=session_id, generation=generation)
        return ready

    async def close_conversation(self, session_id, generation, reason):
        self._mark("conversation_close_start", session_id=session_id,
                   generation=generation, reason=reason)
        proof = await self._source.close_conversation(session_id, generation, reason)
        self.close_proofs.append(proof)
        self._mark("conversation_close_proven", session_id=session_id,
                   generation=generation, reason=reason)
        return proof

    async def authorize_recovery(self, session_id, generation, proof):
        self.authorization_count += 1
        self._mark("sm_authorize_recovery", session_id=session_id,
                   generation=generation)
        await self._source.authorize_recovery(session_id, generation, proof)
        self._mark("sm_authorized_ready", session_id=session_id,
                   generation=generation)

    async def abort(self):
        return await self._source.abort()

    async def force_abort(self):
        return await self._source.force_abort()


class _RecoveryPerception:
    def __init__(self, bus, mark) -> None:
        self.bus, self._mark = bus, mark
        self.calls = 0
        self.release = asyncio.Event()

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def abort(self) -> None:
        self.release.set()

    async def force_abort(self):
        from sbd.core.lifecycle import ForceAbortReport
        self.release.set()
        return ForceAbortReport()

    async def perceive(self, session_id, turn_id, correlation_id, timeout_seconds) -> None:
        self.calls += 1
        if self.calls > 2:
            await self.release.wait()
            return
        self._mark("perception", session_id=session_id, turn_id=turn_id)
        await self.bus.publish(PerceptionResult("listen", "ok", "資源恢復測試",
            session_id=session_id, turn_id=turn_id, correlation_id=correlation_id))


class _RecoveryReasoner:
    _product = True

    def __init__(self, source, adapter, bus, mark, *, planned_recovery: bool = True) -> None:
        self.source, self.adapter, self.bus, self._mark = source, adapter, bus, mark
        self.planned_recovery = planned_recovery
        self.calls = 0
        self.following_done = asyncio.Event()
        self.following_succeeded = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def abort(self) -> None:
        return None

    async def force_abort(self):
        from sbd.core.lifecycle import ForceAbortReport
        return ForceAbortReport()

    async def reason(self, session_id, turn_id, correlation_id, results, pending,
                     *, conversation_generation) -> None:
        self.calls += 1
        if self.calls == 1 and self.planned_recovery:
            self.adapter.mark_recycle_pending(session_id, conversation_generation)
            self._mark("planned_recovery_marked", session_id=session_id,
                       generation=conversation_generation)
            self._mark("structural_response", session_id=session_id, turn_id=turn_id,
                       following=False, source="scripted_planned_condition")
            await self.bus.publish(LLMResponse(action_kind="speak",
                action_payload={"text": "正在進行資源恢復。"},
                post_action_route="END_SESSION", next_perceptions=(),
                session_id=session_id, turn_id=turn_id,
                correlation_id=correlation_id))
            return
        if self.calls == 1:
            self._mark("structural_response", session_id=session_id, turn_id=turn_id,
                       following=False, source="scripted_normal_close")
            await self.bus.publish(LLMResponse(action_kind="speak",
                action_payload={"text": "資源測試完成。"}, post_action_route="END_SESSION",
                next_perceptions=(), session_id=session_id, turn_id=turn_id,
                correlation_id=correlation_id))
            return
        if self.calls != 2 or not self.planned_recovery:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_ORDER_INVALID")
        observer = getattr(self.source, "_observer", None)
        if observer is None:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
        observer.generated_this_turn = False
        try:
            await self.source.reason(session_id, turn_id, correlation_id, results, pending,
                                     conversation_generation=conversation_generation)
            self.following_succeeded = observer.generated_this_turn is True
            self._mark("structural_response", session_id=session_id, turn_id=turn_id,
                       following=True, source="real_reasoner",
                       generated=self.following_succeeded)
        finally:
            self.following_done.set()


class _ResourceRecoverySession(_ResourceStructuralSession):
    """Actual SM action/rest/close authorization around one native LLM rebuild."""

    def __init__(self, components: _Components, config, recorder: _DiagnosticRecorder,
                 coordinator: _RecoveryCoordinator | None = None) -> None:
        from sbd.action.rest import Rest
        from sbd.core.resource_manager.catalog import WorkerCatalog
        from sbd.core.state_manager.manager import StateManager

        super().__init__(components, recorder, text="")
        self.ledger = [] if coordinator is None else coordinator.ledger
        self.coordinator = coordinator
        self.changed = asyncio.Event()
        self.perception = _RecoveryPerception(components.bus, self._mark)
        self.scripted_reasoner = _RecoveryReasoner(components.reasoner,
            components.adapter, components.bus, self._mark,
            planned_recovery=coordinator is not None)
        self.rest = Rest(bus=components.bus)
        workers = WorkerCatalog()
        workers.register_perception("listen", self.perception)
        workers.set_reasoner(self.scripted_reasoner)
        workers.register_action("speak", components.speaker)
        workers.register_action("rest", self.rest)
        workers.seal(("listen", "speak"))
        self.sm = StateManager(config=config, bus=components.bus, workers=workers,
            action_validator=components.reasoner._action_validator)
        self.control = _RecoveryConversationControl(components.adapter.control, self._mark)
        self.sm_started = False
        self.sm_stopped = False

    def _mark(self, stage: str, **values: object) -> None:
        row = {"stage": stage, "monotonic_ns": time.monotonic_ns(), **values}
        self.ledger.append(row)
        self.recorder.record("resource_recovery_trace", trace=row)
        self.changed.set()

    async def _trace_event(self, event) -> None:
        from sbd.core.events import StateChanged
        if isinstance(event, StateChanged):
            self._mark("state", old=event.old, new=event.new)
        elif isinstance(event, ActionCompleted):
            self._mark("action_complete", kind=event.kind, status=event.status,
                       session_id=event.session_id, turn_id=event.turn_id)

    async def _wait(self, predicate, code: str, timeout: float = 180.0) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while not predicate():
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise PVError(code)
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), min(remaining, 0.25))
            except TimeoutError:
                pass

    async def _wake_and_wait_idle(self) -> None:
        from sbd.core.events import ButtonPressed
        from sbd.core.state_manager.notices import _WakeAckElapsed
        await self.c.bus.publish(ButtonPressed("conversation", 1))
        await self._wait(lambda: self.sm.state == "WAKE" and self.sm._session is not None,
                         "M4B_PV_RESOURCE_RECOVERY_WAKE_FAILED")
        session = self.sm._session
        assert session is not None
        self.sm._inbox.put_nowait(_WakeAckElapsed(session.session_id))
        await self._wait(lambda: self.sm.state == "IDLE" and self.sm._session is None,
                         "M4B_PV_RESOURCE_RECOVERY_DRAIN_FAILED")

    async def _wake_following_turn(self) -> None:
        from sbd.core.events import ButtonPressed, InterruptRequested
        from sbd.core.state_manager.notices import _WakeAckElapsed
        await self.c.bus.publish(ButtonPressed("conversation", 1))
        await self._wait(lambda: self.sm.state == "WAKE" and self.sm._session is not None,
                         "M4B_PV_RESOURCE_RECOVERY_WAKE_FAILED")
        session = self.sm._session
        assert session is not None
        self.sm._inbox.put_nowait(_WakeAckElapsed(session.session_id))
        try:
            await asyncio.wait_for(self.scripted_reasoner.following_done.wait(), 180.0)
        except TimeoutError:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_FOLLOWING_FAILED") from None
        if not self.scripted_reasoner.following_succeeded:
            raise PVError("M4B_PV_RESOURCE_RECOVERY_FOLLOWING_FAILED")
        await self._wait(lambda: sum(row["stage"] == "action_complete"
            and row.get("kind") == "speak" for row in self.ledger) >= 2,
            "M4B_PV_RESOURCE_RECOVERY_FOLLOWING_FAILED")
        await asyncio.sleep(0.05)
        if self.sm.state != "IDLE" or self.sm._session is not None:
            await self.c.bus.publish(InterruptRequested())
        await self._wait(lambda: self.sm.state == "IDLE" and self.sm._session is None,
                         "M4B_PV_RESOURCE_RECOVERY_DRAIN_FAILED")

    async def run_normal_close(self) -> dict[str, object]:
        from sbd.core.events import ShutdownRequested, StateChanged
        from sbd.core.state_manager.ports import ConversationCloseProof
        active_error = None
        try:
            await self._start()
            for owner in (self.perception, self.scripted_reasoner, self.rest):
                await owner.start()
            self.subscriptions.append(self.c.bus.subscribe(
                StateChanged, self._trace_event, name="m4b.pv.resource.normal.state"))
            self.subscriptions.append(self.c.bus.subscribe(
                ActionCompleted, self._trace_event, name="m4b.pv.resource.normal.action"))
            await self.sm.start()
            self.sm_started = True
            self.sm.set_conversation_lifecycle(self.control)
            self.sm.mark_input_producers_armed()
            self._sample("engine_ready")
            await self._wake_and_wait_idle()
            self._sample("product_session_closed")
            await self.c.bus.publish(ShutdownRequested())
            await asyncio.wait_for(self.sm.wait_stopped(), 20.0)
            await self.sm.stop()
            self.sm_stopped = True
            proof = self.control.close_proofs[0] if len(self.control.close_proofs) == 1 else None
            stages = [row["stage"] for row in self.ledger]
            speak = next((index for index, row in enumerate(self.ledger)
                if row["stage"] == "action_complete" and row.get("kind") == "speak"), None)
            rest = next((index for index, row in enumerate(self.ledger)
                if row["stage"] == "action_complete" and row.get("kind") == "rest"), None)
            close = next((index for index, row in enumerate(self.ledger)
                          if row["stage"] == "conversation_close_proven"), None)
            if (not isinstance(proof, ConversationCloseProof)
                    or not (proof.request_terminal_proven and proof.cleanup_proven
                            and proof.engine_usable)
                    or speak is None or rest is None or close is None
                    or not speak < rest < close or self.scripted_reasoner.calls != 1
                    or self.control.authorization_count != 0
                    or "planned_recovery_marked" in stages):
                raise PVError("M4B_PV_RESOURCE_CLOSE_UNPROVEN")
            return {"close_proof": asdict(proof), "ledger": list(self.ledger),
                "samples": list(self.samples), "product_session_closed": True,
                "recovery_authorized": False}
        except BaseException as error:
            active_error = error
            raise
        finally:
            if self.sm_started and not self.sm_stopped:
                try:
                    await self.c.bus.publish(ShutdownRequested())
                    await asyncio.wait_for(self.sm.wait_stopped(), 20.0)
                    await self.sm.stop()
                    self.sm_stopped = True
                except BaseException as error:
                    if not isinstance(error, asyncio.CancelledError):
                        self.recorder.error("resource_normal_sm_stop_failed", error)
            await self._cleanup()
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("resource_cleanup_failed", cleanup_error)

    async def run(self) -> dict[str, object]:
        from sbd.core.events import ShutdownRequested, StateChanged
        active_error = None
        try:
            if self.coordinator is None:
                raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
            await self._start()
            for owner in (self.perception, self.scripted_reasoner, self.rest):
                await owner.start()
            self.subscriptions.append(self.c.bus.subscribe(
                StateChanged, self._trace_event, name="m4b.pv.resource.recovery.state"))
            self.subscriptions.append(self.c.bus.subscribe(
                ActionCompleted, self._trace_event, name="m4b.pv.resource.recovery.action"))
            await self.sm.start()
            self.sm_started = True
            self.sm.set_conversation_lifecycle(self.control)
            self.sm.mark_input_producers_armed()
            self._sample("engine_ready")
            await self._wake_and_wait_idle()
            replacement = self.c.adapter._child
            if replacement is None:
                raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
            self.handles.append(replacement)
            self._sample("recovery_ready")
            await self._wake_following_turn()
            self._sample("following_turn_closed")
            await self.c.bus.publish(ShutdownRequested())
            await asyncio.wait_for(self.sm.wait_stopped(), 20.0)
            await self.sm.stop()
            self.sm_stopped = True
            stages = [row["stage"] for row in self.ledger]
            required = ("planned_recovery_marked", "action_complete",
                        "conversation_close_proven", "sm_authorize_recovery",
                        "rebuild_start", "new_ready", "sm_authorized_ready")
            positions = []
            start = 0
            for stage in required:
                try:
                    position = stages.index(stage, start)
                except ValueError:
                    raise PVError("M4B_PV_RESOURCE_RECOVERY_ORDER_INVALID") from None
                positions.append(position)
                start = position + 1
            rest_position = next((index for index, row in enumerate(self.ledger)
                if row["stage"] == "action_complete" and row.get("kind") == "rest"), None)
            speak_position = next((index for index, row in enumerate(self.ledger)
                if row["stage"] == "action_complete" and row.get("kind") == "speak"), None)
            if (rest_position is None or speak_position is None
                    or not speak_position < rest_position < positions[2]
                    or self.scripted_reasoner.calls != 2
                    or self.coordinator.old_pid is None
                    or self.coordinator.new_pid is None):
                raise PVError("M4B_PV_RESOURCE_RECOVERY_ORDER_INVALID")
            return {"ledger": list(self.ledger), "samples": list(self.samples),
                "old_pid": self.coordinator.old_pid,
                "new_pid": self.coordinator.new_pid,
                "following_structural_turn": True,
                "following_source": "real_reasoner", "following_generated": True,
                "sm_authorization_count": 1,
                "new_ready": True}
        except BaseException as error:
            active_error = error
            raise
        finally:
            if self.sm_started and not self.sm_stopped:
                try:
                    await self.c.bus.publish(ShutdownRequested())
                    await asyncio.wait_for(self.sm.wait_stopped(), 20.0)
                    await self.sm.stop()
                    self.sm_stopped = True
                except BaseException as error:
                    if not isinstance(error, asyncio.CancelledError):
                        self.recorder.error("resource_recovery_sm_stop_failed", error)
            await self._cleanup()
            if not self.cleanup_proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("resource_cleanup_failed", cleanup_error)

class _SemanticSession:
    def __init__(self, components: _Components, recorder: _DiagnosticRecorder, *, timeout: float):
        self.c = components
        self.recorder = recorder
        self.timeout = timeout
        self.events = []
        self.started = []
        self.subscriptions = []
        self.session_id = uuid.uuid4().hex
        for kind in (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred):
            self.subscriptions.append(components.bus.subscribe(kind, self._collect,
                name="m4b.pv.semantic.collect"))

    async def _collect(self, event):
        self.recorder.record("bus_event", event_type=type(event).__name__, event=asdict(event))
        self.events.append(event)

    def _take(self, kind):
        events, self.events = self.events, []
        if (any(isinstance(event, ErrorOccurred) for event in events)
                or len(events) != 1 or not isinstance(events[0], kind)):
            raise PVError("M4B_PV_WORKER_FAILED")
        return events[0]

    async def run(self) -> dict[str, object]:
        from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
        c = self.c
        try:
            for name, owner in (("audio_input", c.audio_input), ("audio_output", c.audio_output),
                                ("asr", c.listener), ("tts", c.speaker), ("llm", c.reasoner)):
                self.recorder.announce("owner_starting", owner=name)
                self.started.append(owner)
                await owner.start()
                self.recorder.announce("owner_ready", owner=name)
            ready = await c.adapter.control.open_conversation(self.session_id, 1)
            if (not isinstance(ready, ConversationReady) or ready.session_id != self.session_id
                    or ready.generation != 1):
                raise PVError("M4B_PV_OPEN_UNPROVEN")
            self.recorder.record("conversation_ready", ready=asdict(ready))
            await c.listener.perceive(self.session_id, 1, 1, self.timeout)
            perception = self._take(PerceptionResult)
            self.recorder.record("perception_result", perception=asdict(perception))
            if perception.status != "ok" or not perception.text:
                raise PVError("M4B_PV_RECORDING_FAILED")
            await c.reasoner.reason(self.session_id, 1, 1, (perception,), (),
                                    conversation_generation=1)
            response = self._take(LLMResponse)
            self.recorder.record("llm_response", response=asdict(response))
            if (response.action_kind != "speak" or not response.action_payload.get("text")
                    or response.post_action_route != "KEEP_NEXT"
                    or response.next_perceptions != ("listen",)):
                raise PVError("M4B_PV_STRUCTURAL_RESPONSE_FAILED")
            await c.speaker.execute(self.session_id, 1, 1, response.action_payload)
            action = self._take(ActionCompleted)
            self.recorder.record("action_completed", action=asdict(action))
            if action.status != "ok":
                raise PVError("M4B_PV_ACTION_FAILED")
            proof = await c.adapter.control.close_conversation(self.session_id, 1, "session_end")
            if (not isinstance(proof, ConversationCloseProof)
                    or proof.session_id != self.session_id or proof.generation != 1
                    or proof.request_terminal_proven is not True
                    or proof.cleanup_proven is not True or proof.engine_usable is not True):
                raise PVError("M4B_PV_CLOSE_UNPROVEN")
            self.recorder.record("close_proof", proof=asdict(proof))
            print("[ASR] " + json.dumps(perception.text, ensure_ascii=False), flush=True)
            print("[回答] " + json.dumps(response.action_payload["text"], ensure_ascii=False), flush=True)
            return {"session_id": self.session_id, "perception": asdict(perception),
                    "response": asdict(response), "action": asdict(action), "close_proof": asdict(proof),
                    "ready_identity": dict(c.adapter._lock.identity.fields)}
        finally:
            active_error = sys.exc_info()[1]
            native_owners = ((c.listener, c.asr), (c.speaker, c.tts),
                             (c.reasoner, c.adapter))
            handles = [child for owner, native in native_owners if owner in self.started
                       if (child := getattr(native, "_child", None)) is not None]
            clean = True
            for owner in reversed(self.started):
                try:
                    await owner.stop()
                except Exception as error:
                    clean = False
                    self.recorder.error("owner_stop_failed", error)
            for subscription in self.subscriptions:
                c.bus.unsubscribe(subscription)
            self.events.clear()
            if not clean or not _native_cleanup_proven(c, handles):
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("cleanup_failed", cleanup_error)


def _human_verdict() -> str:
    while True:
        print("USER verdict [Pass/Fail]: ", end="", flush=True)
        value = sys.stdin.readline()
        if value == "":
            raise PVError("M4B_PV_HUMAN_VERDICT_MISSING")
        normalized = value.strip().lower()
        if normalized in {"pass", "p"}:
            return "Pass"
        if normalized in {"fail", "f"}:
            return "Fail"
        print("請輸入 Pass 或 Fail。", flush=True)


def _semantic_native_proof(private: Path, capture: Mapping[str, object]) -> dict[str, object]:
    from sbd.cognition.semantic import (
        RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256, validate_semantic,
    )

    child_events = sorted(private.glob("llm-child-*-events.jsonl"))
    if len(child_events) != 1:
        raise PVError("M4B_PV_NATIVE_PATH_UNPROVEN")
    try:
        rows = [json.loads(line) for line in child_events[0].read_text().splitlines()]
        formats = [row for row in rows if row.get("stage") == "response_format_selected"]
        outputs = [row for row in rows if row.get("stage") == "native_output"]
        stages = {row.get("stage") for row in rows}
        identity = capture["ready_identity"]
        response = capture["response"]
        if (len(formats) != 1 or formats[0].get("kind") != "json"
                or formats[0].get("response_schema_locator") != RESPONSE_SCHEMA_LOCATOR
                or formats[0].get("response_schema_sha256") != RESPONSE_SCHEMA_SHA256
                or len(outputs) != 1 or type(outputs[0].get("raw_json")) not in {str, dict}
                or not {"native_runtime_ready", "native_generate_returned",
                        "native_generate_metrics"}.issubset(stages)
                or type(identity) is not dict
                or identity.get("response_schema_locator") != RESPONSE_SCHEMA_LOCATOR
                or identity.get("response_schema_sha256") != RESPONSE_SCHEMA_SHA256
                or type(response) is not dict):
            raise ValueError
        semantic = validate_semantic(outputs[0]["raw_json"])
        if (not semantic.text or semantic.end is not False
                or response.get("action_kind") != "speak"
                or response.get("action_payload") != {"text": semantic.text}
                or response.get("post_action_route") != "KEEP_NEXT"):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise PVError("M4B_PV_NATIVE_PATH_UNPROVEN") from None
    return {"runtime": "litert-lm/Gemma", "response_format": "json",
            "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
            "response_schema_sha256": RESPONSE_SCHEMA_SHA256,
            "response_format_call_count": 1, "native_output_count": 1,
            "normalized_text": semantic.text, "end": semantic.end,
            "event_log_sha256": _sha256(child_events[0])}


def _run_semantic_case(args) -> int:
    if args.test_id != "M4B-PI-SEM-001" or args.case_id not in SEMANTIC_CASES:
        raise PVError("M4B_PV_SEMANTIC_CASE_INVALID")
    if args.utterance != SEMANTIC_CASES[args.case_id] or not args.fresh_setup or not args.fresh_conversation:
        raise PVError("M4B_PV_SEMANTIC_CASE_INVALID")
    for value, name in ((args.pv_run_id, "RUN_ID"), (args.sub_run_id, "SUB_RUN_ID"),
                        (args.case_attempt_id, "ATTEMPT_ID")):
        _identifier(value, name)
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    try:
        recorder.announce("PV_SEMANTIC_STARTING", test_id=args.test_id, case_id=args.case_id,
                          sub_run_id=args.sub_run_id, case_attempt_id=args.case_attempt_id)
        components, timeout, expected = _build_components(binding, private, recorder)
        capture = asyncio.run(_SemanticSession(components, recorder, timeout=timeout).run())
        native_proof = _semantic_native_proof(private, capture)
        capture.update(schema_version=1, test_id=args.test_id, case_id=args.case_id,
                       pv_run_id=args.pv_run_id, sub_run_id=args.sub_run_id,
                       case_attempt_id=args.case_attempt_id, expected_tuple=expected,
                       native_path_proof=native_proof)
        capture_path = private / "semantic-capture.json"
        _write_json(capture_path, capture, mode=0o600)
        capture_digest = _sha256(capture_path)
        card = {"schema_version": 1, "test_id": args.test_id, "case_id": args.case_id,
                "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
                "case_attempt_id": args.case_attempt_id, "expected_tuple": expected,
                "capture_sha256": capture_digest, "script_status": "Pass",
                "automated_status": "Pass",
                "user_verdict": None, "status": "NeedsHumanReview"}
        review_path = public / "capture.json"
        _write_json(review_path, card, mode=0o644)
        recorder.announce("NEEDS_HUMAN_REVIEW", case_id=args.case_id,
                          capture_sha256=capture_digest)
        print(json.dumps({"status": "NeedsHumanReview", "test_id": args.test_id,
                          "case_id": args.case_id, "public_card": str(review_path),
                          "private_capture": str(capture_path)}, sort_keys=True), flush=True)
        verdict = _human_verdict()
        card.update(user_verdict=verdict, status=verdict,
                    capture_card_sha256=_sha256(review_path))
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        recorder.record("USER_VERDICT", verdict=verdict, public_card_sha256=_sha256(card_path))
        print(json.dumps({"status": verdict, "test_id": args.test_id, "case_id": args.case_id,
                          "public_card": str(card_path), "private_capture": str(capture_path)},
                         sort_keys=True), flush=True)
        return 0 if verdict == "Pass" else 1
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_SEMANTIC_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id, "case_id": args.case_id,
                   "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
                   "case_attempt_id": args.case_attempt_id,
                   "expected_tuple": binding["expected_tuple"],
                   "script_status": "Incomplete", "status": "Incomplete",
                   "error_code": str(error) if isinstance(error, PVError) else "M4B_PV_SEMANTIC_FAILED"}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps({"status": "Incomplete", "test_id": args.test_id,
                          "case_id": args.case_id, "error_code": failure["error_code"]},
                         sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


def _obsolete_surface_absent() -> dict[str, bool]:
    needles = tuple(value.lower().encode() for value in (
        "pm" + "_complete", "pr" + "_complete", "ph" + "_complete",
        "complete" + "-pm", "validate" + "_pm_bundle", "seal" + "_pm_bundle",
        "freeze" + "_release_profile", "release" + "_run_sha256",
        "human" + "_repeat"))
    for root in (ROOT / "src", ROOT / "scripts"):
        for path in root.rglob("*"):
            if (not path.is_file() or path.is_symlink() or "__pycache__" in path.parts
                    or path.suffix not in {".py", ".sh"}):
                continue
            if any(needle in path.read_bytes().lower() for needle in needles):
                raise PVError("M4B_PV_OBSOLETE_STAGE_PRESENT")
    launchers = ("run-pi-one-turn.sh", "run-pi-two-turns.sh", "run-pi-voice.sh")
    if any((ROOT / "scripts" / name).exists() for name in launchers):
        raise PVError("M4B_PV_OBSOLETE_STAGE_PRESENT")
    def options(parser):
        result = {option for action in parser._actions for option in action.option_strings}
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict):
                for child in choices.values():
                    result.update(options(child))
        return result
    actions = options(_parser())
    obsolete_options = ("--" + "complete" + "-pm", "--" + "validate" + "-pm",
                        "--" + "release" + "-rerun", "--" + "ph")
    if any(option in actions for option in obsolete_options):
        raise PVError("M4B_PV_OBSOLETE_STAGE_PRESENT")
    return {"obsolete_completion_flags_absent": True,
            "obsolete_bundle_validators_absent": True,
            "obsolete_launchers_absent": True,
            "canonical_entry_only": True}


async def _att_engine_ready(binding: Mapping[str, object], private: Path,
                            recorder: _DiagnosticRecorder) -> dict[str, object]:
    from sbd.cognition.litert_lm.adapter import AdapterState
    components, _timeout, expected = _build_components(binding, private, recorder)
    children = []
    started = []
    try:
        for name, owner in (("asr", components.listener), ("tts", components.speaker),
                            ("llm", components.reasoner)):
            recorder.announce("ATT_OWNER_STARTING", owner=name)
            started.append(owner)
            await owner.start()
            recorder.announce("ATT_OWNER_READY", owner=name)
        child = components.adapter._child
        children = [getattr(owner, "_child", None)
                    for owner in (components.asr, components.tts, components.adapter)]
        if (components.adapter.state is not AdapterState.ENGINE_READY or child is None
                or any(owner is None for owner in children)
                or child.pid <= 0 or child.pgid != child.pid
                or components.adapter._ledger.claim is not None
                or components.adapter.conversation_revision != 0):
            raise PVError("M4B_PV_READY_INVALID")
        identity = dict(components.adapter._lock.identity.fields)
        if identity.get("conversation_state") != "none":
            raise PVError("M4B_PV_READY_INVALID")
        result = {"expected_tuple": expected, "ready_identity": identity,
                  "pid": child.pid, "pgid": child.pgid,
                  "adapter_state": components.adapter.state.name,
                  "conversation_claim": None, "conversation_revision": 0,
                  "prewarm_generations": 0}
        recorder.record("ATT_READY", **result)
        return result
    finally:
        active_error = sys.exc_info()[1]
        clean = True
        for owner in reversed(started):
            try:
                await owner.stop()
            except Exception as error:
                clean = False
                recorder.error("ATT_ENGINE_STOP_FAILED", error)
        live_handles = [child for child in children if child is not None]
        if (not clean or not live_handles
                or not _native_cleanup_proven(components, live_handles)):
            cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
            if active_error is None:
                raise cleanup_error
            recorder.error("ATT_CLEANUP_FAILED", cleanup_error)


def _run_att(args) -> int:
    if args.test_id != "M4B-PI-ATT-001" or not args.fresh_setup:
        raise PVError("M4B_PV_ATT_INPUT_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    _identifier(args.sub_run_id, "SUB_RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    try:
        from scripts.m4b_llm_product import capture_python_abi, validate_python_abi
        from sbd.cognition.semantic import (
            RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256,
            RESPONSE_SCHEMA_SIZE_BYTES, load_response_schema, validate_semantic,
        )
        profile, expected, _grant, _cfg, lock = _attest(binding["paths"], private)
        abi = capture_python_abi(Path("/usr/bin/python3.13"))
        validate_python_abi(abi)
        obsolete = _obsolete_surface_absent()
        ready = asyncio.run(_att_engine_ready(binding, private, recorder))
        if ready["expected_tuple"] != expected:
            raise PVError("M4B_PV_BINDING_DRIFT")
        worker_source = (ROOT / "src/sbd/cognition/litert_lm/worker.py").read_text()
        schema_path = ROOT / RESPONSE_SCHEMA_LOCATOR
        schema_bytes = schema_path.read_bytes()
        schema_mapping = load_response_schema(repo_root=ROOT)
        schema_facts = {"locator": RESPONSE_SCHEMA_LOCATOR,
            "size_bytes": len(schema_bytes), "final_lf": schema_bytes.endswith(b"\n"),
            "bom_absent": not schema_bytes.startswith(b"\xef\xbb\xbf"),
            "sha256": hashlib.sha256(schema_bytes).hexdigest(),
            "decoded_mapping": schema_mapping}
        semantic_proof = {"empty_false_rejected": False,
            "empty_true_accepted": validate_semantic({"text": "", "end": True}).text == "",
            "nonempty_false_accepted": validate_semantic({"text": "嗨", "end": False}).text == "嗨"}
        try:
            validate_semantic({"text": "", "end": False})
        except ValueError:
            semantic_proof["empty_false_rejected"] = True
        if (len(schema_bytes) != RESPONSE_SCHEMA_SIZE_BYTES
                or schema_facts["sha256"] != RESPONSE_SCHEMA_SHA256
                or not schema_facts["final_lf"] or not schema_facts["bom_absent"]
                or not all(semantic_proof.values())
                or profile.get("response_schema_locator") != RESPONSE_SCHEMA_LOCATOR
                or profile.get("response_schema_sha256") != RESPONSE_SCHEMA_SHA256
                or lock.product_profile.get("response_schema_locator") != RESPONSE_SCHEMA_LOCATOR
                or lock.product_profile.get("response_schema_sha256") != RESPONSE_SCHEMA_SHA256
                or ready["ready_identity"].get("response_schema_locator") != RESPONSE_SCHEMA_LOCATOR
                or ready["ready_identity"].get("response_schema_sha256") != RESPONSE_SCHEMA_SHA256
                or ".regex(" in worker_source or "semantic.gbnf" in worker_source
                or (ROOT / "requirements/m4b/semantic.gbnf").exists()):
            raise PVError("M4B_PV_RESPONSE_SCHEMA_IDENTITY_INVALID")
        child_events = sorted(private.glob("llm-child-*-events.jsonl"))
        if len(child_events) != 1:
            raise PVError("M4B_PV_CHILD_ATTESTATION_MISSING")
        stages = [json.loads(line)["stage"] for line in child_events[0].read_text().splitlines()]
        required_stages = {"artifact_lock_verified", "response_schema_verified",
                           "runtime_closure_verified",
                           "model_profile_verified", "network_denial_installed",
                           "native_runtime_ready", "ready_emitting"}
        if not required_stages.issubset(stages):
            raise PVError("M4B_PV_CHILD_ATTESTATION_MISSING")
        assertions = {"A01-NEW-ROOTS": "Pass", "A02-BOUND-TUPLE": "Pass",
                      "A03-target-runtime": "Pass", "A04-artifacts": "Pass",
                      "A05-profile-ready": "Pass", "A06-obsolete-stage-negative": "Pass"}
        manifest = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "partition_identity": {
                "public": str(public), "private": str(private)},
            "target_facts": binding["target_facts"], "python_abi": abi.as_dict(),
            "python_abi_sha256": abi.sha256, "artifact_lock_sha256": lock.digest,
            "runtime": dict(lock.runtime), "model": dict(lock.model),
            "runtime_files": [asdict(item) for item in lock.runtime_closure.files],
            "response_schema": schema_facts, "python_semantic_proof": semantic_proof,
            "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
            "response_schema_sha256": RESPONSE_SCHEMA_SHA256,
            "profile": dict(profile), "ready": ready, "child_event_stages": stages,
            "obsolete_surface": obsolete, "assertions": assertions,
            "cleanup_proven": True, "status": "Pass"}
        manifest_path = private / "att-manifest.json"
        _write_json(manifest_path, manifest, mode=0o600)
        card = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "artifact_lock_sha256": lock.digest,
            "python_abi_sha256": abi.sha256, "runtime_file_count": len(lock.runtime_closure.files),
            "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
            "response_schema_size_bytes": RESPONSE_SCHEMA_SIZE_BYTES,
            "response_schema_sha256": RESPONSE_SCHEMA_SHA256,
            "ready_identity_sha256": hashlib.sha256(_json_bytes(ready["ready_identity"])).hexdigest(),
            "manifest_sha256": _sha256(manifest_path), "assertions": assertions,
            "cleanup_proven": True, "script_status": "Pass",
            "status": "NeedsDeveloperReview"}
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        catalog_path = _write_inspection_catalog(test_id=args.test_id,
            pv_run_id=args.pv_run_id, expected=expected, card_path=card_path,
            public_root=public_root, private_root=private_root, private_partition=private)
        print(json.dumps({"script_status": "Pass", "status": "NeedsDeveloperReview",
                          "test_id": args.test_id, "public_card": str(card_path),
                          "private_manifest": str(manifest_path),
                          "inspection_catalog": str(catalog_path)},
                         sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_ATT_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": binding["expected_tuple"],
            "script_status": "Incomplete", "status": "Incomplete", "error_code": (str(error)
                if isinstance(error, PVError) else "M4B_PV_ATT_FAILED")}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


class _AutomatedLifecycleSession:
    """One independent scripted Product Session for CONV and MEM evidence."""

    def __init__(self, components: _Components, recorder: _DiagnosticRecorder,
                 *, measurement_harness=None):
        self.c = components
        self.recorder = recorder
        self.events = []
        self.subscriptions = []
        self.started = []
        self.session_id = uuid.uuid4().hex
        self.generation = 1
        self.next_turn = 1
        self.turns = []
        self.measurement_harness = measurement_harness
        self.capture = None
        if measurement_harness is not None:
            components.observer.harness = measurement_harness
        for kind in (LLMResponse, ActionCompleted, ErrorOccurred):
            self.subscriptions.append(components.bus.subscribe(kind, self._collect,
                name="m4b.pv.automated.collect"))

    async def _collect(self, event):
        self.recorder.record("bus_event", event_type=type(event).__name__, event=asdict(event))
        self.events.append(event)

    def _take(self, kind):
        events, self.events = self.events, []
        if (any(isinstance(event, ErrorOccurred) for event in events)
                or len(events) != 1 or not isinstance(events[0], kind)):
            raise PVError("M4B_PV_WORKER_FAILED")
        return events[0]

    @staticmethod
    def _close_proven(proof, session_id, generation):
        from sbd.core.state_manager.ports import ConversationCloseProof
        return (isinstance(proof, ConversationCloseProof) and proof.session_id == session_id
                and proof.generation == generation and proof.request_terminal_proven is True
                and proof.cleanup_proven is True and proof.engine_usable is True)

    async def _open(self):
        from sbd.core.state_manager.ports import ConversationReady
        ready = await self.c.adapter.control.open_conversation(self.session_id, self.generation)
        if (not isinstance(ready, ConversationReady) or ready.session_id != self.session_id
                or ready.generation != self.generation):
            raise PVError("M4B_PV_OPEN_UNPROVEN")
        self.recorder.record("conversation_ready", ready=asdict(ready))
        return ready

    async def _turn(self, text: str, label: str) -> dict[str, object]:
        turn_id = self.next_turn
        self.next_turn += 1
        observer = self.c.observer
        observer.operation_index = turn_id
        observer.context_rejected = False
        observer.generated_this_turn = False
        observer.snapshot = None
        before_revision = self.c.adapter.conversation_revision
        perception = PerceptionResult("listen", "ok", text, {}, self.session_id,
                                      turn_id, turn_id)
        reasoning = lambda: self.c.reasoner.reason(
            self.session_id, turn_id, turn_id, (perception,), (),
            conversation_generation=self.generation)
        if self.measurement_harness is None:
            await reasoning()
        else:
            await self.measurement_harness.operation(
                before="sample", after="sample", index=turn_id, execute=reasoning)
        response = self._take(LLMResponse)
        if (response.action_kind != "speak" or set(response.action_payload) != {"text"}
                or not response.action_payload["text"]):
            raise PVError("M4B_PV_STRUCTURAL_RESPONSE_FAILED")
        speaking = lambda: self.c.speaker.execute(
            self.session_id, turn_id, turn_id, response.action_payload)
        if self.measurement_harness is None:
            await speaking()
        else:
            await self.measurement_harness.operation(
                before="pre_speak", after="audio_completion", index=turn_id,
                execute=speaking)
        action = self._take(ActionCompleted)
        if action.kind != "speak" or action.status != "ok":
            raise PVError("M4B_PV_ACTION_FAILED")
        snapshot = observer.snapshot
        if snapshot is None:
            raise PVError("M4B_PV_ADMISSION_MISSING")
        if self.measurement_harness is not None:
            self.measurement_harness.capture("primary_completion", turn_id)
        observer.finish()
        row = {"label": label, "text": text, "turn_id": turn_id,
            "generation": self.generation, "revision_before": before_revision,
            "revision_after": self.c.adapter.conversation_revision,
            "child_pid": self.c.adapter._child.pid,
            "child_pgid": self.c.adapter._child.pgid,
            "snapshot": asdict(snapshot), "response": asdict(response),
            "action": asdict(action), "generated": observer.generated_this_turn,
            "context_rejected": observer.context_rejected}
        self.turns.append(row)
        self.recorder.record("scripted_turn_complete", **row)
        return row

    async def _cleanup(self) -> bool:
        c = self.c
        c.observer.harness = None
        native_owners = ((c.listener, c.asr), (c.speaker, c.tts),
                         (c.reasoner, c.adapter))
        handles = [child for owner, native in native_owners if owner in self.started
                   if (child := getattr(native, "_child", None)) is not None]
        clean = True
        for owner in reversed(self.started):
            try:
                await owner.stop()
            except Exception as error:
                clean = False
                self.recorder.error("owner_stop_failed", error)
        self.started.clear()
        for subscription in self.subscriptions:
            c.bus.unsubscribe(subscription)
        self.subscriptions.clear()
        self.events.clear()
        proven = clean and bool(handles) and _native_cleanup_proven(c, handles)
        self.recorder.record("cleanup_complete", cleanup_proven=proven)
        return proven

    async def _scenario(self, _harness=None) -> None:
        c = self.c
        for name, owner in (("audio_output", c.audio_output), ("asr", c.listener),
                            ("tts", c.speaker), ("llm", c.reasoner)):
            self.recorder.announce("owner_starting", owner=name)
            self.started.append(owner)
            await owner.start()
            self.recorder.announce("owner_ready", owner=name)
        await self._open()
        first = await self._turn("請簡短介紹台灣。", "C01-FIRST")
        if (not first["generated"] or first["context_rejected"]
                or first["response"]["post_action_route"] != "KEEP_NEXT"
                or first["revision_after"] <= first["revision_before"]):
            raise PVError("M4B_PV_FIRST_TURN_FAILED")
        continued = await self._turn("0001 請再補充一點。", "C02-CONTINUE")
        if (not continued["generated"] or continued["context_rejected"]
                or continued["response"]["post_action_route"] != "KEEP_NEXT"
                or continued["generation"] != first["generation"]
                or continued["revision_before"] != first["revision_after"]
                or continued["revision_after"] <= continued["revision_before"]
                or continued["snapshot"]["current_kv_tokens"] <= 0
                or (continued["child_pid"], continued["child_pgid"])
                   != (first["child_pid"], first["child_pgid"])):
            raise PVError("M4B_PV_CONTINUING_TURN_FAILED")
        if self.measurement_harness is not None:
            self.measurement_harness.capture("sample", continued["turn_id"],
                                             before_operation=True)
        proof = await c.adapter.control.close_conversation(
            self.session_id, self.generation, "session_end")
        if not self._close_proven(proof, self.session_id, self.generation):
            raise PVError("M4B_PV_CLOSE_UNPROVEN")
        self.recorder.record("final_close_proven", proof=asdict(proof))
        self.capture = {"session_id": self.session_id, "final_generation": self.generation,
                "next_turn_id": self.next_turn, "turns": self.turns,
                "close_proofs": [asdict(proof)], "normal_close_completed": True,
                "observed_scope": "FINITE_TWO_TURN_NO_REPLACEMENT"}

    async def run(self) -> dict[str, object]:
        if self.measurement_harness is not None:
            measured = await self.measurement_harness.run(self._scenario)
            if self.capture is None:
                raise PVError("M4B_PV_LIFECYCLE_CAPTURE_MISSING")
            return {**self.capture, "measurement": measured}
        active_error = None
        try:
            await self._scenario()
            if self.capture is None:
                raise PVError("M4B_PV_LIFECYCLE_CAPTURE_MISSING")
            return self.capture
        except BaseException as error:
            active_error = error
            raise
        finally:
            clean = await self._cleanup()
            if not clean:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("cleanup_failed", cleanup_error)


def _run_conv(args) -> int:
    if args.test_id != "M4B-PI-CONV-001" or not args.fresh_setup or args.audio_fixture is not None:
        raise PVError("M4B_PV_CONV_INPUT_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    _identifier(args.sub_run_id, "SUB_RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    try:
        components, _timeout, expected = _build_components(binding, private, recorder)
        capture = asyncio.run(_AutomatedLifecycleSession(components, recorder).run())
        capture.update(schema_version=1, test_id=args.test_id, pv_run_id=args.pv_run_id,
                       sub_run_id=args.sub_run_id, expected_tuple=expected)
        capture_path = private / "conv-capture.json"
        _write_json(capture_path, capture, mode=0o600)
        assertions = {"C01-FIRST": "Pass", "C02-CONTINUE": "Pass",
            "C03-CLOSE": "Pass"}
        card = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "turn_count": len(capture["turns"]),
            "final_generation": capture["final_generation"],
            "normal_close_completed": capture["normal_close_completed"],
            "observed_scope": capture["observed_scope"], "cleanup_proven": True,
            "capture_sha256": _sha256(capture_path), "assertions": assertions,
            "script_status": "Pass", "status": "NeedsDeveloperReview"}
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        catalog_path = _write_inspection_catalog(test_id=args.test_id,
            pv_run_id=args.pv_run_id, expected=expected, card_path=card_path,
            public_root=public_root, private_root=private_root, private_partition=private)
        print(json.dumps({"script_status": "Pass", "status": "NeedsDeveloperReview",
                          "test_id": args.test_id, "public_card": str(card_path),
                          "private_capture": str(capture_path),
                          "inspection_catalog": str(catalog_path)},
                         sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_CONV_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": binding["expected_tuple"],
            "script_status": "Incomplete", "status": "Incomplete", "error_code": (str(error)
                if isinstance(error, PVError) else "M4B_PV_CONV_FAILED")}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


def _mem_swap_configuration(meminfo: str, swappiness: str) -> dict[str, int]:
    swap_total = re.search(r"^SwapTotal:\s+(\d+) kB$", meminfo, re.MULTILINE)
    if swap_total is None:
        raise PVError("M4B_PV_SWAP_CONFIGURATION_MISSING")
    try:
        vm_swappiness = int(swappiness.strip())
    except ValueError:
        raise PVError("M4B_PV_SWAP_CONFIGURATION_MISSING") from None
    if not 0 <= vm_swappiness <= 200:
        raise PVError("M4B_PV_SWAP_CONFIGURATION_INVALID")
    return {"swap_total_bytes": int(swap_total.group(1)) * 1024,
            "vm_swappiness": vm_swappiness}


def _run_mem(args) -> int:
    if args.test_id != "M4B-PI-MEM-001" or not args.fresh_setup or args.audio_fixture is not None:
        raise PVError("M4B_PV_MEM_INPUT_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    _identifier(args.sub_run_id, "SUB_RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    harness = None
    try:
        from scripts.m4b_target_metrics import MeasurementHarness
        from sbd.cognition.litert_lm.lock import LLMLockError, load_product_profile

        components, _timeout, expected = _build_components(binding, private, recorder)
        profile = load_product_profile(
            Path(binding["paths"]["product_profile"]), allow_measurement=True)
        try:
            load_product_profile(Path(binding["paths"]["product_profile"]))
        except LLMLockError:
            normal_profile_rejected = True
        else:
            raise PVError("M4B_PV_MEASUREMENT_PROFILE_ACCEPTED_BY_PRODUCT")

        try:
            meminfo = Path("/proc/meminfo").read_text()
            swappiness = Path("/proc/sys/vm/swappiness").read_text()
        except OSError:
            raise PVError("M4B_PV_SWAP_CONFIGURATION_MISSING") from None
        swap_configuration = _mem_swap_configuration(meminfo, swappiness)

        session = None

        def sample():
            child = components.adapter._child
            if child is None:
                raise PVError("M4B_PV_OWNER_MISSING")
            return components.sampler.sample(child_pid=child.pid, child_pgid=child.pgid)

        async def cleanup():
            if session is None:
                return False
            return await session._cleanup()

        harness = MeasurementHarness(authorization=None, expected_tuple=expected,
            pv_attested=True, sample=sample, cleanup=cleanup,
            point_sink=lambda point: recorder.record("resource_point", point=asdict(point)),
            error_sink=recorder.error)
        session = _AutomatedLifecycleSession(
            components, recorder, measurement_harness=harness)
        capture = asyncio.run(session.run())
        measured = capture.pop("measurement")
        derived = measured["derived"]
        if (measured["status"] != "Measured" or measured["authorized_tuple"] != expected
                or not harness.completed or not harness.cleanup_proven
                or len(capture["turns"]) != 2
                or [row["label"] for row in capture["turns"]]
                   != ["C01-FIRST", "C02-CONTINUE"]
                or not capture["normal_close_completed"]
                or any(point.lifecycle_point in {"pre_replacement", "post_replacement"}
                       for point in harness.points)
                or profile["profile_stage"] != "measurement"
                or profile["min_mem_available_speak_bytes"] is not None
                or profile["min_mem_available_generate_bytes"] is not None):
            raise PVError("M4B_PV_MEASUREMENT_INCOMPLETE")
        series = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "profile_id": profile["profile_id"],
            "profile_stage": profile["profile_stage"],
            "profile_thresholds": {"speak": None, "generate": None},
            "normal_profile_rejected": normal_profile_rejected,
            "swap_configuration": swap_configuration,
            "points": [_json_value(asdict(point)) for point in harness.points],
            "capture": _json_value(capture), "completed": True,
            "cleanup_proven": True, "derived": derived,
            "estimate_scope": "FINITE_TWO_TURN_NO_REPLACEMENT", "status": "Pass"}
        series_path = private / "mem-series.json"
        _write_json(series_path, series, mode=0o600)
        assertions = {"M01-PROFILE": "Pass", "M02-LIFECYCLE": "Pass",
            "M03-SERIES": "Pass", "M04-STOPS": "Pass", "M05-ESTIMATES": "Pass"}
        card = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "profile_id": profile["profile_id"],
            "sample_count": len(harness.points), "series_sha256": _sha256(series_path),
            "swap_total_bytes": swap_configuration["swap_total_bytes"],
            "vm_swappiness": swap_configuration["vm_swappiness"],
            "swap_used_start_bytes": harness.points[0].sample.swap_used_bytes,
            "swap_used_end_bytes": harness.points[-1].sample.swap_used_bytes,
            **derived, "estimates_reason": None,
            "estimate_scope": "FINITE_TWO_TURN_NO_REPLACEMENT", "cleanup_proven": True,
            "assertions": assertions, "script_status": "Pass",
            "status": "NeedsDeveloperReview"}
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        catalog_path = _write_inspection_catalog(test_id=args.test_id,
            pv_run_id=args.pv_run_id, expected=expected, card_path=card_path,
            public_root=public_root, private_root=private_root, private_partition=private)
        print(json.dumps({"script_status": "Pass", "status": "NeedsDeveloperReview",
                          "inspection_catalog": str(catalog_path), "test_id": args.test_id,
                          "public_card": str(card_path),
                          "private_series": str(series_path)}, sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_MEM_FAILED", error)
        points = [] if harness is None else [_json_value(asdict(point)) for point in harness.points]
        incomplete = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": binding["expected_tuple"],
            "points": points, "completed": False,
            "cleanup_proven": bool(harness is not None and harness.cleanup_proven),
            "derived": None, "estimates_reason": "SUB_RUN_INCOMPLETE",
            "script_status": "Incomplete", "status": "Incomplete"}
        try:
            series_path = private / "mem-series.json"
            _write_json(series_path, incomplete, mode=0o600)
            failure = {"schema_version": 1, "test_id": args.test_id,
                "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
                "expected_tuple": binding["expected_tuple"],
                "speak_drop_bytes": None, "generate_drop_bytes": None,
                "min_mem_available_speak_bytes": None,
                "min_mem_available_generate_bytes": None,
                "estimates_reason": "SUB_RUN_INCOMPLETE",
                "series_sha256": _sha256(series_path),
                "script_status": "Incomplete", "status": "Incomplete",
                "error_code": (str(error) if isinstance(error, PVError)
                               else "M4B_PV_MEM_FAILED")}
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            failure = incomplete
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps({"status": "Incomplete", "test_id": args.test_id,
                          "error_code": failure.get("error_code", "M4B_PV_MEM_FAILED")},
                         sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


class _FixedAudioSession:
    def __init__(self, components: _Components, audio: _FixedAudioInput,
                 recorder: _DiagnosticRecorder, *, timeout: float) -> None:
        from sbd.perception.listen.listener import Listen
        self.c = components
        self.audio = audio
        self.recorder = recorder
        self.timeout = timeout
        self.session_id = uuid.uuid4().hex
        self.events = []
        self.started = []
        self.subscriptions = []
        components.audio_input = audio
        components.listener = Listen(audio_input=audio, asr=components.asr,
            bus=components.bus, observe=components.observer.mark)
        for kind in (PerceptionResult, LLMResponse, ActionCompleted, ErrorOccurred):
            self.subscriptions.append(components.bus.subscribe(
                kind, self._collect, name="m4b.pv.time.collect"))

    async def _collect(self, event) -> None:
        self.recorder.record("bus_event", event_type=type(event).__name__, event=asdict(event))
        self.events.append(event)

    def _take(self, kind):
        events, self.events = self.events, []
        if (any(isinstance(event, ErrorOccurred) for event in events)
                or len(events) != 1 or not isinstance(events[0], kind)):
            raise PVError("M4B_PV_WORKER_FAILED")
        return events[0]

    async def run(self) -> dict[str, object]:
        from sbd.core.state_manager.ports import ConversationCloseProof, ConversationReady
        c = self.c
        try:
            for name, owner in (("audio_input", self.audio), ("audio_output", c.audio_output),
                                ("asr", c.listener), ("tts", c.speaker),
                                ("llm", c.reasoner)):
                self.recorder.announce("owner_starting", owner=name)
                self.started.append(owner)
                await owner.start()
                self.recorder.announce("owner_ready", owner=name)
            ready = await c.adapter.control.open_conversation(self.session_id, 1)
            if (not isinstance(ready, ConversationReady) or ready.session_id != self.session_id
                    or ready.generation != 1):
                raise PVError("M4B_PV_OPEN_UNPROVEN")
            await c.listener.perceive(self.session_id, 1, 1, self.timeout)
            perception = self._take(PerceptionResult)
            self.recorder.record("fixed_audio_perception", perception=asdict(perception))
            if perception.status != "ok" or not perception.text:
                raise PVError("M4B_PV_FIXED_AUDIO_ASR_FAILED")
            c.observer.operation_index = 1
            c.observer.generated_this_turn = False
            await c.reasoner.reason(self.session_id, 1, 1, (perception,), (),
                                    conversation_generation=1)
            response = self._take(LLMResponse)
            if (not c.observer.generated_this_turn or response.action_kind != "speak"
                    or response.post_action_route != "KEEP_NEXT"
                    or not response.action_payload.get("text")):
                raise PVError("M4B_PV_FIXED_AUDIO_GENERATION_FAILED")
            await c.speaker.execute(self.session_id, 1, 1, response.action_payload)
            action = self._take(ActionCompleted)
            if action.kind != "speak" or action.status != "ok":
                raise PVError("M4B_PV_ACTION_FAILED")
            c.observer.finish("NOT_APPLICABLE")
            timing = next((row for row in reversed(c.observer.rows)
                           if row.get("dashboard") == "timing"), None)
            runtime = next((row for row in reversed(c.observer.rows)
                            if row.get("dashboard") == "runtime"), None)
            if timing is None or runtime is None:
                raise PVError("M4B_PV_TIMING_MISSING")
            events = timing["values"]["events"]
            present = [events[name]["monotonic_ns"] for name in (
                "conversation_ready", "asr_final", "llm_send", "first_safe_text",
                "llm_terminal", "tts_pcm_ready", "audio_first_write")
                if events[name]["monotonic_ns"] is not None]
            required_present = {"conversation_ready", "asr_final", "llm_send",
                                "llm_terminal", "tts_pcm_ready", "audio_first_write"}
            if (present != sorted(present)
                    or any(events[name]["monotonic_ns"] is None for name in required_present)
                    or any(events[name]["monotonic_ns"] is None
                           and events[name]["null_reason"] is None for name in events)):
                raise PVError("M4B_PV_TIMING_INVALID")
            proof = await c.adapter.control.close_conversation(self.session_id, 1, "session_end")
            if (not isinstance(proof, ConversationCloseProof)
                    or proof.session_id != self.session_id or proof.generation != 1
                    or proof.request_terminal_proven is not True
                    or proof.cleanup_proven is not True or proof.engine_usable is not True):
                raise PVError("M4B_PV_CLOSE_UNPROVEN")
            self.recorder.record("fixed_audio_turn_complete", perception=asdict(perception),
                response=asdict(response), action=asdict(action), timing=timing, runtime=runtime,
                close_proof=asdict(proof))
            return {"perception": asdict(perception), "response": asdict(response),
                    "action": asdict(action), "timing": timing["values"],
                    "runtime": runtime["values"], "close_proof": asdict(proof),
                    "frame_pull_count": self.audio.frame_pull_count}
        finally:
            active_error = sys.exc_info()[1]
            handles = [child for native in (c.asr, c.tts, c.adapter)
                       if (child := getattr(native, "_child", None)) is not None]
            clean = True
            for owner in reversed(self.started):
                try:
                    await owner.stop()
                except Exception as error:
                    clean = False
                    self.recorder.error("owner_stop_failed", error)
            for subscription in self.subscriptions:
                c.bus.unsubscribe(subscription)
            self.subscriptions.clear()
            self.events.clear()
            proven = clean and bool(handles) and _native_cleanup_proven(c, handles)
            self.recorder.record("cleanup_complete", cleanup_proven=proven)
            if not proven:
                cleanup_error = PVError("M4B_PV_CLEANUP_FAILED")
                if active_error is None:
                    raise cleanup_error
                self.recorder.error("cleanup_failed", cleanup_error)


def _run_time(args) -> int:
    canonical = (ROOT / "tests/fixtures/m4b/pv/short-taiwan.wav").absolute()
    if (args.test_id != "M4B-PI-TIME-001" or not args.fresh_setup
            or args.audio_fixture is None or args.audio_fixture.absolute() != canonical):
        raise PVError("M4B_PV_TIME_INPUT_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    _identifier(args.sub_run_id, "SUB_RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    try:
        components, timeout, expected = _build_components(binding, private, recorder)
        audio = _FixedAudioInput(canonical, recorder)
        capture = asyncio.run(_FixedAudioSession(
            components, audio, recorder, timeout=timeout).run())
        capture.update(schema_version=1, test_id=args.test_id,
            pv_run_id=args.pv_run_id, sub_run_id=args.sub_run_id,
            expected_tuple=expected, fixture={"filename": canonical.name,
                "size_bytes": len(audio.raw),
                "sha256": hashlib.sha256(audio.raw).hexdigest()})
        capture_path = private / "time-capture.json"
        _write_json(capture_path, capture, mode=0o600)
        assertions = {"T01-FIXED-AUDIO": "Pass", "T02-CLOCK-MAP": "Pass",
            "T03-NODE-ORDER": "Pass", "T04-NULL-REASON": "Pass"}
        card = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": expected, "fixture": capture["fixture"],
            "timing": capture["timing"], "capture_sha256": _sha256(capture_path),
            "clock_mapping_verified": True, "cleanup_proven": True,
            "assertions": assertions, "script_status": "Pass",
            "status": "NeedsDeveloperReview"}
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        catalog_path = _write_inspection_catalog(test_id=args.test_id,
            pv_run_id=args.pv_run_id, expected=expected, card_path=card_path,
            public_root=public_root, private_root=private_root, private_partition=private)
        print(json.dumps({"script_status": "Pass", "status": "NeedsDeveloperReview",
                          "inspection_catalog": str(catalog_path), "test_id": args.test_id,
                          "public_card": str(card_path),
                          "private_capture": str(capture_path)}, sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_TIME_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id,
            "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
            "expected_tuple": binding["expected_tuple"],
            "script_status": "Incomplete", "status": "Incomplete", "error_code": (str(error)
                if isinstance(error, PVError) else "M4B_PV_TIME_FAILED")}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


def _run_wake_case(args) -> int:
    if (args.test_id != "M4B-PI-WAKE-001"
            or args.case_id not in AGGREGATE_CASES["M4B-PI-WAKE-001"]
            or not args.fresh_setup or not args.production_wake_path):
        raise PVError("M4B_PV_WAKE_CASE_INVALID")
    for value, name in ((args.pv_run_id, "RUN_ID"), (args.sub_run_id, "SUB_RUN_ID"),
                        (args.case_attempt_id, "ATTEMPT_ID")):
        _identifier(value, name)
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    recorder = _DiagnosticRecorder(private)
    try:
        from sbd.core.config.loader import load_config
        recorder.announce("PV_WAKE_STARTING", test_id=args.test_id, case_id=args.case_id,
                          sub_run_id=args.sub_run_id,
                          case_attempt_id=args.case_attempt_id)
        components, timeout, expected = _build_components(binding, private, recorder)
        config = load_config(local_path=Path(binding["paths"]["audio_config"]),
                             dotenv_path=Path("/dev/null"), environ={})
        session = _WakePathSession(components, config, recorder,
                                   case_id=args.case_id, listen_timeout=timeout)
        capture = asyncio.run(session.run())
        capture.update(schema_version=1, test_id=args.test_id,
            pv_run_id=args.pv_run_id, sub_run_id=args.sub_run_id,
            case_attempt_id=args.case_attempt_id, expected_tuple=expected,
            cleanup_proven=session.cleanup_proven)
        capture_path = private / "wake-capture.json"
        _write_json(capture_path, capture, mode=0o600)
        assertions = {args.case_id: "Pass", "W00-PRODUCTION-PATH": "Pass",
            "W00-PRE-BARRIER-EXCLUSION": "Pass",
            "W00-DISPLAY-NONBLOCKING": "Pass", "W00-CLEANUP": "Pass"}
        activity_counts = {stage: sum(row["stage"] == stage
            for row in capture["activity"]) for stage in sorted(_WakeTrace.ACTIVITY_STAGES)}
        card = {"schema_version": 1, "test_id": args.test_id,
            "case_id": args.case_id, "pv_run_id": args.pv_run_id,
            "sub_run_id": args.sub_run_id, "case_attempt_id": args.case_attempt_id,
            "expected_tuple": expected, "capture_sha256": _sha256(capture_path),
            "barriers": capture["barriers"], "activity_counts": activity_counts,
            "display": capture["display"], "production_path": capture["production_path"],
            "assertions": assertions, "cleanup_proven": True,
            "script_status": "Pass", "status": "Pass"}
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        print(json.dumps({"status": "Pass", "test_id": args.test_id,
                          "case_id": args.case_id, "public_card": str(card_path),
                          "private_capture": str(capture_path)}, sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_WAKE_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id,
            "case_id": args.case_id, "pv_run_id": args.pv_run_id,
            "sub_run_id": args.sub_run_id, "case_attempt_id": args.case_attempt_id,
            "expected_tuple": binding["expected_tuple"],
            "script_status": "Incomplete", "status": "Incomplete", "error_code": (str(error)
                if isinstance(error, PVError) else "M4B_PV_WAKE_FAILED")}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 2
    finally:
        recorder.close()


def _owned_file_blobs(*roots: Path) -> list[tuple[str, bytes]]:
    blobs: list[tuple[str, bytes]] = []
    total = 0
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise PVError("M4B_PV_RESOURCE_EVIDENCE_UNSAFE")
            if not path.is_file():
                continue
            size = path.stat().st_size
            total += size
            if size > 32 * 1024**2 or total > 256 * 1024**2:
                raise PVError("M4B_PV_RESOURCE_EVIDENCE_UNSAFE")
            try:
                blobs.append((str(path), path.read_bytes()))
            except OSError:
                raise PVError("M4B_PV_RESOURCE_EVIDENCE_UNSAFE") from None
    return blobs


def _private_tree_controlled(root: Path) -> bool:
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        return False
    for path in root.rglob("*"):
        if path.is_symlink():
            return False
        mode = stat.S_IMODE(path.stat().st_mode)
        if path.is_dir():
            if mode & 0o077:
                return False
        elif not path.is_file() or mode & 0o077:
            return False
    return True


def _partition_holders(*roots: Path) -> list[str]:
    """Return live process handles resolving inside a case evidence partition."""
    resolved = tuple(root.resolve(strict=True) for root in roots)
    hits: list[str] = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        surfaces = [process / "cwd", process / "root"]
        try:
            surfaces.extend((process / "fd").iterdir())
        except OSError:
            pass
        for surface in surfaces:
            try:
                target = Path(os.readlink(surface))
            except OSError:
                continue
            if any(target == root or target.is_relative_to(root) for root in resolved):
                hits.append(f"{process.name}/{surface.name}")
    return sorted(set(hits))


def _resource_health_summary(capture: Mapping[str, object]) -> dict[str, object]:
    samples = capture.get("samples")
    if type(samples) is not list or len(samples) < 5:
        raise PVError("M4B_PV_RESOURCE_HEALTH_INCOMPLETE")
    rows = [row.get("sample") for row in samples if type(row) is dict]
    if len(rows) != len(samples) or any(type(row) is not dict for row in rows):
        raise PVError("M4B_PV_RESOURCE_HEALTH_INCOMPLETE")
    floor = 512 * 1024**2
    if (any(row["mem_available_bytes"] < floor or row["temperature_c"] >= 80
            or row["throttled_bits"] != 0 for row in rows)
            or any(row["oom_kill"] != rows[0]["oom_kill"] for row in rows)):
        raise PVError("M4B_PV_RESOURCE_HEALTH_UNSAFE")
    return {"sample_count": len(rows),
        "min_mem_available_bytes": min(row["mem_available_bytes"] for row in rows),
        "max_temperature_c": max(row["temperature_c"] for row in rows),
        "swap_growth_bytes": max(row["swap_used_bytes"] for row in rows)
                             - rows[0]["swap_used_bytes"],
        "oom_growth": max(row["oom_kill"] for row in rows) - rows[0]["oom_kill"],
        "throttled_or_stop_count": sum(bool(row["throttled_bits"])
                                       or row["temperature_c"] >= 80 for row in rows)}


def _resource_pid_summary(capture: Mapping[str, object]) -> dict[str, object]:
    samples = capture.get("samples")
    if type(samples) is not list or not samples:
        raise PVError("M4B_PV_RESOURCE_PID_INCOMPLETE")
    baseline = None
    owners = frozenset({"core", "vad", "asr", "tts", "llm"})
    for row in samples:
        processes = row.get("sample", {}).get("processes") if type(row) is dict else None
        if type(processes) is not list or not processes:
            raise PVError("M4B_PV_RESOURCE_PID_INCOMPLETE")
        pids = [process.get("pid") for process in processes if type(process) is dict]
        seen_owners = frozenset(owner for process in processes
            for owner in process.get("owner", []) if type(process) is dict)
        identities = tuple(sorted((process["pid"], process["start_time_ticks"],
                                   tuple(process["owner"])) for process in processes))
        if (len(pids) != len(processes) or len(set(pids)) != len(pids)
                or seen_owners != owners or (baseline is not None and identities != baseline)):
            raise PVError("M4B_PV_RESOURCE_PID_INVALID")
        baseline = identities
    assert baseline is not None
    return {"sample_count": len(samples), "unique_pid_count": len(baseline),
            "owners": sorted(owners),
            "identity_sha256": hashlib.sha256(_json_bytes(baseline)).hexdigest()}


def _network_trace_violations(blobs: list[tuple[str, bytes]]) -> list[str]:
    violations: list[str] = []
    downloader = re.compile(r'execve\("[^"\n]*/(?:curl|wget|aria2c)"')
    network_tool = re.compile(
        r'execve\("[^"\n]*/(?:git|pip|pip3|npm|apt|apt-get)".*?'
        r'"(?:clone|fetch|pull|push|remote|install|download|publish|update|upgrade)"')
    outbound = re.compile(r"\b(?:connect|sendto|sendmsg)\(.*sa_family=AF_INET6?")
    loopback = re.compile(r'(?:127(?:\.[0-9]{1,3}){3}|::1|0\.0\.0\.0|"::")')
    dns = re.compile(r"(?:sin_port=htons\(53\)|:53\b)")
    for locator, blob in blobs:
        text_value = blob.decode("utf-8", "replace")
        for number, line in enumerate(text_value.splitlines(), 1):
            if downloader.search(line) or network_tool.search(line) or (outbound.search(line)
                    and (dns.search(line) or not loopback.search(line))):
                violations.append(f"{locator}:{number}")
    return violations


def _resource_child_args(args) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "run-resource-case",
        "--test-id", args.test_id, "--case-id", args.case_id,
        "--pv-run-id", args.pv_run_id, "--sub-run-id", args.sub_run_id,
        "--case-attempt-id", args.case_attempt_id,
        "--public-partition", str(args.public_partition.absolute()),
        "--private-partition", str(args.private_partition.absolute()),
        "--binding-manifest", str(args.binding_manifest.absolute()), "--fresh-setup"]


def _run_resource_offline_child(args) -> int:
    from scripts.m4b_target_metrics import network_isolated
    binding, public_root, private_root = _load_binding(args)
    _partition(args.public_partition, public_root, private=False)
    private_value = args.private_partition.absolute()
    if not private_value.is_relative_to(private_root):
        raise PVError("M4B_PV_PARTITION_OUTSIDE_ROOT")
    private = private_value.resolve(strict=True)
    initial = tuple(private.iterdir())
    if (stat.S_IMODE(private.stat().st_mode) & 0o077 or not initial
            or any(path.is_symlink() or not path.is_file()
                   or re.fullmatch(r"network-syscalls(?:\.[0-9]+)?", path.name) is None
                   or stat.S_IMODE(path.stat().st_mode) & 0o077 for path in initial)):
        raise PVError("M4B_PV_RESOURCE_OFFLINE_CAPTURE_FAILED")
    recorder = _DiagnosticRecorder(private)
    session = None
    try:
        before_dev = Path("/proc/net/dev").read_text()
        before_route = Path("/proc/net/route").read_text()
        components, _timeout, expected = _build_components(binding, private, recorder)
        session = _ResourceStructuralSession(components, recorder,
            text="請簡短說明台灣。")
        capture = asyncio.run(session.run())
        after_dev = Path("/proc/net/dev").read_text()
        after_route = Path("/proc/net/route").read_text()
        if (not network_isolated(before_dev, before_route)
                or not network_isolated(after_dev, after_route)
                or not session.cleanup_proven):
            raise PVError("M4B_PV_RESOURCE_OFFLINE_INVALID")
        capture.update(schema_version=1, test_id=args.test_id, case_id=args.case_id,
            pv_run_id=args.pv_run_id, sub_run_id=args.sub_run_id,
            case_attempt_id=args.case_attempt_id, expected_tuple=expected,
            network_namespace_isolated=True, cleanup_proven=True)
        _write_json(private / "offline-child-capture.json", capture, mode=0o600)
        return 0
    except BaseException as error:
        if not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_RESOURCE_OFFLINE_CHILD_FAILED", error)
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        return 2
    finally:
        recorder.close()


def _run_resource_offline(args, binding: Mapping[str, object], public: Path,
                          private: Path) -> int:
    trace_prefix = private / "network-syscalls"
    command = ["/usr/bin/unshare", "--user", "--map-root-user", "--net", "--",
        "/usr/bin/strace", "-ff", "-qq", "-s", "256", "-e", "trace=network,process",
        "-o", str(trace_prefix), *_resource_child_args(args)]
    environment = dict(os.environ)
    environment["SBD_M4B_PV_R01_CHILD"] = "1"
    old_umask = os.umask(0o077)
    try:
        completed = subprocess.run(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900,
            env=environment, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise PVError("M4B_PV_RESOURCE_OFFLINE_CAPTURE_FAILED") from None
    finally:
        os.umask(old_umask)
    _write_bytes(private / "offline-stdout.bin", completed.stdout, mode=0o600)
    _write_bytes(private / "offline-stderr.bin", completed.stderr, mode=0o600)
    traces = [(str(path.relative_to(private)), path.read_bytes())
              for path in sorted(private.glob("network-syscalls*"))
              if path.is_file() and not path.is_symlink()]
    capture_path = private / "offline-child-capture.json"
    if completed.returncode != 0 or not traces or not capture_path.is_file():
        raise PVError("M4B_PV_RESOURCE_OFFLINE_CAPTURE_FAILED")
    capture = _read_json(capture_path)
    violations = _network_trace_violations(traces)
    holders = _partition_holders(public, private)
    if (capture.get("network_namespace_isolated") is not True or violations or holders
            or capture.get("cleanup_proven") is not True):
        raise PVError("M4B_PV_RESOURCE_OFFLINE_INVALID")
    summary = {"trace_file_count": len(traces),
        "trace_sha256": hashlib.sha256(b"".join(blob for _, blob in traces)).hexdigest(),
        "network_attempt_count": 0, "network_namespace_isolated": True,
        "partition_holder_count": 0, "cleanup_proven": True}
    summary_path = private / "offline-summary.json"
    _write_json(summary_path, summary, mode=0o600)
    assertions = {"R01-OFFLINE": "Pass", "R01-NONLOOPBACK": "Pass",
        "R01-NO-DOWNLOADER-TELEMETRY-DNS-FALLBACK": "Pass", "R01-CLEANUP": "Pass"}
    card = {"schema_version": 1, "test_id": args.test_id, "case_id": args.case_id,
        "pv_run_id": args.pv_run_id, "sub_run_id": args.sub_run_id,
        "case_attempt_id": args.case_attempt_id,
        "expected_tuple": binding["expected_tuple"], "summary": summary,
        "summary_sha256": _sha256(summary_path), "assertions": assertions,
        "cleanup_proven": True, "script_status": "Pass", "status": "Pass"}
    card_path = public / "result.json"
    _write_json(card_path, card, mode=0o644)
    print(json.dumps({"status": "Pass", "test_id": args.test_id,
        "case_id": args.case_id, "public_card": str(card_path),
        "private_capture": str(capture_path)}, sort_keys=True), flush=True)
    return 0


def _run_resource_case(args) -> int:
    if (args.test_id != "M4B-PI-RES-001"
            or args.case_id not in AGGREGATE_CASES["M4B-PI-RES-001"]
            or not args.fresh_setup):
        raise PVError("M4B_PV_RESOURCE_CASE_INVALID")
    for value, name in ((args.pv_run_id, "RUN_ID"), (args.sub_run_id, "SUB_RUN_ID"),
                        (args.case_attempt_id, "ATTEMPT_ID")):
        _identifier(value, name)
    if args.case_id == "R01-OFFLINE" and os.environ.get("SBD_M4B_PV_R01_CHILD") == "1":
        return _run_resource_offline_child(args)
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    if args.case_id == "R01-OFFLINE":
        try:
            return _run_resource_offline(args, binding, public, private)
        except BaseException as error:
            failure = {"schema_version": 1, "test_id": args.test_id,
                "case_id": args.case_id, "pv_run_id": args.pv_run_id,
                "sub_run_id": args.sub_run_id,
                "case_attempt_id": args.case_attempt_id,
                "expected_tuple": binding["expected_tuple"],
                "script_status": "Incomplete", "status": "Incomplete",
                "error_code": str(error) if isinstance(error, PVError)
                              else "M4B_PV_RESOURCE_FAILED"}
            try:
                _write_json(public / "result.json", failure, mode=0o644)
            except (OSError, PVError):
                pass
            if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
                raise
            print(json.dumps(failure, sort_keys=True), flush=True)
            return 2

    recorder = _DiagnosticRecorder(private)
    recorder_closed = False
    try:
        recorder.announce("PV_RESOURCE_STARTING", test_id=args.test_id,
                          case_id=args.case_id, sub_run_id=args.sub_run_id,
                          case_attempt_id=args.case_attempt_id)
        if args.case_id == "R05-RECOVERY":
            from sbd.core.config.loader import load_config
            ledger: list[dict[str, object]] = []
            coordinator = _RecoveryCoordinator(recorder, ledger)
            components, _timeout, expected = _build_components(
                binding, private, recorder, recovery=coordinator)
            config = load_config(local_path=Path(binding["paths"]["audio_config"]),
                                 dotenv_path=Path("/dev/null"), environ={})
            session = _ResourceRecoverySession(components, config, recorder, coordinator)
            capture = asyncio.run(session.run())
            if (capture.get("sm_authorization_count") != 1
                    or capture.get("new_ready") is not True
                    or capture.get("following_structural_turn") is not True
                    or capture.get("following_source") != "real_reasoner"
                    or capture.get("following_generated") is not True):
                raise PVError("M4B_PV_RESOURCE_RECOVERY_INVALID")
            assertions = {"R05-RECOVERY": "Pass", "R05-ACTION-REST-CLOSE": "Pass",
                          "R05-SM-AUTHORIZATION": "Pass", "R05-NEW-READY": "Pass",
                          "R05-FOLLOWING-TURN": "Pass", "R00-CLEANUP": "Pass"}
        else:
            components, _timeout, expected = _build_components(binding, private, recorder)
        if args.case_id == "R06-FORCED-CLEANUP":
            session = _ResourceOwnerSession(components, recorder, text="")
            capture = asyncio.run(session.run_forced_cleanup())
            assertions = {"R06-FORCED-CLEANUP": "Pass", "R06-DESCENDANTS-GONE": "Pass",
                          "R06-NO-REBUILD": "Pass", "R00-CLEANUP": "Pass"}
        elif args.case_id == "R07-SHUTDOWN":
            session = _ResourceOwnerSession(components, recorder, text="")
            capture = asyncio.run(session.run_shutdown())
            recorder.close()
            recorder_closed = True
            holders = _partition_holders(public, private)
            if (holders or not session.cleanup_proven
                    or capture.get("sampler_stopped") is not True
                    or capture.get("shutdown_invoked_with_sampler_live") is not True):
                raise PVError("M4B_PV_RESOURCE_SHUTDOWN_FAILED")
            capture.update(partition_holder_count=0, cleanup_proven=True)
            assertions = {"R07-SHUTDOWN": "Pass", "R07-SAMPLER-STOPPED": "Pass",
                          "R07-NO-HANDLES": "Pass", "R00-CLEANUP": "Pass"}
        elif args.case_id == "R04-NORMAL-CLOSE":
            from sbd.core.config.loader import load_config
            config = load_config(local_path=Path(binding["paths"]["audio_config"]),
                                 dotenv_path=Path("/dev/null"), environ={})
            session = _ResourceRecoverySession(components, config, recorder)
            capture = asyncio.run(session.run_normal_close())
            assertions = {"R04-NORMAL-CLOSE": "Pass", "R04-CLOSE-PROOF": "Pass",
                          "R04-PRODUCT-SESSION": "Pass",
                          "R04-DESCENDANTS-GONE": "Pass", "R00-CLEANUP": "Pass"}
        elif args.case_id != "R05-RECOVERY":
            canary = f"pv{uuid.uuid4().hex[:16]}" if args.case_id == "R08-PRIVACY" else None
            session = _ResourceStructuralSession(components, recorder,
                text=canary or "請簡短說明台灣。", redact_content=canary is not None)
            capture = asyncio.run(session.run())
            if args.case_id == "R02-HEALTH":
                from scripts.m4b_target_metrics import kernel_resource_sample
                from sbd.core._m4b_resource_binding import _pi_temperature, _pi_throttled
                setup = kernel_resource_sample(Path("/proc/meminfo").read_text(),
                    Path("/proc/vmstat").read_text(),
                    str(round(_pi_temperature() * 1000)),
                    f"throttled=0x{_pi_throttled():x}")
                capture["swap_configuration"] = {"swap_total_mib": setup["swap_total_mib"]}
                capture["health"] = _resource_health_summary(capture)
                assertions = {"R02-HEALTH": "Pass", "R02-OOM": "Pass",
                              "R02-THERMAL-FLOOR": "Pass", "R00-CLEANUP": "Pass"}
            elif args.case_id == "R03-PID":
                capture["pid_accounting"] = _resource_pid_summary(capture)
                assertions = {"R03-PID": "Pass", "R03-OWNER-COVERAGE": "Pass",
                              "R03-IDENTITY-STABLE": "Pass", "R00-CLEANUP": "Pass"}
            elif args.case_id == "R08-PRIVACY":
                from scripts.m4b_target_metrics import privacy_hits
                recorder.close()
                recorder_closed = True
                blobs = [*session.process_blobs, *_owned_file_blobs(public, private),
                    ("controller/argv", b"\0".join(os.fsencode(value) for value in sys.argv)),
                    ("controller/environ", b"\0".join(os.fsencode(f"{key}={value}")
                        for key, value in os.environ.items()))]
                hits = privacy_hits(blobs, (canary,))
                holders = _partition_holders(public, private)
                if (hits or holders or any(Path(path).exists() for path in session.workdirs)
                        or not _private_tree_controlled(private)):
                    raise PVError("M4B_PV_RESOURCE_PRIVACY_FAILED")
                capture.update(canary_sha256=hashlib.sha256(canary.encode()).hexdigest(),
                    scanned_blob_count=len(blobs), privacy_hit_count=0,
                    partition_holder_count=0, raw_evidence_access_controlled=True)
                assertions = {"R08-PRIVACY": "Pass", "R08-NO-REVERSIBLE-HIT": "Pass",
                              "R08-OPAQUE-PUBLIC": "Pass", "R08-PRIVATE-MODE": "Pass",
                              "R00-CLEANUP": "Pass"}
            else:
                raise PVError("M4B_PV_RESOURCE_CASE_INVALID")
        if not session.cleanup_proven:
            raise PVError("M4B_PV_CLEANUP_FAILED")
        capture.update(schema_version=1, test_id=args.test_id, case_id=args.case_id,
            pv_run_id=args.pv_run_id, sub_run_id=args.sub_run_id,
            case_attempt_id=args.case_attempt_id, expected_tuple=expected,
            cleanup_proven=True)
        capture_path = private / "resource-capture.json"
        capture_bytes = _json_bytes(capture)
        if args.case_id == "R08-PRIVACY":
            from scripts.m4b_target_metrics import privacy_hits
            if privacy_hits([("capture", capture_bytes)], (canary,)):
                raise PVError("M4B_PV_RESOURCE_PRIVACY_FAILED")
        _write_bytes(capture_path, capture_bytes, mode=0o600)
        card = {"schema_version": 1, "test_id": args.test_id,
            "case_id": args.case_id, "pv_run_id": args.pv_run_id,
            "sub_run_id": args.sub_run_id, "case_attempt_id": args.case_attempt_id,
            "expected_tuple": expected, "capture_sha256": _sha256(capture_path),
            "assertions": assertions, "cleanup_proven": True,
            "script_status": "Pass", "status": "Pass"}
        if args.case_id == "R08-PRIVACY":
            from scripts.m4b_target_metrics import privacy_hits
            if privacy_hits([("public-card", _json_bytes(card))], (canary,)):
                raise PVError("M4B_PV_RESOURCE_PRIVACY_FAILED")
        card_path = public / "result.json"
        _write_json(card_path, card, mode=0o644)
        print(json.dumps({"status": "Pass", "test_id": args.test_id,
            "case_id": args.case_id, "public_card": str(card_path),
            "private_capture": str(capture_path)}, sort_keys=True), flush=True)
        return 0
    except BaseException as error:
        if not recorder_closed and not isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            recorder.error("PV_RESOURCE_FAILED", error)
        failure = {"schema_version": 1, "test_id": args.test_id,
            "case_id": args.case_id, "pv_run_id": args.pv_run_id,
            "sub_run_id": args.sub_run_id, "case_attempt_id": args.case_attempt_id,
            "expected_tuple": binding["expected_tuple"],
            "script_status": "Incomplete", "status": "Incomplete", "error_code": (str(error)
                if isinstance(error, PVError) else "M4B_PV_RESOURCE_FAILED")}
        try:
            _write_json(public / "result.json", failure, mode=0o644)
        except (OSError, PVError):
            pass
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 2
    finally:
        if not recorder_closed:
            recorder.close()


def _public_result_cards(public_root: Path, pv_run_id: str,
                         test_id: str) -> list[tuple[Path, dict[str, object]]]:
    """Read all designated-candidate cards, including unsatisfied script states."""
    cards = []
    for path in sorted([*public_root.rglob("result.json"),
                        *(public_root.rglob("capture.json") if test_id == "M4B-PI-SEM-001" else ())]):
        relative = path.relative_to(public_root)
        parents = [public_root / Path(*relative.parts[:index])
                   for index in range(1, len(relative.parts))]
        if (path.is_symlink() or not path.is_file()
                or any(parent.is_symlink() for parent in parents)):
            raise PVError("M4B_PV_RESULT_CARD_UNSAFE")
        value = _read_json(path)
        if value.get("pv_run_id") != pv_run_id or value.get("test_id") != test_id:
            continue
        if path.name == "capture.json" and (path.parent / "result.json").exists():
            continue
        cards.append((path, value))
    return cards


def _designation_key(test_id: str, case_id: str | None) -> str:
    if test_id not in PV_TEST_IDS or (case_id is not None and
            case_id not in (SEMANTIC_CASES if test_id == "M4B-PI-SEM-001"
                else AGGREGATE_CASES.get(test_id, ()))):
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    return f"{test_id}-{case_id or 'RESULT'}"


def _current_designation(private_root: Path, *, test_id: str,
                         case_id: str | None, pv_run_id: str,
                         expected: Mapping[str, object]) -> dict[str, object] | None:
    directory = private_root / "designations" / _designation_key(test_id, case_id)
    if not directory.exists():
        return None
    if directory.is_symlink() or not directory.is_dir():
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    paths = sorted(directory.glob("[0-9][0-9][0-9][0-9].json"))
    if not paths:
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    latest = _read_json(paths[-1])
    if (set(latest) != {"schema_version", "pv_run_id", "test_id", "case_id",
                         "expected_tuple", "card_locator", "card_sha256",
                         "case_attempt_id", "sequence"}
            or latest.get("schema_version") != 1
            or latest.get("pv_run_id") != pv_run_id
            or latest.get("test_id") != test_id
            or latest.get("case_id") != case_id
            or latest.get("expected_tuple") != expected
            or latest.get("sequence") != int(paths[-1].stem)):
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    return latest


def _select_exact_attempt(matches: list[tuple[Path, dict[str, object]]], *,
                          public_root: Path, private_root: Path, pv_run_id: str,
                          test_id: str, case_id: str | None,
                          expected: Mapping[str, object]) -> tuple[Path, dict[str, object]]:
    designation = _current_designation(private_root, test_id=test_id,
        case_id=case_id, pv_run_id=pv_run_id, expected=expected)
    if designation is None:
        if len(matches) != 1:
            raise PVError("M4B_PV_CASE_SELECTION_INVALID" if case_id else
                          "M4B_PV_TEST_SELECTION_INVALID")
        return matches[0]
    selected = [(path, card) for path, card in matches
        if path.relative_to(public_root).as_posix() == designation["card_locator"]
        and _sha256(path) == designation["card_sha256"]
        and card.get("case_attempt_id") == designation["case_attempt_id"]]
    if len(selected) != 1:
        raise PVError("M4B_PV_DESIGNATION_STALE")
    return selected[0]


def _run_designate_result(args) -> int:
    _identifier(args.pv_run_id, "RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    expected = binding["expected_tuple"]
    key = _designation_key(args.test_id, args.case_id)
    card_path = args.result_card.absolute()
    if (not card_path.is_relative_to(public_root) or card_path.is_symlink()
            or not card_path.is_file()
            or not card_path.resolve(strict=True).is_relative_to(public_root)):
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    card = _read_json(card_path)
    if (card.get("schema_version") != 1 or card.get("pv_run_id") != args.pv_run_id
            or card.get("test_id") != args.test_id or card.get("case_id") != args.case_id
            or card.get("expected_tuple") != expected):
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    if args.case_id is None:
        if (card.get("aggregate", False) is True and args.test_id not in AGGREGATE_CASES
                or card.get("aggregate", False) is False and args.test_id in AGGREGATE_CASES):
            raise PVError("M4B_PV_DESIGNATION_INVALID")
    elif type(card.get("case_attempt_id")) is not str:
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    directory = private_root / "designations" / key
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or stat.S_IMODE(directory.stat().st_mode) & 0o077:
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    sequence = 1 + max((int(path.stem) for path in directory.glob("[0-9][0-9][0-9][0-9].json")),
                       default=0)
    if sequence > 9999:
        raise PVError("M4B_PV_DESIGNATION_INVALID")
    designation = {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "test_id": args.test_id, "case_id": args.case_id,
        "expected_tuple": expected, "card_locator": card_path.relative_to(public_root).as_posix(),
        "card_sha256": _sha256(card_path),
        "case_attempt_id": card.get("case_attempt_id"), "sequence": sequence}
    path = directory / f"{sequence:04d}.json"
    _write_json(path, designation, mode=0o600)
    print(json.dumps({"status": "Designated", "test_id": args.test_id,
        "case_id": args.case_id, "case_attempt_id": designation["case_attempt_id"],
        "designation_sha256": _sha256(path)}, sort_keys=True), flush=True)
    return 0


def _validate_pass_card(card: Mapping[str, object], *, expected: Mapping[str, object],
                        test_id: str, pv_run_id: str) -> None:
    if (card.get("schema_version") != 1 or card.get("test_id") != test_id
            or card.get("pv_run_id") != pv_run_id or card.get("script_status") != "Pass"
            or card.get("expected_tuple") != expected):
        raise PVError("M4B_PV_RESULT_CARD_INVALID")


def _select_cases(public_root: Path, private_root: Path, *, pv_run_id: str, test_id: str,
                  expected: Mapping[str, object], required: tuple[str, ...]
                  ) -> list[tuple[Path, dict[str, object]]]:
    selected = []
    cards = _public_result_cards(public_root, pv_run_id, test_id)
    for case_id in required:
        matches = [(path, card) for path, card in cards
                   if card.get("case_id") == case_id and card.get("aggregate") is not True]
        path, card = _select_exact_attempt(matches, public_root=public_root,
            private_root=private_root, pv_run_id=pv_run_id, test_id=test_id,
            case_id=case_id, expected=expected)
        selected.append((path, card))
    return selected


def _case_private_partition(private_root: Path, *, test_id: str,
                            pv_run_id: str, case_attempt_id: str,
                            expected: Mapping[str, object]) -> Path:
    capture_names = (("wake-capture.json",) if test_id == "M4B-PI-WAKE-001" else
        ("semantic-capture.json",) if test_id == "M4B-PI-SEM-001" else
        ("resource-capture.json", "offline-child-capture.json"))
    matches: list[Path] = []
    for name in capture_names:
        for path in private_root.rglob(name):
            if path.is_symlink() or not path.is_file():
                raise PVError("M4B_PV_INSPECTION_EVIDENCE_UNSAFE")
            value = _read_json(path)
            if (value.get("test_id") == test_id and value.get("pv_run_id") == pv_run_id
                    and value.get("case_attempt_id") == case_attempt_id
                    and value.get("expected_tuple") == expected):
                matches.append(path.parent)
    if len(matches) != 1:
        raise PVError("M4B_PV_CASE_EVIDENCE_INCOMPLETE")
    return matches[0]


def _run_aggregate_cases(args) -> int:
    required = AGGREGATE_CASES.get(args.test_id)
    if required is None:
        raise PVError("M4B_PV_AGGREGATE_TEST_ID_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    public = _partition(args.public_partition, public_root, private=False)
    private = _partition(args.private_partition, private_root, private=True)
    expected = binding["expected_tuple"]
    selected = _select_cases(public_root, private_root, pv_run_id=args.pv_run_id,
                             test_id=args.test_id, expected=expected,
                             required=required)
    private_rows = []
    public_rows = []
    for path, card in selected:
        _validate_pass_card(card, expected=expected, test_id=args.test_id,
                            pv_run_id=args.pv_run_id)
        if (card.get("status") != "Pass" or type(card.get("sub_run_id")) is not str
                or type(card.get("case_attempt_id")) is not str):
            raise PVError("M4B_PV_CASE_SCRIPT_UNSATISFIED")
        card_sha256 = _sha256(path)
        assertions = card.get("assertions", {})
        if (type(assertions) is not dict or not assertions
                or any(value != "Pass" for value in assertions.values())):
            raise PVError("M4B_PV_RESULT_CARD_INVALID")
        private_rows.append({"case_id": card["case_id"],
            "sub_run_id": card["sub_run_id"],
            "case_attempt_id": card["case_attempt_id"],
            "card_locator": str(path.relative_to(public_root)),
            "card_sha256": card_sha256})
        public_rows.append({"case_id": card["case_id"],
            "case_attempt_id": card["case_attempt_id"],
            "card_sha256": card_sha256, "assertions": dict(assertions),
            "status": "Pass"})
    selection = {"schema_version": 1, "test_id": args.test_id,
        "pv_run_id": args.pv_run_id, "expected_tuple": expected,
        "selected_cases": private_rows, "status": "Pass"}
    case_parts = [_case_private_partition(private_root, test_id=args.test_id,
        pv_run_id=args.pv_run_id, case_attempt_id=case["case_attempt_id"],
        expected=expected) for _, case in selected]
    selection_path = private / "aggregate-selection.json"
    _write_json(selection_path, selection, mode=0o600)
    card = {"schema_version": 1, "test_id": args.test_id,
        "pv_run_id": args.pv_run_id, "expected_tuple": expected,
        "aggregate": True, "cases": public_rows,
        "selection_sha256": _sha256(selection_path),
        "script_status": "Pass", "status": "NeedsDeveloperReview"}
    card_path = public / "result.json"
    _write_json(card_path, card, mode=0o644)
    catalog_path = _write_inspection_catalog(test_id=args.test_id,
        pv_run_id=args.pv_run_id, expected=expected, card_path=card_path,
        public_root=public_root, private_root=private_root, private_partition=private,
        public_cards=[card_path, *(path for path, _ in selected)],
        private_parts=[private, *case_parts])
    print(json.dumps({"script_status": "Pass", "status": "NeedsDeveloperReview",
                      "inspection_catalog": str(catalog_path), "test_id": args.test_id,
                      "public_card": str(card_path),
                      "private_selection": str(selection_path)}, sort_keys=True), flush=True)
    return 0


def _select_single(public_root: Path, private_root: Path, *, pv_run_id: str, test_id: str,
                   expected: Mapping[str, object], aggregate: bool = False
                   ) -> tuple[Path, dict[str, object]]:
    matches = [(path, card) for path, card in
               _public_result_cards(public_root, pv_run_id, test_id)
               if card.get("aggregate", False) is aggregate and "case_id" not in card]
    path, card = _select_exact_attempt(matches, public_root=public_root,
        private_root=private_root, pv_run_id=pv_run_id, test_id=test_id,
        case_id=None, expected=expected)
    return path, card


def _validate_aggregate_card(card: Mapping[str, object], *, test_id: str) -> None:
    required = AGGREGATE_CASES[test_id]
    cases = card.get("cases")
    if (card.get("aggregate") is not True or type(cases) is not list
            or len(cases) != len(required)
            or [row.get("case_id") for row in cases] != list(required)):
        raise PVError("M4B_PV_RESULT_CARD_INVALID")
    for row in cases:
        if (type(row) is not dict or set(row) != {
                "case_id", "case_attempt_id", "card_sha256", "assertions", "status"}
                or row["status"] != "Pass" or type(row["assertions"]) is not dict
                or not row["assertions"]
                or any(value != "Pass" for value in row["assertions"].values())
                or re.fullmatch(r"[0-9a-f]{64}", str(row["card_sha256"])) is None):
            raise PVError("M4B_PV_RESULT_CARD_INVALID")


def _review_path(private_root: Path, test_id: str, card_sha256: str) -> Path:
    directory = private_root / "developer-reviews"
    if directory.exists():
        if directory.is_symlink() or not directory.is_dir() or stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise PVError("M4B_PV_DEVELOPER_REVIEW_INVALID")
    else:
        directory.mkdir(mode=0o700)
    return directory / f"{test_id}-{card_sha256}.json"


_INSPECTION_CAPTURE = {
    "M4B-PI-ATT-001": "att-manifest.json",
    "M4B-PI-CONV-001": "conv-capture.json",
    "M4B-PI-MEM-001": "mem-series.json",
    "M4B-PI-TIME-001": "time-capture.json",
    "M4B-PI-WAKE-001": "wake-capture.json",
    "M4B-PI-RES-001": "resource-capture.json",
}
_INSPECTION_META_FILES = {"inspection-catalog.json", "evidence-manifest.json"}


def _inspection_pointer(parts: tuple[str, ...]) -> str:
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)


def _inspection_values(value: object, locator: str, parts: tuple[str, ...],
                       fields: list[dict[str, object]], rows: list[dict[str, object]]) -> None:
    if type(value) is dict:
        for name in sorted(value):
            _inspection_values(value[name], locator, (*parts, name), fields, rows)
    elif type(value) is list:
        for index, item in enumerate(value):
            pointer = _inspection_pointer((*parts, str(index)))
            rows.append({"locator": locator + "#" + pointer, "kind": "json-array-element"})
            _inspection_values(item, locator, (*parts, str(index)), fields, rows)
    else:
        fields.append({"locator": locator + "#" + _inspection_pointer(parts),
                       "type": type(value).__name__, "value": value})


def _inspection_file(path: Path, locator: str) -> tuple[dict[str, object],
                                                        list[dict[str, object]],
                                                        list[dict[str, object]]]:
    if path.is_symlink() or not path.is_file():
        raise PVError("M4B_PV_INSPECTION_EVIDENCE_UNSAFE")
    raw = path.read_bytes()
    fields: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    if path.suffix == ".json":
        try:
            value = json.loads(raw.decode("utf-8", "strict"))
        except (UnicodeError, ValueError):
            raise PVError("M4B_PV_INSPECTION_EVIDENCE_INVALID") from None
        _inspection_values(value, locator, (), fields, rows)
        rows.insert(0, {"locator": locator + "#document", "kind": "json-document"})
    elif path.suffix == ".jsonl":
        try:
            for number, line in enumerate(raw.decode("utf-8", "strict").splitlines(), 1):
                value = json.loads(line)
                line_locator = f"{locator}#line:{number}"
                rows.append({"locator": line_locator, "kind": "jsonl-row"})
                _inspection_values(value, line_locator, (), fields, rows)
        except (UnicodeError, ValueError):
            raise PVError("M4B_PV_INSPECTION_EVIDENCE_INVALID") from None
    else:
        try:
            decoded = raw.decode("utf-8", "strict")
        except UnicodeError:
            rows.append({"locator": locator + "#binary", "kind": "binary-digest"})
        else:
            for number, _line in enumerate(decoded.splitlines(), 1):
                rows.append({"locator": f"{locator}#line:{number}", "kind": "text-row"})
            if not rows:
                rows.append({"locator": locator + "#empty-text", "kind": "text-digest"})
    item = {"locator": locator, "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "field_count": len(fields), "row_count": len(rows)}
    return item, fields, rows


def _inspection_files(public_root: Path, private_root: Path,
                      public_cards: list[Path], private_parts: list[Path]
                      ) -> tuple[list[dict[str, object]], list[dict[str, object]],
                                 list[dict[str, object]]]:
    locations: dict[str, Path] = {}
    for card_path in public_cards:
        if not card_path.is_relative_to(public_root):
            raise PVError("M4B_PV_INSPECTION_EVIDENCE_UNSAFE")
        locations["public:" + card_path.relative_to(public_root).as_posix()] = card_path
    for partition in private_parts:
        if (not partition.is_relative_to(private_root) or partition.is_symlink()
                or not partition.is_dir()):
            raise PVError("M4B_PV_INSPECTION_EVIDENCE_UNSAFE")
        for path in partition.rglob("*"):
            if path.is_symlink():
                raise PVError("M4B_PV_INSPECTION_EVIDENCE_UNSAFE")
            if path.is_file() and path.name not in _INSPECTION_META_FILES:
                locations["private:" + path.relative_to(private_root).as_posix()] = path
    files: list[dict[str, object]] = []
    fields: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for locator, path in sorted(locations.items()):
        item, file_fields, file_rows = _inspection_file(path, locator)
        files.append(item)
        fields.extend(file_fields)
        rows.extend(file_rows)
    return files, fields, rows


def _write_inspection_catalog(*, test_id: str, pv_run_id: str,
                              expected: Mapping[str, object], card_path: Path,
                              public_root: Path, private_root: Path,
                              private_partition: Path, public_cards: list[Path] | None = None,
                              private_parts: list[Path] | None = None) -> Path:
    cards = public_cards if public_cards is not None else [card_path]
    partitions = private_parts if private_parts is not None else [private_partition]
    files, fields, rows = _inspection_files(public_root, private_root, cards, partitions)
    if not fields or not rows or not any(item["locator"].startswith("private:") for item in files):
        raise PVError("M4B_PV_INSPECTION_EVIDENCE_INCOMPLETE")
    manifest = {"schema_version": 1, "pv_run_id": pv_run_id, "test_id": test_id,
        "expected_tuple": expected,
        "result_card_locator": card_path.relative_to(public_root).as_posix(),
        "result_card_sha256": _sha256(card_path),
        "public_cards": [path.relative_to(public_root).as_posix() for path in cards],
        "private_partitions": [path.relative_to(private_root).as_posix() for path in partitions],
        "files": files, "expected_field_count": len(fields), "expected_row_count": len(rows)}
    manifest_path = private_partition / "evidence-manifest.json"
    _write_json(manifest_path, manifest, mode=0o600)
    catalog = {"schema_version": 1, "pv_run_id": pv_run_id, "test_id": test_id,
        "expected_tuple": expected,
        "result_card_locator": manifest["result_card_locator"],
        "result_card_sha256": manifest["result_card_sha256"],
        "evidence_manifest_locator": manifest_path.relative_to(private_root).as_posix(),
        "evidence_manifest_sha256": _sha256(manifest_path),
        "expected_field_count": len(fields), "expected_row_count": len(rows),
        "fields": fields, "rows": rows}
    catalog_path = private_partition / "inspection-catalog.json"
    _write_json(catalog_path, catalog, mode=0o600)
    return catalog_path


def _inspection_path(root: Path, locator: object) -> Path:
    if (type(locator) is not str or not locator or Path(locator).is_absolute()
            or ".." in Path(locator).parts or "\x00" in locator):
        raise PVError("M4B_PV_INSPECTION_LOCATOR_INVALID")
    path = root / locator
    if (path.is_symlink() or not path.is_file()
            or not path.resolve(strict=True).is_relative_to(root)):
        raise PVError("M4B_PV_INSPECTION_LOCATOR_INVALID")
    return path


def _verify_inspection_catalog(*, catalog_path: Path, private_root: Path,
                               public_root: Path, test_id: str, pv_run_id: str,
                               expected: Mapping[str, object], card_path: Path
                               ) -> tuple[dict[str, object], dict[str, object]]:
    try:
        if (catalog_path.is_symlink() or not catalog_path.is_file()
                or not catalog_path.resolve(strict=True).is_relative_to(private_root)
                or stat.S_IMODE(catalog_path.stat().st_mode) & 0o077):
            raise PVError("M4B_PV_INSPECTION_CATALOG_INVALID")
        catalog = _read_json(catalog_path, max_bytes=16 * 1024 * 1024)
        if (catalog.get("schema_version") != 1 or catalog.get("pv_run_id") != pv_run_id
                or catalog.get("test_id") != test_id or catalog.get("expected_tuple") != expected
                or catalog.get("result_card_locator") != card_path.relative_to(public_root).as_posix()
                or catalog.get("result_card_sha256") != _sha256(card_path)):
            raise PVError("M4B_PV_INSPECTION_CATALOG_INVALID")
        manifest_path = _inspection_path(private_root, catalog.get("evidence_manifest_locator"))
        if (manifest_path != catalog_path.parent / "evidence-manifest.json"
                or stat.S_IMODE(manifest_path.stat().st_mode) & 0o077
                or catalog.get("evidence_manifest_sha256") != _sha256(manifest_path)):
            raise PVError("M4B_PV_INSPECTION_MANIFEST_INVALID")
        manifest = _read_json(manifest_path)
        if (manifest.get("schema_version") != 1 or manifest.get("pv_run_id") != pv_run_id
                or manifest.get("test_id") != test_id or manifest.get("expected_tuple") != expected
                or manifest.get("result_card_locator") != catalog["result_card_locator"]
                or manifest.get("result_card_sha256") != catalog["result_card_sha256"]):
            raise PVError("M4B_PV_INSPECTION_MANIFEST_INVALID")
        card_locators = manifest.get("public_cards")
        partition_locators = manifest.get("private_partitions")
        if (type(card_locators) is not list or type(partition_locators) is not list
                or not card_locators or not partition_locators):
            raise PVError("M4B_PV_INSPECTION_MANIFEST_INVALID")
        cards = [_inspection_path(public_root, locator) for locator in card_locators]
        parts = [private_root / locator for locator in partition_locators]
        if (cards[0] != card_path or parts[0] != catalog_path.parent
                or any(type(locator) is not str or Path(locator).is_absolute()
                       or ".." in Path(locator).parts or "\x00" in locator
                       or part.is_symlink() or not part.is_dir()
                       or not part.resolve(strict=True).is_relative_to(private_root)
                       for locator, part in zip(partition_locators, parts))):
            raise PVError("M4B_PV_INSPECTION_MANIFEST_INVALID")
        if test_id in AGGREGATE_CASES:
            case_rows = _read_json(card_path).get("cases")
            if (type(case_rows) is not list or len(case_rows) != len(AGGREGATE_CASES[test_id])
                    or len(cards) != len(case_rows) + 1 or len(parts) != len(case_rows) + 1):
                raise PVError("M4B_PV_INSPECTION_CASES_INCOMPLETE")
            for index, row in enumerate(case_rows, 1):
                case_card = _read_json(cards[index])
                if (case_card.get("case_id") != row.get("case_id")
                        or case_card.get("case_attempt_id") != row.get("case_attempt_id")
                        or _sha256(cards[index]) != row.get("card_sha256")
                        or parts[index] != _case_private_partition(private_root,
                            test_id=test_id, pv_run_id=pv_run_id,
                            case_attempt_id=row["case_attempt_id"], expected=expected)):
                    raise PVError("M4B_PV_INSPECTION_CASES_INCOMPLETE")
        else:
            capture_name = _INSPECTION_CAPTURE[test_id]
            if len(cards) != 1 or len(parts) != 1 or not (parts[0] / capture_name).is_file():
                raise PVError("M4B_PV_INSPECTION_EVIDENCE_INCOMPLETE")
            capture = _read_json(parts[0] / capture_name)
            if (capture.get("test_id") != test_id or capture.get("pv_run_id") != pv_run_id
                    or capture.get("expected_tuple") != expected):
                raise PVError("M4B_PV_INSPECTION_EVIDENCE_INCOMPLETE")
        files, fields, rows = _inspection_files(public_root, private_root, cards, parts)
        if (manifest.get("files") != files or catalog.get("fields") != fields
                or catalog.get("rows") != rows
                or manifest.get("expected_field_count") != len(fields)
                or manifest.get("expected_row_count") != len(rows)
                or catalog.get("expected_field_count") != len(fields)
                or catalog.get("expected_row_count") != len(rows)
                or not fields or not rows):
            raise PVError("M4B_PV_INSPECTION_CATALOG_INCOMPLETE")
        return catalog, manifest
    except (OSError, ValueError, TypeError, KeyError):
        raise PVError("M4B_PV_INSPECTION_CATALOG_INVALID") from None


def _run_developer_review(args) -> int:
    if (args.test_id not in DEVELOPER_REVIEW_CATEGORIES
            or args.review_status not in {"Pass", "Fail"}
            or type(args.reviewed_field_count) is not int
            or type(args.reviewed_row_count) is not int
            or not args.commentary.strip() or not args.failed_item.strip()):
        raise PVError("M4B_PV_DEVELOPER_REVIEW_INVALID")
    _identifier(args.pv_run_id, "RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    expected = binding["expected_tuple"]
    aggregate = args.test_id in AGGREGATE_CASES
    card_path, card = _select_single(public_root, private_root, pv_run_id=args.pv_run_id,
                                     test_id=args.test_id, expected=expected,
                                     aggregate=aggregate)
    if card.get("script_status") != "Pass" or card.get("status") != "NeedsDeveloperReview":
        raise PVError("M4B_PV_DEVELOPER_REVIEW_STATE_INVALID")
    catalog_path = args.inspection_catalog.absolute()
    catalog, _manifest = _verify_inspection_catalog(
        catalog_path=catalog_path, private_root=private_root, public_root=public_root,
        test_id=args.test_id, pv_run_id=args.pv_run_id, expected=expected,
        card_path=card_path)
    if (args.reviewed_field_count != catalog["expected_field_count"]
            or args.reviewed_row_count != catalog["expected_row_count"]):
        raise PVError("M4B_PV_DEVELOPER_REVIEW_COUNT_MISMATCH")
    locators = {item["locator"] for item in (*catalog["fields"], *catalog["rows"])}
    if aggregate:
        locators.update(AGGREGATE_CASES[args.test_id])
    if (args.review_status == "Pass" and args.failed_item != "NONE"
            or args.review_status == "Fail" and args.failed_item not in locators):
        raise PVError("M4B_PV_DEVELOPER_REVIEW_FAILED_ITEM_INVALID")
    card_digest = _sha256(card_path)
    record = {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "test_id": args.test_id, "expected_tuple": expected,
        "result_card_locator": card_path.relative_to(public_root).as_posix(),
        "result_card_sha256": card_digest,
        "inspection_catalog_locator": catalog_path.relative_to(private_root).as_posix(),
        "inspection_catalog_sha256": _sha256(catalog_path),
        "evidence_manifest_locator": catalog["evidence_manifest_locator"],
        "evidence_manifest_sha256": catalog["evidence_manifest_sha256"],
        "expected_field_count": catalog["expected_field_count"],
        "reviewed_field_count": args.reviewed_field_count,
        "expected_row_count": catalog["expected_row_count"],
        "reviewed_row_count": args.reviewed_row_count,
        "failed_item": args.failed_item, "anomaly_notes": args.commentary.strip(),
        "status": args.review_status}
    path = _review_path(private_root, args.test_id, card_digest)
    if path.exists():
        raise PVError("M4B_PV_DEVELOPER_REVIEW_ALREADY_RECORDED")
    _write_json(path, record, mode=0o600)
    status_root = public_root / "developer-status"
    status_root.mkdir(mode=0o755, exist_ok=True)
    status_path = status_root / f"{args.test_id}-{card_digest}.json"
    if status_path.exists():
        raise PVError("M4B_PV_DEVELOPER_REVIEW_ALREADY_RECORDED")
    _write_json(status_path, {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "test_id": args.test_id, "expected_tuple": expected,
        "result_card_sha256": card_digest, "script_status": "Pass",
        "review_sha256": _sha256(path), "status": args.review_status}, mode=0o644)
    print(json.dumps({"status": args.review_status, "test_id": args.test_id,
                      "developer_review": str(path),
                      "public_status": str(status_path),
                      "reviewed_field_count": args.reviewed_field_count,
                      "reviewed_row_count": args.reviewed_row_count}, sort_keys=True), flush=True)
    return 0 if args.review_status == "Pass" else 1


def _load_developer_review(private_root: Path, public_root: Path, *, test_id: str,
                           pv_run_id: str, expected: Mapping[str, object],
                           card_path: Path) -> dict[str, object]:
    card_digest = _sha256(card_path)
    path = _review_path(private_root, test_id, card_digest)
    try:
        value = _read_json(path)
        required = {"schema_version", "pv_run_id", "test_id", "expected_tuple",
            "result_card_locator", "result_card_sha256", "inspection_catalog_locator",
            "inspection_catalog_sha256", "evidence_manifest_locator",
            "evidence_manifest_sha256", "expected_field_count", "reviewed_field_count",
            "expected_row_count", "reviewed_row_count", "failed_item", "anomaly_notes",
            "status"}
        if (set(value) != required or value.get("schema_version") != 1
                or value.get("pv_run_id") != pv_run_id
                or value.get("test_id") != test_id or value.get("expected_tuple") != expected
                or value.get("result_card_locator") != card_path.relative_to(public_root).as_posix()
                or value.get("result_card_sha256") != card_digest
                or value.get("status") not in {"Pass", "Fail"}
                or type(value.get("anomaly_notes")) is not str or not value["anomaly_notes"]):
            raise ValueError
        catalog_path = _inspection_path(private_root, value["inspection_catalog_locator"])
        if (_sha256(catalog_path) != value["inspection_catalog_sha256"]
                or stat.S_IMODE(path.stat().st_mode) & 0o077):
            raise ValueError
        catalog, _manifest = _verify_inspection_catalog(
            catalog_path=catalog_path, private_root=private_root,
            public_root=public_root, test_id=test_id, pv_run_id=pv_run_id,
            expected=expected, card_path=card_path)
        if (value["evidence_manifest_locator"] != catalog["evidence_manifest_locator"]
                or value["evidence_manifest_sha256"] != catalog["evidence_manifest_sha256"]
                or value["expected_field_count"] != catalog["expected_field_count"]
                or value["reviewed_field_count"] != catalog["expected_field_count"]
                or value["expected_row_count"] != catalog["expected_row_count"]
                or value["reviewed_row_count"] != catalog["expected_row_count"]):
            raise ValueError
        status_path = public_root / "developer-status" / f"{test_id}-{card_digest}.json"
        status = _read_json(status_path)
        if (status.get("pv_run_id") != pv_run_id or status.get("test_id") != test_id
                or status.get("expected_tuple") != expected
                or status.get("result_card_sha256") != card_digest
                or status.get("review_sha256") != _sha256(path)
                or status.get("status") != value["status"]):
            raise ValueError
    except (OSError, ValueError, PVError):
        raise PVError("M4B_PV_DEVELOPER_REVIEW_INCOMPLETE") from None
    return value


def _finalize(args) -> int:
    _identifier(args.pv_run_id, "RUN_ID")
    binding, public_root, private_root = _load_binding(args)
    if (args.public_root.absolute().resolve(strict=True) != public_root
            or args.private_root.absolute().resolve(strict=True) != private_root):
        raise PVError("M4B_PV_FINAL_ROOT_INVALID")
    expected = binding["expected_tuple"]
    selected: dict[str, tuple[Path, dict[str, object]] | list[tuple[Path, dict[str, object]]]] = {}
    selection_errors: dict[str, str] = {}
    for test_id in ("M4B-PI-ATT-001", "M4B-PI-CONV-001", "M4B-PI-MEM-001",
                    "M4B-PI-TIME-001"):
        try:
            selected[test_id] = _select_single(public_root, private_root,
                pv_run_id=args.pv_run_id, test_id=test_id, expected=expected)
        except PVError as error:
            selection_errors[test_id] = str(error)
    try:
        selected["M4B-PI-SEM-001"] = _select_cases(
            public_root, private_root, pv_run_id=args.pv_run_id,
            test_id="M4B-PI-SEM-001", expected=expected,
            required=tuple(SEMANTIC_CASES))
    except PVError as error:
        selection_errors["M4B-PI-SEM-001"] = str(error)
    for test_id in AGGREGATE_CASES:
        try:
            selected[test_id] = _select_single(
                public_root, private_root, pv_run_id=args.pv_run_id,
                test_id=test_id, expected=expected, aggregate=True)
            _validate_aggregate_card(selected[test_id][1], test_id=test_id)
            designated_cases = _select_cases(public_root, private_root,
                pv_run_id=args.pv_run_id, test_id=test_id, expected=expected,
                required=AGGREGATE_CASES[test_id])
            for row, (path, card) in zip(selected[test_id][1]["cases"], designated_cases):
                if (row["case_attempt_id"] != card.get("case_attempt_id")
                        or row["card_sha256"] != _sha256(path)):
                    raise PVError("M4B_PV_AGGREGATE_SELECTION_STALE")
        except PVError as error:
            selection_errors[test_id] = str(error)
            try:
                selected[test_id] = _select_cases(public_root, private_root,
                    pv_run_id=args.pv_run_id, test_id=test_id,
                    expected=expected, required=AGGREGATE_CASES[test_id])
            except PVError:
                pass

    public_tests = []
    private_cards = []
    developer_reviews = {}
    for test_id in PV_TEST_IDS:
        value = selected.get(test_id)
        entries = value if isinstance(value, list) else ([value] if value else [])
        cases = []
        assertions = {}
        reasons = []
        script_states = []
        state = "Pass"
        if test_id in selection_errors:
            state = "Incomplete"
            reasons.append(selection_errors[test_id])
        for path, card in entries:
            digest = _sha256(path)
            private_cards.append({"test_id": test_id,
                "case_id": card.get("case_id"),
                "card_locator": str(path.relative_to(public_root)),
                "card_sha256": digest})
            if "case_id" in card:
                cases.append({"case_id": card["case_id"], "status": card.get("status"),
                              "card_sha256": digest})
            script = card.get("script_status")
            if (script not in {"Pass", "Fail", "Incomplete", "Blocked"}
                    or card.get("expected_tuple") != expected):
                script = "Incomplete"
                reasons.append("M4B_PV_SCRIPT_IDENTITY_INCOMPLETE")
            script_states.append(script)
            if script != "Pass":
                if ("Fail", "Incomplete", "Blocked").index(script) < (
                        ("Fail", "Incomplete", "Blocked").index(state)
                        if state in {"Fail", "Incomplete", "Blocked"} else 3):
                    state = script
                reasons.append(str(card.get("error_code") or "M4B_PV_SCRIPT_UNSATISFIED"))
            if type(card.get("assertions")) is dict:
                if set(assertions) & set(card["assertions"]):
                    raise PVError("M4B_PV_RESULT_CARD_INVALID")
                assertions.update(card["assertions"])
            if type(card.get("cases")) is list:
                cases.extend(card["cases"])
        if assertions and any(result != "Pass" for result in assertions.values()):
            state = "Fail"
            reasons.append("M4B_PV_ASSERTION_FAILED")
        developer_review = None
        user_result = None
        if state == "Pass" and test_id in DEVELOPER_REVIEW_CATEGORIES:
            review_path = _review_path(private_root, test_id, _sha256(entries[0][0]))
            if not review_path.exists():
                state = "NeedsDeveloperReview"
                reasons.append("M4B_PV_DEVELOPER_REVIEW_MISSING")
            else:
                try:
                    review = _load_developer_review(private_root, public_root,
                        test_id=test_id, pv_run_id=args.pv_run_id,
                        expected=expected, card_path=entries[0][0])
                    developer_reviews[test_id] = review
                    developer_review = {key: review[key] for key in (
                        "status", "result_card_sha256", "inspection_catalog_sha256",
                        "evidence_manifest_sha256", "reviewed_field_count",
                        "reviewed_row_count")}
                    state = review["status"]
                    if state == "Fail":
                        reasons.append("M4B_PV_DEVELOPER_REVIEW_FAILED")
                except PVError as error:
                    state = "Incomplete"
                    reasons.append(str(error))
        elif state == "Pass":
            user_result = []
            for path, card in entries:
                verdict = card.get("user_verdict")
                capture_path = path.parent / "capture.json"
                if (verdict in {"Pass", "Fail"} and capture_path.is_file()
                        and card.get("capture_card_sha256") == _sha256(capture_path)
                        and card.get("case_attempt_id") == _read_json(capture_path).get("case_attempt_id")):
                    try:
                        private_case = _case_private_partition(private_root,
                            test_id=test_id, pv_run_id=args.pv_run_id,
                            case_attempt_id=card["case_attempt_id"], expected=expected)
                        if card.get("capture_sha256") != _sha256(
                                private_case / "semantic-capture.json"):
                            raise PVError("M4B_PV_SEMANTIC_CAPTURE_STALE")
                    except PVError as error:
                        state = "Incomplete"
                        reasons.append(str(error))
                    else:
                        user_result.append({"case_id": card["case_id"], "status": verdict})
                        if verdict == "Fail":
                            state = "Fail"
                            reasons.append("M4B_PV_USER_VERDICT_FAILED")
                elif verdict is None and path.name == "capture.json":
                    try:
                        private_case = _case_private_partition(private_root,
                            test_id=test_id, pv_run_id=args.pv_run_id,
                            case_attempt_id=card["case_attempt_id"], expected=expected)
                        if card.get("capture_sha256") != _sha256(
                                private_case / "semantic-capture.json"):
                            raise PVError("M4B_PV_SEMANTIC_CAPTURE_STALE")
                    except PVError as error:
                        state = "Incomplete" if state != "Fail" else state
                        reasons.append(str(error))
                    else:
                        user_result.append({"case_id": card["case_id"],
                                            "status": "NeedsHumanReview"})
                        if state not in {"Fail", "Incomplete"}:
                            state = "NeedsHumanReview"
                        reasons.append("M4B_PV_USER_VERDICT_MISSING")
                else:
                    if state != "Fail":
                        state = "Incomplete"
                    reasons.append("M4B_PV_HUMAN_RESULT_INCOMPLETE")
        script_status = next((status for status in ("Fail", "Incomplete", "Blocked")
            if status in script_states), "Pass" if script_states else "Incomplete")
        public_tests.append({"test_id": test_id, "script_status": script_status,
                             "developer_review": developer_review,
                             "user_result": user_result,
                             "status": state, "reason_codes": sorted(set(reasons)),
                             "assertions": assertions, "cases": cases})

    mem_selected = selected.get("M4B-PI-MEM-001")
    mem_card = mem_selected[1] if isinstance(mem_selected, tuple) else {}
    estimates = {name: mem_card.get(name) for name in (
        "speak_drop_bytes", "generate_drop_bytes",
        "min_mem_available_speak_bytes", "min_mem_available_generate_bytes")}
    measurement_status = ("Pass" if all(type(value) is int and value >= 0
        for value in estimates.values()) else "Incomplete")
    dispositions = {row["status"] for row in public_tests}
    pv_status = next((status for status in (
        "Fail", "Incomplete", "Blocked", "NeedsHumanReview", "NeedsDeveloperReview")
        if status in dispositions), "Pass")
    if measurement_status != "Pass" and pv_status == "Pass":
        pv_status = "Incomplete"
    private_manifest = {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "expected_tuple": expected, "selected_cards": private_cards,
        "developer_reviews": developer_reviews,
        "automated_status": "Pass" if all(row["script_status"] == "Pass"
            for row in public_tests) else "Incomplete",
        "human_status": "Pass" if all(row["status"] == "Pass"
            for row in public_tests) else pv_status,
        "measurement_status": measurement_status, "pv_status": pv_status}
    version = 1
    while (private_root / ("pv-final-manifest.json" if version == 1 else
            f"pv-final-manifest-{version:04d}.json")).exists() or (
            public_root / ("pv-final.json" if version == 1 else
            f"pv-final-{version:04d}.json")).exists():
        version += 1
    if version > 9999:
        raise PVError("M4B_PV_FINAL_VERSION_EXHAUSTED")
    private_path = private_root / ("pv-final-manifest.json" if version == 1 else
        f"pv-final-manifest-{version:04d}.json")
    _write_json(private_path, private_manifest, mode=0o600)
    public_manifest = {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "expected_tuple": expected, "tests": public_tests, "estimates": estimates,
        "automated_status": private_manifest["automated_status"],
        "human_status": private_manifest["human_status"],
        "measurement_status": measurement_status,
        "private_manifest_sha256": _sha256(private_path), "pv_status": pv_status}
    public_path = public_root / ("pv-final.json" if version == 1 else
        f"pv-final-{version:04d}.json")
    _write_json(public_path, public_manifest, mode=0o644)
    print(json.dumps({"pv_status": pv_status, "public_manifest": str(public_path),
                      "private_manifest": str(private_path)}, sort_keys=True), flush=True)
    return 0 if pv_status == "Pass" else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--pv-run-id", required=True)
    init.add_argument("--public-root", type=Path, required=True)
    init.add_argument("--private-root", type=Path, required=True)
    init.add_argument("--binding-manifest", type=Path, required=True)
    semantic = commands.add_parser("run-semantic-case")
    semantic.add_argument("--test-id", required=True)
    semantic.add_argument("--case-id", required=True)
    semantic.add_argument("--utterance", required=True)
    semantic.add_argument("--pv-run-id", required=True)
    semantic.add_argument("--sub-run-id", required=True)
    semantic.add_argument("--case-attempt-id", required=True)
    semantic.add_argument("--public-partition", type=Path, required=True)
    semantic.add_argument("--private-partition", type=Path, required=True)
    semantic.add_argument("--binding-manifest", type=Path, required=True)
    semantic.add_argument("--fresh-setup", action="store_true")
    semantic.add_argument("--fresh-conversation", action="store_true")
    wake = commands.add_parser("run-wake-case")
    wake.add_argument("--test-id", required=True)
    wake.add_argument("--case-id", required=True)
    wake.add_argument("--pv-run-id", required=True)
    wake.add_argument("--sub-run-id", required=True)
    wake.add_argument("--case-attempt-id", required=True)
    wake.add_argument("--public-partition", type=Path, required=True)
    wake.add_argument("--private-partition", type=Path, required=True)
    wake.add_argument("--binding-manifest", type=Path, required=True)
    wake.add_argument("--fresh-setup", action="store_true")
    wake.add_argument("--production-wake-path", action="store_true")
    resource = commands.add_parser("run-resource-case")
    resource.add_argument("--test-id", required=True)
    resource.add_argument("--case-id", required=True)
    resource.add_argument("--pv-run-id", required=True)
    resource.add_argument("--sub-run-id", required=True)
    resource.add_argument("--case-attempt-id", required=True)
    resource.add_argument("--public-partition", type=Path, required=True)
    resource.add_argument("--private-partition", type=Path, required=True)
    resource.add_argument("--binding-manifest", type=Path, required=True)
    resource.add_argument("--fresh-setup", action="store_true")
    run = commands.add_parser("run")
    run.add_argument("--test-id", required=True)
    run.add_argument("--pv-run-id", required=True)
    run.add_argument("--sub-run-id", required=True)
    run.add_argument("--public-partition", type=Path, required=True)
    run.add_argument("--private-partition", type=Path, required=True)
    run.add_argument("--binding-manifest", type=Path, required=True)
    run.add_argument("--fresh-setup", action="store_true")
    run.add_argument("--audio-fixture", type=Path)
    aggregate = commands.add_parser("aggregate-cases")
    aggregate.add_argument("--test-id", required=True)
    aggregate.add_argument("--pv-run-id", required=True)
    aggregate.add_argument("--public-partition", type=Path, required=True)
    aggregate.add_argument("--private-partition", type=Path, required=True)
    aggregate.add_argument("--binding-manifest", type=Path, required=True)
    designate = commands.add_parser("designate-result")
    designate.add_argument("--pv-run-id", required=True)
    designate.add_argument("--test-id", required=True)
    designate.add_argument("--case-id")
    designate.add_argument("--result-card", type=Path, required=True)
    designate.add_argument("--binding-manifest", type=Path, required=True)
    finalize = commands.add_parser("finalize")
    finalize.add_argument("--pv-run-id", required=True)
    finalize.add_argument("--public-root", type=Path, required=True)
    finalize.add_argument("--private-root", type=Path, required=True)
    finalize.add_argument("--binding-manifest", type=Path, required=True)
    review = commands.add_parser("record-developer-review")
    review.add_argument("--test-id", required=True)
    review.add_argument("--pv-run-id", required=True)
    review.add_argument("--binding-manifest", type=Path, required=True)
    review.add_argument("--inspection-catalog", type=Path, required=True)
    review.add_argument("--review-status", choices=("Pass", "Fail"), required=True)
    review.add_argument("--reviewed-field-count", type=int, required=True)
    review.add_argument("--reviewed-row-count", type=int, required=True)
    review.add_argument("--failed-item", required=True)
    review.add_argument("--commentary", required=True)
    return parser


def main(argv=None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "init":
            return _init(args)
        if args.command == "run-semantic-case":
            return _run_semantic_case(args)
        if args.command == "run-wake-case":
            return _run_wake_case(args)
        if args.command == "run-resource-case":
            return _run_resource_case(args)
        if args.command == "aggregate-cases":
            return _run_aggregate_cases(args)
        if args.command == "designate-result":
            return _run_designate_result(args)
        if args.command == "finalize":
            return _finalize(args)
        if args.command == "record-developer-review":
            return _run_developer_review(args)
        if args.command == "run" and args.test_id == "M4B-PI-ATT-001" and args.audio_fixture is None:
            return _run_att(args)
        if args.command == "run" and args.test_id == "M4B-PI-CONV-001":
            return _run_conv(args)
        if args.command == "run" and args.test_id == "M4B-PI-MEM-001":
            return _run_mem(args)
        if args.command == "run" and args.test_id == "M4B-PI-TIME-001":
            return _run_time(args)
        raise PVError("M4B_PV_COMMAND_INVALID")
    except PVError as error:
        print(json.dumps({"status": "Blocked", "error_code": str(error)}, sort_keys=True),
              flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
