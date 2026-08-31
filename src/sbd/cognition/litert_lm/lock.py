"""Strict M4b lock and isolated-runtime closure verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from sbd.cognition.llm_child_protocol import LLMReadyIdentity


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TOP_LEVEL_KEYS = {
    "lock", "poc_reference", "candidate", "runtime", "model",
    "product_profile", "runtime_closure", "licenses",
}

EXPECTED_LOCK = {"schema_version": 1, "protocol_version": "snowboard.llm/1"}
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
    "config_locator": "poc_llm/config/litert-lm-v0.16.0-pi-g2b-r5.json",
    "config_sha256": "c4557b018733ce8a2f4aa46b375cc7dafb31fbd8c363271deb1156c651e5171e",
    "config_schema_locator": "poc_llm/contracts/m1/strict-config-pi-gate2b-product-v2.schema.json",
    "config_schema_sha256": "ce8fa478a1b167042714cb579bb950cf87f7bdb0f80af73fe3a023e16ad77c34",
    "prompt_schema_locator": "poc_llm/contracts/m1/prompt-input.schema.json",
    "prompt_schema_sha256": "aca834bb448f88dfb403c74c427b5462922ccf23f4f26c1944c47d5731522de6",
    "response_schema_locator": "poc_llm/contracts/m1/response.schema.json",
    "response_schema_sha256": "4be45ee60f603d7349ff5fb29b667d6e59970dd0be3ce9176c03e923e0a6fca2",
    "protocol_schema_locator": "poc_llm/contracts/m1/protocol-frame-pi.schema.json",
    "protocol_schema_sha256": "e1af3bc5f83f1456d393d30acd9bcf9b9a8a7f91cbdcbe7aa0136a17c275301e",
    "prewarm_prompt_sha256": "4f3bc3e09b3b1693812c749765cfce5899dc11933de06623dbfc82a61a50472d",
    "max_input_tokens": 128,
    "max_output_tokens": 128,
    "max_kv_tokens": 1024,
    "temperature": 0.0,
    "top_p": 1.0,
    "threads": 4,
    "generation_timeout_seconds": 15.0,
    "terminal_grace_seconds": 2.0,
    "cancel_timeout_seconds": 0.5,
    "terminate_timeout_seconds": 2.0,
    "kill_wait_timeout_seconds": 1.0,
    "rebuild_ready_timeout_seconds": 10.0,
    "offline": True,
    "runtime_download": False,
    "network_fallback": False,
    "fallback_model": None,
}
EXPECTED_PRODUCT_CONFIG = {
    "candidate_id": EXPECTED_CANDIDATE["candidate_id"],
    "pairing_revision": EXPECTED_CANDIDATE["pairing_revision"],
    "platform": EXPECTED_CANDIDATE["platform"],
    "protocol_version": EXPECTED_LOCK["protocol_version"],
    "driver": "litert_lm",
    "runtime_sha256": EXPECTED_RUNTIME["wheel_sha256"],
    "model_sha256": EXPECTED_MODEL["sha256"],
    "test_profile": "gate2b-structured-product-v5-controller-r2",
    "max_input_tokens": 128,
    "max_output_tokens": 128,
    "engine_max_num_tokens": 1024,
    "temperature": 0.0,
    "top_p": 1.0,
    "threads": 4,
    "ready_timeout_ms": 45000,
    "generate_timeout_ms": 15000,
    "terminal_grace_ms": 2000,
    "cancel_timeout_ms": 500,
    "term_timeout_ms": 2000,
    "kill_timeout_ms": 1000,
    "rebuild_timeout_ms": 10000,
    "runtime_download": False,
    "network_fallback": False,
    "fallback_model": None,
}
EXPECTED_RUNTIME_CLOSURE = {
    "manifest_locator": "requirements/m4b/llm-runtime-rpi-cp313.json",
    "manifest_sha256": "6c11b8357021fb3bd7abaddeb8fdfdabc1b0fa85cd22bd49fcd7d9cd7d0871d2",
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
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise LLMLockError("required file is missing, unreadable, or unsafe") from error
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
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise LLMLockError("required file is missing, unreadable, or unsafe") from error
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
    if value != dict(expected):
        raise LLMLockError(f"{label} identity mismatch")
    return value


def _contains_absolute(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_absolute(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_absolute(item) for item in value)
    return isinstance(value, str) and value.startswith("/")


def validate_product_config(value: object) -> Mapping[str, Any]:
    required = set(EXPECTED_PRODUCT_CONFIG) | {"runtime_path", "model_path"}
    if type(value) is not dict or set(value) != required:
        raise LLMLockError("product config has missing or extra fields")
    for key, expected in EXPECTED_PRODUCT_CONFIG.items():
        if value[key] != expected or type(value[key]) is not type(expected):
            raise LLMLockError("product config identity mismatch")
    for key in ("runtime_path", "model_path"):
        path = value[key]
        if (
            type(path) is not str
            or "\x00" in path
            or not PurePosixPath(path).is_absolute()
        ):
            raise LLMLockError("product config provenance path is invalid")
    return value


def load_product_config(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(_read_regular(path))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LLMLockError("product config is invalid JSON") from error
    return validate_product_config(value)


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
            raw = json.loads(raw_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LLMLockError("runtime closure manifest is invalid JSON") from error
        if type(raw) is not dict or set(raw) != {
            "schema_version", "payload_scope", "platform", "python", "distribution",
            "source_wheel", "files",
        }:
            raise LLMLockError("runtime closure manifest has missing or extra fields")
        if (
            raw["schema_version"] != 1
            or raw["payload_scope"] != "product-owned-litert-lm"
            or raw["platform"] != "pi-debian13-aarch64"
        ):
            raise LLMLockError("runtime closure platform identity mismatch")
        if raw["python"] != {"implementation": "CPython", "version": "3.13.5"}:
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
    identity: LLMReadyIdentity
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
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LLMLockError("artifact lock is invalid JSON") from error
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
            LLMReadyIdentity(
                candidate_id=str(candidate["candidate_id"]),
                pairing_revision=str(candidate["pairing_revision"]),
                platform=str(candidate["platform"]),
                runtime_sha256=str(runtime["wheel_sha256"]),
                model_sha256=str(model["sha256"]),
                config_sha256=str(profile["config_sha256"]),
            ),
            runtime,
            model,
            profile,
            closure,
        )

    def verify_config_paths(self, config: Any) -> None:
        if config.model_path.name != self.model["filename"]:
            raise LLMLockError("model filename mismatch")
        if config.model_path.stat().st_size != self.model["size_bytes"]:
            raise LLMLockError("model size mismatch")
        if _sha256(config.model_path) != self.model["sha256"]:
            raise LLMLockError("model checksum mismatch")
        if _sha256(config.product_config_path) != self.product_profile["config_sha256"]:
            raise LLMLockError("product config checksum mismatch")
        load_product_config(config.product_config_path)


__all__ = [
    "LLMArtifactLock",
    "LLMLockError",
    "RuntimeClosure",
    "RuntimeFile",
    "load_product_config",
    "validate_product_config",
]
