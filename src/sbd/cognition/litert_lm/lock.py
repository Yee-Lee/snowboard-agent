"""Strict M4b lock and isolated-runtime closure verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from sbd.cognition.llm_child_protocol import LLMReadyIdentity
from sbd.cognition.prompt_builder import PROFILE_ID, PROMPT_COUNTS, PROMPT_HASHES, validate_prompt_identity
from sbd.cognition.semantic import (
    RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256, ResponseSchemaError,
    load_response_schema,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TOP_LEVEL_KEYS = {
    "lock", "poc_reference", "candidate", "runtime", "model",
    "product_profile", "runtime_closure", "licenses",
}

EXPECTED_LOCK = {"schema_version": 2, "protocol_version": "snowboard.llm/3"}
EXPECTED_POC_REFERENCE = {
    "core_ack_id": "DELIVERY-LLM-POC-M4B-GATE2B-FINAL-WINNER-ACK-001",
    "execution_sha": "0c75536e6ee99b502c59438989ca852194648946",
    "closure_sha": "5ffdd9eaa3beb9ca09ff6a63839e02248c9a78ae",
    "publication_sha": "485bb2a7c07d86a09899f09358c744edd733f875",
    "manifest_id": "POC-llm-DEL-2026-001-R3",
    "evidence_id": "G2B-PI-COMBINED-006",
    "sanitized_sha256": "f5f5b3acd15e32bb0208da9f838cec4415469c28c12a45b25f8c2f5f55ad33fa",
}
EXPECTED_CANDIDATE = {
    "candidate_id": "CAND-LRT-G4E2B-MOBILE-R1",
    "pairing_revision": "litert-lm-v0.16.0-pi-g2b-r5",
    "platform": "pi-debian13-aarch64",
}
EXPECTED_RUNTIME = {
    "api_version": "0.16.0",
    "source_commit": "924e79c91542761242244e4f1651851f822e4cbb",
    "wheel_filename": "litert_lm_api-0.16.0-py3-none-manylinux_2_27_aarch64.whl",
    "wheel_size_bytes": 46085754,
    "wheel_sha256": "5eb8c9faa5727730239591f8c912261ec7705512d5f30ec674586bc0005f2b00",
    "native_relative_path": "litert_lm/liblitert-lm.so",
    "native_size_bytes": 131217040,
    "native_sha256": "9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4",
    "spdx": "Apache-2.0",
}
EXPECTED_RUNTIME_FILES = {
    "litert_lm/__init__.py": (2545, "6fd72b12ddef4c64c0c78df62002083fb6404a39f1cf71815d429f92f392bdf0"),
    "litert_lm/_ffi.py": (22068, "be300a5fb939356ee2ebf78e76b8aa40358cc8af8faf3ffe71a1d73c6e4550b9"),
    "litert_lm/_messages.py": (7727, "9cabe70cf26c07fd34283cade50abbd6056ac63329c2e6e513575939707821c4"),
    "litert_lm/benchmark.py": (4838, "c1bc8961dfbb45a43448fae4cd698c0a0d81edac1d592dc029e2853e60b8adc6"),
    "litert_lm/conversation.py": (18519, "eb45d74fa60318388bb44572c3d1e6ceef65e1ad863b3278c0636d57edf8bbd4"),
    "litert_lm/engine.py": (17050, "da40bdd89d66a16537861a674f8a97aba19a78219e351509bd0d94804751c91a"),
    "litert_lm/interfaces.py": (34452, "23a47a8b921beb717a8299be459007ac7a0c68787538befe12142c6d912906a3"),
    "litert_lm/liblitert-lm.so": (131217040, "9b3a319b4878c3fafeea16db06eea7b2f023619e5f97037eb20b8e38662875e4"),
    "litert_lm/session.py": (6319, "786ea19f5ed01134db650ee2c6dd1585d88808bf34c927109bdde664ff31ca75"),
    "litert_lm/tools.py": (3789, "acbd43a0f8498b6a61e6fa67af39e4a1bd0abf547a3fb594171de9f03d7e62f3"),
    "litert_lm/utils.py": (3254, "ddd9486650eb963dddc47f07e1ac29af3e24fb21c388a97f8b4e840f99c6624c"),
    "litert_lm_api-0.16.0.dist-info/METADATA": (906, "61418790e1681e08720bfce61f9cbff9ab9fa3373ab84e5af47fd5967ad0b7a3"),
    "litert_lm_api-0.16.0.dist-info/RECORD": (1093, "f2cc0a97f35d261ebbe43a52ea9bdd5e6212d7e8dc052c034c939b8785f2098b"),
    "litert_lm_api-0.16.0.dist-info/WHEEL": (111, "02a00643f059cd48b88240900282090ea0b08edf837ec4605dadce114014e43b"),
}
EXPECTED_MODEL = {
    "source_repository": "litert-community/gemma-4-E2B-it-litert-lm",
    "source_revision": "6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94",
    "filename": "gemma-4-E2B-it.litertlm",
    "size_bytes": 2588147712,
    "sha256": "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c",
    "quantization": "artifact-embedded-mobile-2-4-8-bit-mixture",
    "spdx": "Apache-2.0",
}
EXPECTED_PROFILE = {
    "profile_id": PROFILE_ID,
    "candidate_id": EXPECTED_CANDIDATE["candidate_id"],
    "pairing_revision": EXPECTED_CANDIDATE["pairing_revision"],
    "platform": EXPECTED_CANDIDATE["platform"],
    "python_implementation": "CPython",
    "python_version": "3.13.5",
    "python_soabi": "cpython-313-aarch64-linux-gnu",
    "python_multiarch": "aarch64-linux-gnu",
    "runtime_api_version": EXPECTED_RUNTIME["api_version"],
    "runtime_source_commit": EXPECTED_RUNTIME["source_commit"],
    "runtime_wheel_filename": EXPECTED_RUNTIME["wheel_filename"],
    "runtime_wheel_size_bytes": EXPECTED_RUNTIME["wheel_size_bytes"],
    "runtime_sha256": EXPECTED_RUNTIME["wheel_sha256"],
    "native_relative_path": EXPECTED_RUNTIME["native_relative_path"],
    "native_size_bytes": EXPECTED_RUNTIME["native_size_bytes"],
    "native_sha256": EXPECTED_RUNTIME["native_sha256"],
    "model_source_repository": EXPECTED_MODEL["source_repository"],
    "model_source_revision": EXPECTED_MODEL["source_revision"],
    "model_filename": EXPECTED_MODEL["filename"],
    "model_size_bytes": EXPECTED_MODEL["size_bytes"],
    "model_sha256": EXPECTED_MODEL["sha256"],
    "model_quantization": EXPECTED_MODEL["quantization"],
    "core_prompt_sha256": PROMPT_HASHES["core"],
    "personality_prompt_sha256": PROMPT_HASHES["personality"],
    "prompt_sha256": PROMPT_HASHES["system"],
    "core_prompt_tokens": PROMPT_COUNTS["core"],
    "personality_prompt_tokens": PROMPT_COUNTS["personality"],
    "prompt_tokens": PROMPT_COUNTS["system"],
    "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
    "response_schema_sha256": RESPONSE_SCHEMA_SHA256,
    "max_user_tokens": 32,
    "max_output_tokens": 128,
    "engine_context_tokens": 1024,
    "temperature": 0.0,
    "top_p": 1.0,
    "threads": 4,
    "protocol": 3,
    "protocol_name": "snowboard.llm/3",
    "network": "disabled",
    "runtime_download": False,
    "network_fallback": False,
    "fallback_model": None,
    "system_site_packages": False,
    "prewarm": "none",
}
PROFILE_DYNAMIC_KEYS = {
    "profile_stage", "profile_sha256", "min_mem_available_generate_bytes",
    "min_mem_available_speak_bytes", "measurement_evidence_locator",
}
EXPECTED_RUNTIME_CLOSURE = {
    "manifest_locator": "requirements/m4b/llm-runtime-rpi-cp313.json",
    "manifest_sha256": "5cddddce70854116a36e292a1757d1e644f007a6798a8ce0d7455cb4806cd786",
}
EXPECTED_LICENSES = {
    "runtime_source_metadata": "https://github.com/google-ai-edge/LiteRT-LM/tree/924e79c91542761242244e4f1651851f822e4cbb",
    "model_source_metadata": "https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/tree/6b78abd019e61a1ca4cbe3b212d2c9ce8ff38a94",
    "runtime_spdx": "Apache-2.0",
    "model_spdx": "Apache-2.0",
    "notice_locator": "requirements/m4b/THIRD_PARTY_NOTICES.md",
    "notice_sha256": "0764aa43b64cd78b09dca8f5ae3ae3c79bb98893832c9666ad9404d64599b0ef",
}


class LLMLockError(ValueError):
    """The M4b product identity or installed closure is invalid."""


def _read_regular(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise LLMLockError("required file is missing, unreadable, or unsafe") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise LLMLockError("required path is not a regular file")
        blocks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            blocks.append(block)
        return b"".join(blocks)
    finally:
        os.close(descriptor)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise LLMLockError("required file is missing, unreadable, or unsafe") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise LLMLockError("required path is not a regular file")
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _exact(value: Any, expected: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != set(expected):
        raise LLMLockError(f"{label} has missing or extra fields")
    if any(type(value[key]) is not type(item) or value[key] != item
           for key, item in expected.items()):
        raise LLMLockError(f"{label} identity mismatch")
    return value


def _contains_absolute(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_absolute(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_absolute(item) for item in value)
    return isinstance(value, str) and value.startswith("/")


def profile_digest(value: Mapping[str, Any]) -> str:
    content = {key: item for key, item in value.items() if key != "profile_sha256"}
    try:
        raw = json.dumps(content, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError):
        raise LLMLockError("product profile is invalid") from None
    return hashlib.sha256(raw).hexdigest()


def validate_product_profile(value: object, *, allow_measurement: bool = False) -> Mapping[str, Any]:
    try:
        validate_prompt_identity()
    except ValueError:
        raise LLMLockError("prompt identity mismatch") from None
    if type(value) is not dict or set(value) != set(EXPECTED_PROFILE) | PROFILE_DYNAMIC_KEYS:
        raise LLMLockError("product profile has missing or extra fields")
    _exact({key: value[key] for key in EXPECTED_PROFILE}, EXPECTED_PROFILE, "product profile")
    if value["profile_sha256"] != profile_digest(value):
        raise LLMLockError("product profile checksum mismatch")
    stage = value["profile_stage"]
    generate = value["min_mem_available_generate_bytes"]
    speak = value["min_mem_available_speak_bytes"]
    locator = value["measurement_evidence_locator"]
    if stage == "measurement" and allow_measurement:
        if generate is not None or speak is not None or locator is not None:
            raise LLMLockError("measurement profile cannot set release thresholds")
    elif stage == "release":
        if type(generate) is not int or type(speak) is not int or not 0 < speak <= generate:
            raise LLMLockError("release profile memory thresholds are invalid")
        if (type(locator) is not str or not locator or locator.startswith("/") or
                ".." in PurePosixPath(locator).parts or "\x00" in locator):
            raise LLMLockError("release profile evidence locator is invalid")
    else:
        raise LLMLockError("product profile stage is not permitted")
    return dict(value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LLMLockError("duplicate JSON field")
        result[key] = value
    return result


def load_product_profile(path: Path, *, allow_measurement: bool = False) -> Mapping[str, Any]:
    try:
        value = json.loads(_read_regular(path), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LLMLockError("product profile is invalid JSON") from None
    return validate_product_profile(value, allow_measurement=allow_measurement)


@dataclass(frozen=True, slots=True)
class RuntimeFile:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeClosure:
    path: Path
    digest: str
    files: tuple[RuntimeFile, ...]

    @classmethod
    def load(cls, path: Path, *, expected_digest: str) -> "RuntimeClosure":
        raw_bytes = _read_regular(path)
        if hashlib.sha256(raw_bytes).hexdigest() != expected_digest:
            raise LLMLockError("runtime closure manifest checksum mismatch")
        try:
            raw = json.loads(raw_bytes, object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LLMLockError("runtime closure manifest is invalid JSON") from None
        if type(raw) is not dict or set(raw) != {
            "schema_version", "payload_scope", "platform", "python", "distribution",
            "source_wheel", "files",
        }:
            raise LLMLockError("runtime closure manifest has missing or extra fields")
        if (
            type(raw["schema_version"]) is not int or raw["schema_version"] != 1
            or raw["payload_scope"] != "product-owned-litert-lm"
            or raw["platform"] != "pi-debian13-aarch64"
        ):
            raise LLMLockError("runtime closure platform identity mismatch")
        if raw["python"] != {"implementation": "CPython", "version": "3.13.5",
                             "soabi": "cpython-313-aarch64-linux-gnu",
                             "multiarch": "aarch64-linux-gnu"}:
            raise LLMLockError("runtime closure Python identity mismatch")
        if raw["distribution"] != {"name": "litert-lm-api", "version": "0.16.0"}:
            raise LLMLockError("runtime closure distribution mismatch")
        if raw["source_wheel"] != {
            "filename": EXPECTED_RUNTIME["wheel_filename"],
            "size_bytes": EXPECTED_RUNTIME["wheel_size_bytes"],
            "sha256": EXPECTED_RUNTIME["wheel_sha256"],
        }:
            raise LLMLockError("runtime closure wheel identity mismatch")
        values = raw["files"]
        if type(values) is not list or not values:
            raise LLMLockError("runtime closure files must be a non-empty array")
        files: list[RuntimeFile] = []
        names: set[str] = set()
        for item in values:
            if type(item) is not dict or set(item) != {
                "relative_path", "size_bytes", "sha256",
            }:
                raise LLMLockError("runtime file entry has missing or extra fields")
            relative_path = item["relative_path"]
            if (
                type(relative_path) is not str
                or not relative_path
                or PurePosixPath(relative_path).is_absolute()
                or ".." in PurePosixPath(relative_path).parts
                or relative_path in names
            ):
                raise LLMLockError("runtime file relative path is invalid or duplicate")
            if type(item["size_bytes"]) is not int or item["size_bytes"] <= 0:
                raise LLMLockError("runtime file size is invalid")
            if type(item["sha256"]) is not str or not SHA256_RE.fullmatch(item["sha256"]):
                raise LLMLockError("runtime file digest is invalid")
            names.add(relative_path)
            files.append(RuntimeFile(**item))
        actual_files = {
            item.relative_path: (item.size_bytes, item.sha256) for item in files
        }
        if actual_files != EXPECTED_RUNTIME_FILES:
            raise LLMLockError("runtime product payload identity mismatch")
        return cls(path.resolve(), expected_digest, tuple(files))

    def verify_install(self, root: Path) -> None:
        if not root.is_dir() or root.is_symlink():
            raise LLMLockError("runtime install root is missing or unsafe")
        expected = {item.relative_path for item in self.files}
        actual = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        unsafe = [path for path in root.rglob("*") if path.is_symlink() or (not path.is_file() and not path.is_dir())]
        if unsafe or actual != expected:
            raise LLMLockError("runtime install has missing, extra, or unsafe entries")
        for item in self.files:
            path = root / item.relative_path
            if path.stat().st_size != item.size_bytes or _sha256(path) != item.sha256:
                raise LLMLockError("runtime installed file identity mismatch")


@dataclass(frozen=True, slots=True)
class LLMArtifactLock:
    path: Path
    digest: str
    identity: LLMReadyIdentity | None
    runtime: Mapping[str, Any]
    model: Mapping[str, Any]
    product_profile: Mapping[str, Any]
    runtime_closure: RuntimeClosure | None

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        repo_root: Path | None = None,
    ) -> "LLMArtifactLock":
        raw_bytes = _read_regular(path)
        try:
            raw = json.loads(raw_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LLMLockError("artifact lock is invalid JSON") from None
        if type(raw) is not dict or set(raw) != TOP_LEVEL_KEYS:
            raise LLMLockError("artifact lock has missing or extra top-level fields")
        if _contains_absolute(raw):
            raise LLMLockError("artifact lock contains an absolute deployment path")
        _exact(raw["lock"], EXPECTED_LOCK, "lock")
        _exact(raw["poc_reference"], EXPECTED_POC_REFERENCE, "poc_reference")
        candidate = _exact(raw["candidate"], EXPECTED_CANDIDATE, "candidate")
        runtime = _exact(raw["runtime"], EXPECTED_RUNTIME, "runtime")
        model = _exact(raw["model"], EXPECTED_MODEL, "model")
        profile = _exact(raw["product_profile"], EXPECTED_PROFILE, "product_profile")
        closure_value = _exact(
            raw["runtime_closure"], EXPECTED_RUNTIME_CLOSURE, "runtime_closure"
        )
        licenses = _exact(raw["licenses"], EXPECTED_LICENSES, "licenses")
        closure: RuntimeClosure | None = None
        if repo_root is not None:
            try:
                load_response_schema(repo_root=repo_root)
            except ResponseSchemaError:
                raise LLMLockError("deployed response schema identity mismatch") from None
            closure_path = repo_root / str(closure_value["manifest_locator"])
            closure = RuntimeClosure.load(
                closure_path,
                expected_digest=str(closure_value["manifest_sha256"]),
            )
            notice_path = repo_root / str(licenses["notice_locator"])
            if _sha256(notice_path) != licenses["notice_sha256"]:
                raise LLMLockError("third-party notice checksum mismatch")
        return cls(
            path.resolve(),
            hashlib.sha256(raw_bytes).hexdigest(),
            None,
            runtime,
            model,
            profile,
            closure,
        )

    def ready_identity(self, profile: Mapping[str, Any]) -> LLMReadyIdentity:
        from sbd.cognition.llm_child_protocol import LLMReadyIdentity
        validate_product_profile(dict(profile), allow_measurement=True)
        names = (
            "protocol_name", "candidate_id", "pairing_revision", "profile_id",
            "profile_stage", "profile_sha256", "runtime_sha256", "native_sha256",
            "model_sha256", "prompt_sha256", "response_schema_locator",
            "response_schema_sha256", "prompt_tokens",
            "max_output_tokens", "engine_context_tokens", "temperature", "top_p",
            "threads", "min_mem_available_generate_bytes", "min_mem_available_speak_bytes",
            "network",
        )
        return LLMReadyIdentity({**{name: profile[name] for name in names},
                                 "conversation_state": "none"})

    def verify_config_paths(self, config: Any, *, allow_measurement: bool = False) -> Mapping[str, Any]:
        if config.model_path.name != self.model["filename"]:
            raise LLMLockError("model filename mismatch")
        try:
            if config.model_path.stat().st_size != self.model["size_bytes"]:
                raise LLMLockError("model size mismatch")
        except OSError:
            raise LLMLockError("model file unavailable") from None
        if _sha256(config.model_path) != self.model["sha256"]:
            raise LLMLockError("model checksum mismatch")
        return load_product_profile(config.product_profile_path, allow_measurement=allow_measurement)


__all__ = [
    "LLMArtifactLock", "LLMLockError", "RuntimeClosure", "RuntimeFile",
    "load_product_profile", "validate_product_profile", "profile_digest",
]
