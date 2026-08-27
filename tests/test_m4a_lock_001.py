"""M4A-LOCK-001 — fail-closed product lock and artifact identity."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from sbd.adaptor.audio_lock import (
    ACCEPTED_AUDIO_SHA,
    BUILD_RESULT_SCHEMA,
    WHISPER_CMAKE_OPTIONS,
    WHISPER_SOURCE_SHA256,
    WHISPER_WRAPPER_SOURCES_SHA256,
    AudioArtifactLock,
    AudioLockError,
)
from scripts.m4a_audio_product import _load_runtime
from sbd.action.speak.matcha import worker as tts_worker
from sbd.perception.listen.whispercpp import supervisor as asr_supervisor


LOCK_ROOT = Path(__file__).parent.parent / "requirements" / "m4a"


def _mutated_lock(tmp_path: Path, mutate) -> Path:
    value = json.loads((LOCK_ROOT / "audio-artifacts.json").read_text(encoding="utf-8"))
    mutate(value)
    path = tmp_path / "audio-artifacts.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("extra", True),
        lambda value: value.__setitem__("accepted_audio_sha", "0" * 40),
        lambda value: value["target"].__setitem__("arch", "x86_64"),
        lambda value: value["profiles"]["asr"].__setitem__("threads", 8),
        lambda value: value["artifacts"][0].__setitem__("sha256", "0" * 64),
        lambda value: value["artifacts"][0].__setitem__("version", "unexpected"),
        lambda value: value["artifacts"][0].__setitem__("target_python", "3.12"),
        lambda value: value["artifacts"][0].__setitem__("unexpected", "field"),
    ],
)
def test_m4a_lock_001_rejects_schema_identity_hash_version_arch_and_profile(
    tmp_path: Path, mutate,
) -> None:
    path = _mutated_lock(tmp_path, mutate)
    with pytest.raises(AudioLockError):
        AudioArtifactLock.load(path)
    assert list(tmp_path.iterdir()) == [path]


def test_m4a_lock_001_rejects_missing_directory_and_symlink_lock(tmp_path: Path) -> None:
    with pytest.raises(AudioLockError):
        AudioArtifactLock.load(tmp_path / "missing.json")
    link = tmp_path / "link.json"
    link.symlink_to(LOCK_ROOT / "audio-artifacts.json")
    with pytest.raises(AudioLockError):
        AudioArtifactLock.load(link)


def test_m4a_lock_001_accepts_exact_tracked_identity_and_runtime_inventories() -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    assert lock.accepted_audio_sha == ACCEPTED_AUDIO_SHA
    assert len(lock.artifacts) == 13
    assert len(lock.digest) == 64
    assert _load_runtime(LOCK_ROOT / "vad-rpi-cp313.json", "vad", lock).runtime == "vad"
    assert _load_runtime(LOCK_ROOT / "tts-rpi-cp313.json", "tts", lock).runtime == "tts"


@pytest.mark.parametrize(
    ("module", "expected"),
    [
        (asr_supervisor, asr_supervisor.VAD_RUNTIME_DISTRIBUTIONS),
        (tts_worker, tts_worker.TTS_RUNTIME_DISTRIBUTIONS),
    ],
)
def test_m4a_lock_001_actual_child_requires_every_exact_runtime_distribution(
    monkeypatch: pytest.MonkeyPatch, module, expected: dict[str, str],
) -> None:
    monkeypatch.setattr(
        module.importlib.metadata,
        "version",
        lambda name: expected[name],
    )
    module.require_runtime_identity()
    wrong = dict(expected)
    wrong[next(iter(wrong))] = "0"
    monkeypatch.setattr(
        module.importlib.metadata,
        "version",
        lambda name: wrong[name],
    )
    with pytest.raises(RuntimeError, match="RUNTIME_IDENTITY"):
        module.require_runtime_identity()


def test_m4a_lock_001_artifact_verifier_rejects_wrong_bytes(tmp_path: Path) -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    artifact = lock.require("silero-model")
    path = tmp_path / artifact.filename
    path.write_bytes(b"not-the-model")
    with pytest.raises(AudioLockError, match="size mismatch"):
        artifact.verify(path)


@pytest.mark.parametrize(
    ("runtime", "field", "value"),
    [
        ("vad", "interpreter", "CPython 3.12"),
        ("vad", "arch", "x86_64"),
        ("vad", "profile", "wrong"),
        ("tts", "interpreter", "PyPy 3.13"),
        ("tts", "arch", "x86_64"),
        ("tts", "profile", "wrong"),
    ],
)
def test_m4a_lock_001_runtime_lock_rejects_interpreter_arch_and_profile_drift(
    tmp_path: Path, runtime: str, field: str, value: str,
) -> None:
    lock = AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json")
    source = LOCK_ROOT / f"{runtime}-rpi-cp313.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    raw[field] = value
    mutated = tmp_path / source.name
    mutated.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity"):
        _load_runtime(mutated, runtime, lock)


def _worker_fixture(tmp_path: Path) -> tuple[AudioArtifactLock, Path, Path]:
    worker = tmp_path / "m4a-whispercpp-worker"
    worker.write_bytes(b"core-product-worker")
    worker.chmod(0o755)
    result = worker.with_suffix(".json")
    result.write_text(json.dumps({
        "schema": BUILD_RESULT_SCHEMA,
        "source_sha256": WHISPER_SOURCE_SHA256,
        "cmake_options_sha256": hashlib.sha256(
            json.dumps(WHISPER_CMAKE_OPTIONS, separators=(",", ":")).encode()
        ).hexdigest(),
        "wrapper_sources_sha256": WHISPER_WRAPPER_SOURCES_SHA256,
        "binary_filename": worker.name,
        "binary_size_bytes": worker.stat().st_size,
        "binary_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    return AudioArtifactLock.load(LOCK_ROOT / "audio-artifacts.json"), worker, result


def test_m4a_lock_001_accepts_core_binary_delta_only_with_exact_build_result(
    tmp_path: Path,
) -> None:
    lock, worker, _ = _worker_fixture(tmp_path)
    assert lock.worker_binary_sha256(worker) == hashlib.sha256(worker.read_bytes()).hexdigest()


@pytest.mark.parametrize("field", ["source_sha256", "cmake_options_sha256", "wrapper_sources_sha256", "binary_sha256"])
def test_m4a_lock_001_rejects_worker_source_options_or_binary_drift(
    tmp_path: Path, field: str,
) -> None:
    lock, worker, result_path = _worker_fixture(tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result[field] = "0" * 64
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(AudioLockError):
        lock.worker_binary_sha256(worker)
