"""Strict M4a product-lock parsing and artifact verification.

This module deliberately imports no candidate-native package.  Controller-side
configuration and factories may therefore validate the complete Audio identity
before creating a child process, work directory, or Audio HAL owner.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ACCEPTED_AUDIO_SHA = "5694ead4ba6be928fdb4dbdf6da7155b214d72bd"
LOCK_SCHEMA = "sbd.m4a.audio-artifacts.v1"
EXPECTED_LOCK_SHA256 = "21389a0fb6030a9ca74645003239119a9e299bd2719b98e2df15bc19a0c360d4"
BUILD_RESULT_SCHEMA = "sbd.m4a.whispercpp-build-result.v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TARGET = MappingProxyType({"os": "linux", "arch": "aarch64", "python": "3.13"})
WHISPER_SOURCE_SHA256 = "988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47"
WHISPER_WRAPPER_SOURCES_SHA256 = "2035e9358b2058f7f3da3e6fb9d859db4b03c9ef6940a6c8a90e8289f019da55"
WHISPER_CMAKE_OPTIONS = (
    "-DBUILD_SHARED_LIBS=OFF", "-DGGML_NATIVE=OFF", "-DGGML_BLAS=OFF",
    "-DGGML_CUDA=OFF", "-DGGML_VULKAN=OFF", "-DGGML_OPENCL=OFF",
    "-DGGML_RPC=OFF", "-DGGML_OPENMP=OFF", "-DGGML_METAL=OFF",
    "-DGGML_SYCL=OFF", "-DGGML_KOMPUTE=OFF", "-DGGML_CCACHE=OFF",
    "-DWHISPER_CURL=OFF", "-DWHISPER_BUILD_SERVER=OFF",
    "-DWHISPER_COMMON_FFMPEG=OFF", "-DWHISPER_SDL2=OFF",
    "-DWHISPER_BUILD_TESTS=OFF", "-DWHISPER_BUILD_EXAMPLES=OFF",
    "-DWHISPER_USE_SYSTEM_GGML=OFF", "-DWHISPER_COREML=OFF",
    "-DWHISPER_OPENVINO=OFF", "-DWHISPER_MKL=OFF",
)
EXPECTED_ARTIFACTS = MappingProxyType({
    "vad-onnxruntime": ("1.29.0", 20816263, "d67673c5367727860922c5262d724472f1b5539fb7ccf4c81a638f9b71719803"),
    "vad-flatbuffers": ("25.12.19", 26661, "7634f50c427838bb021c2d66a3d1168e9d199b0607e6329399f04846d42e20b4"),
    "runtime-numpy": ("2.5.2", 15609566, "0aadf13b60048d501e05fa699efaf7734e2494f3498a4c2a5521d822640324f3"),
    "vad-packaging": ("26.3", 129956, "d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c"),
    "vad-protobuf": ("7.36.0", 341436, "bf94a5917c71058262de683669bc0a797a7669d3de71f0b36d058e3194f47b44"),
    "tts-sherpa-onnx": ("1.13.5", 4167203, "f5a6cc5ac96043670faa0f5c0e56310315a4600cf7b764fee014e7dd75fda00f"),
    "tts-sherpa-onnx-core": ("1.13.5", 13051193, "4cd751063a378a49f0c72eba5ba959fe375397f5baf93a53f3db64097d00e2aa"),
    "silero-model": ("6.2.1", 2327524, "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"),
    "whisper-source": ("1.9.2", 9613762, "988945d81af6abcf52d5e8034f516c74ffc61057c32c3a4b84f3451c2c7e5e47"),
    "whisper-model": ("base-q8_0", 81768585, "c577b9a86e7e048a0b7eada054f4dd79a56bbfa911fbdacf900ac5b567cbb7d9"),
    "matcha-archive": ("zh-en-2026-01-28", 79033838, "271b804af570400d3bcdcb53bf6e53cc9f75180ee763b9f13eb5eaf2b0d086ef"),
    "matcha-model": ("steps-3", 75717082, "524286bf6cf11be74329ae1c682ac69e34d6860c2ea9fd1290319d561540b16a"),
    "vocos-model": ("16khz-univ", 53882848, "b599142a1fb8ff03de3e84ac35ff537c619e56f4267a6fe894851a42844acf9e"),
})


class AudioLockError(ValueError):
    """The tracked Audio product identity is absent, malformed, or mismatched."""


@dataclass(frozen=True, slots=True)
class LockedArtifact:
    kind: str
    name: str
    version: str
    filename: str
    size_bytes: int
    sha256: str
    source_locator: str
    notice_ref: str
    target_os: str
    target_arch: str
    target_python: str
    baseline_source_sha: str

    def verify(self, path: Path) -> None:
        if not path.is_file() or path.is_symlink():
            raise AudioLockError(f"artifact is missing or is not a regular file: {self.name}")
        if path.name != self.filename:
            raise AudioLockError(f"artifact filename mismatch: {self.name}")
        if path.stat().st_size != self.size_bytes:
            raise AudioLockError(f"artifact size mismatch: {self.name}")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != self.sha256:
            raise AudioLockError(f"artifact checksum mismatch: {self.name}")


@dataclass(frozen=True, slots=True)
class AudioArtifactLock:
    path: Path
    digest: str
    accepted_audio_sha: str
    delivery_id: str
    profiles: Mapping[str, Mapping[str, Any]]
    artifacts: tuple[LockedArtifact, ...]

    @classmethod
    def load(cls, path: Path) -> "AudioArtifactLock":
        if not path.is_file() or path.is_symlink():
            raise AudioLockError("artifact lock is missing or is not a regular file")
        try:
            raw_bytes = path.read_bytes()
            raw = json.loads(raw_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AudioLockError("artifact lock is unreadable or invalid JSON") from error
        if not isinstance(raw, dict):
            raise AudioLockError("artifact lock must be a JSON object")
        if hashlib.sha256(raw_bytes).hexdigest() != EXPECTED_LOCK_SHA256:
            raise AudioLockError("artifact lock bytes differ from the Accepted baseline")
        _exact_keys(
            raw,
            {"schema", "accepted_audio_sha", "delivery_id", "target", "profiles", "artifacts"},
            "artifact lock",
        )
        if raw["schema"] != LOCK_SCHEMA:
            raise AudioLockError("artifact lock schema mismatch")
        if raw["accepted_audio_sha"] != ACCEPTED_AUDIO_SHA:
            raise AudioLockError("Accepted Audio SHA mismatch")
        if raw["delivery_id"] != "POC-audio-DEL-2026-001-R1":
            raise AudioLockError("Audio delivery identity mismatch")
        if raw["target"] != dict(TARGET):
            raise AudioLockError("target interpreter or architecture mismatch")
        profiles = _profiles(raw["profiles"])
        values = raw["artifacts"]
        if not isinstance(values, list) or not values:
            raise AudioLockError("artifacts must be a non-empty array")
        artifacts = tuple(_artifact(value, index) for index, value in enumerate(values))
        names = [item.name for item in artifacts]
        filenames = [item.filename for item in artifacts]
        if len(set(names)) != len(names) or len(set(filenames)) != len(filenames):
            raise AudioLockError("artifact names and filenames must be unique")
        if set(names) != set(EXPECTED_ARTIFACTS):
            raise AudioLockError("artifact inventory does not match the Accepted baseline")
        for artifact in artifacts:
            if (artifact.version, artifact.size_bytes, artifact.sha256) != EXPECTED_ARTIFACTS[artifact.name]:
                raise AudioLockError(f"artifact identity mismatch: {artifact.name}")
        return cls(
            path=path.resolve(),
            digest=hashlib.sha256(raw_bytes).hexdigest(),
            accepted_audio_sha=raw["accepted_audio_sha"],
            delivery_id=raw["delivery_id"],
            profiles=MappingProxyType(profiles),
            artifacts=artifacts,
        )

    def require(self, name: str) -> LockedArtifact:
        for artifact in self.artifacts:
            if artifact.name == name:
                return artifact
        raise AudioLockError(f"required artifact is absent: {name}")

    def verify_input_root(self, root: Path, names: tuple[str, ...] | None = None) -> None:
        selected = self.artifacts if names is None else tuple(self.require(name) for name in names)
        expected = {item.filename for item in selected}
        if not root.is_dir() or root.is_symlink():
            raise AudioLockError("controlled input root is missing or invalid")
        actual = {path.name for path in root.iterdir() if path.is_file() and not path.is_symlink()}
        non_files = [path for path in root.iterdir() if not path.is_file() or path.is_symlink()]
        if non_files or actual != expected:
            raise AudioLockError("controlled input inventory has missing, extra, or unsafe entries")
        for artifact in selected:
            artifact.verify(root / artifact.filename)

    def verify_asr_config(self, config: Any) -> None:
        self.require("whisper-model").verify(config.model_path)
        self.require("silero-model").verify(config.vad_model_path)
        self.worker_binary_sha256(config.worker_path)
        _verify_isolated_python(config.runtime_python, "VAD runtime")

    def worker_binary_sha256(self, path: Path) -> str:
        """Verify a Core rebuild against the pinned source/options and its bytes."""
        result_path = path.with_suffix(path.suffix + ".json")
        if not result_path.is_file() or result_path.is_symlink():
            raise AudioLockError("ASR worker build result is missing or invalid")
        try:
            result = json.loads(result_path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AudioLockError("ASR worker build result is unreadable or invalid JSON") from error
        if not isinstance(result, dict):
            raise AudioLockError("ASR worker build result must be an object")
        fields = {
            "schema", "source_sha256", "cmake_options_sha256",
            "wrapper_sources_sha256", "binary_filename", "binary_size_bytes",
            "binary_sha256",
        }
        _exact_keys(result, fields, "ASR worker build result")
        options_sha256 = hashlib.sha256(
            json.dumps(WHISPER_CMAKE_OPTIONS, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            result["schema"] != BUILD_RESULT_SCHEMA
            or result["source_sha256"] != WHISPER_SOURCE_SHA256
            or result["cmake_options_sha256"] != options_sha256
            or result["wrapper_sources_sha256"] != WHISPER_WRAPPER_SOURCES_SHA256
            or result["binary_filename"] != path.name
            or type(result["binary_size_bytes"]) is not int
            or result["binary_size_bytes"] <= 0
            or not SHA256_RE.fullmatch(str(result["binary_sha256"]))
        ):
            raise AudioLockError("ASR worker build identity mismatch")
        if not path.is_file() or path.is_symlink() or not path.stat().st_mode & 0o111:
            raise AudioLockError("ASR worker is missing, unsafe, or not executable")
        if path.stat().st_size != result["binary_size_bytes"]:
            raise AudioLockError("ASR worker size mismatch")
        _verify_sha256(path, result["binary_sha256"], "ASR worker")
        return result["binary_sha256"]

    def verify_tts_config(self, config: Any) -> None:
        self.require("matcha-model").verify(config.model_path / "model-steps-3.onnx")
        self.require("vocos-model").verify(config.vocoder_path)
        _verify_isolated_python(config.runtime_python, "TTS runtime")


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise AudioLockError(f"{label} has missing or extra fields")


def _profiles(value: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, dict):
        raise AudioLockError("profiles must be an object")
    expected = {"asr", "tts", "vad"}
    _exact_keys(value, expected, "profiles")
    profile_keys = {
        "asr": {
            "engine", "language", "threads", "strategy", "best_of", "temperature",
            "timestamps", "translate", "internal_vad", "previous_text", "prompt_sha256",
        },
        "tts": {"engine", "voice_id", "sid", "speed", "provider", "threads", "max_sentences", "sample_rate_hz", "channels", "sample_format"},
        "vad": {"engine", "provider", "intra_threads", "inter_threads", "window_samples", "context_samples", "positive_threshold", "negative_threshold", "startup_mask_ms", "minimum_speech_ms", "end_silence_ms", "pre_padding_ms", "post_padding_ms"},
    }
    exact = {
        "asr": {"engine": "whisper.cpp-1.9.2", "language": "zh", "threads": 4, "strategy": "greedy", "best_of": 1, "temperature": 0, "timestamps": False, "translate": False, "internal_vad": False, "previous_text": False, "prompt_sha256": "e3b2606c90009ce609aa23183c2229619619cf1173dc17d2ecd2308bfe4fe8ef"},
        "tts": {"engine": "sherpa-onnx-1.13.5-matcha", "voice_id": "matcha-zh-en-default-sid-0", "sid": 0, "speed": 1.0, "provider": "cpu", "threads": 2, "max_sentences": 1, "sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE"},
        "vad": {"engine": "silero-6.2.1-endpoint-v1", "provider": "CPUExecutionProvider", "intra_threads": 1, "inter_threads": 1, "window_samples": 512, "context_samples": 64, "positive_threshold": 0.5, "negative_threshold": 0.35, "startup_mask_ms": 160, "minimum_speech_ms": 250, "end_silence_ms": 500, "pre_padding_ms": 500, "post_padding_ms": 600},
    }
    result: dict[str, Mapping[str, Any]] = {}
    for name in sorted(expected):
        profile = value[name]
        if not isinstance(profile, dict):
            raise AudioLockError(f"{name} profile must be an object")
        _exact_keys(profile, profile_keys[name], f"{name} profile")
        if profile != exact[name]:
            raise AudioLockError(f"{name} profile mismatch")
        result[name] = MappingProxyType(dict(profile))
    return result


def _artifact(value: Any, index: int) -> LockedArtifact:
    if not isinstance(value, dict):
        raise AudioLockError(f"artifact {index} must be an object")
    fields = {
        "kind", "name", "version", "filename", "size_bytes", "sha256",
        "source_locator", "notice_ref", "target_os", "target_arch", "target_python",
        "baseline_source_sha",
    }
    _exact_keys(value, fields, f"artifact {index}")
    for field in fields - {"size_bytes"}:
        if not isinstance(value[field], str) or not value[field]:
            raise AudioLockError(f"artifact {index}.{field} must be a non-empty string")
    if value["kind"] not in {"artifact", "distribution"}:
        raise AudioLockError(f"artifact {index}.kind is invalid")
    if type(value["size_bytes"]) is not int or value["size_bytes"] <= 0:
        raise AudioLockError(f"artifact {index}.size_bytes must be positive")
    if not SHA256_RE.fullmatch(value["sha256"]):
        raise AudioLockError(f"artifact {index}.sha256 is invalid")
    if not GIT_SHA_RE.fullmatch(value["baseline_source_sha"]):
        raise AudioLockError(f"artifact {index}.baseline_source_sha is invalid")
    if {key: value[f"target_{key}"] for key in ("os", "arch", "python")} != dict(TARGET):
        raise AudioLockError(f"artifact {index} target mismatch")
    if not value["source_locator"].startswith(("https://", "controlled://")):
        raise AudioLockError(f"artifact {index}.source_locator is not immutable/controlled")
    return LockedArtifact(**value)


def _verify_sha256(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise AudioLockError(f"{label} is missing or invalid")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise AudioLockError(f"{label} checksum mismatch")


def _verify_isolated_python(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink() or not path.stat().st_mode & 0o111:
        raise AudioLockError(f"{label} interpreter is missing or not executable")
    cfg = path.parent.parent / "pyvenv.cfg"
    if not cfg.is_file():
        raise AudioLockError(f"{label} is not an isolated virtual environment")
    values = {}
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().lower()] = value.strip().lower()
    if values.get("include-system-site-packages") != "false":
        raise AudioLockError(f"{label} permits system-site packages")


__all__ = [
    "ACCEPTED_AUDIO_SHA", "AudioArtifactLock", "AudioLockError", "LockedArtifact",
]
