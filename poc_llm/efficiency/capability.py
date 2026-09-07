"""Reproducible static inventory for the frozen LiteRT-LM 0.16 wheel."""

from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZipFile


class CapabilityError(ValueError):
    pass


def _has(source: str, snippet: str, label: str) -> bool:
    if snippet not in source:
        raise CapabilityError(f"frozen wheel lacks required {label}")
    return True


def inspect_frozen_wheel(path: Path, *, expected_sha256: str) -> dict[str, object]:
    """Inspect exact packaged source without importing native code or exposing paths."""

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise CapabilityError("runtime wheel digest mismatch")
    with ZipFile(path) as wheel:
        names = set(wheel.namelist())
        required = {"litert_lm/interfaces.py", "litert_lm/conversation.py", "litert_lm/_ffi.py"}
        if not required.issubset(names):
            raise CapabilityError("runtime wheel source inventory is incomplete")
        interfaces = wheel.read("litert_lm/interfaces.py").decode("utf-8")
        conversation = wheel.read("litert_lm/conversation.py").decode("utf-8")
        ffi = wheel.read("litert_lm/_ffi.py").decode("utf-8")
        metadata_names = sorted(name for name in names if name.endswith(".dist-info/METADATA"))
        if len(metadata_names) != 1:
            raise CapabilityError("runtime wheel metadata is ambiguous")
        metadata = wheel.read(metadata_names[0]).decode("utf-8")
    version_lines = [line.removeprefix("Version: ") for line in metadata.splitlines()
                     if line.startswith("Version: ")]
    if version_lines != ["0.16.0"]:
        raise CapabilityError("runtime wheel version mismatch")
    return {
        "inventory_format": "m4b-mva-efficiency-capability-v1",
        "runtime_version": "0.16.0",
        "wheel_sha256": digest,
        "python_public_api": {
            "response_format_regex": _has(interfaces, "def regex(cls, pattern: str)", "regex factory"),
            "regex_type_value": 1 if _has(interfaces, "REGEX = 1", "regex type") else None,
            "json_schema_type_value": 2 if _has(interfaces, "JSON_OBJECT = 2", "JSON type") else None,
            "llguidance_required": _has(
                conversation,
                "!= LiteRtLmConstraintProviderType.LL_GUIDANCE",
                "LLGuidance response-format gate",
            ),
        },
        "frozen_c_ffi": {
            "regex_constraint_value": 1 if _has(ffi, "REGEX = 1", "FFI regex type") else None,
            "json_schema_constraint_value": 2 if _has(ffi, "JSON_SCHEMA = 2", "FFI JSON type") else None,
            "raw_stream_final_flag": _has(ffi, "litert_lm_stream_chunk_is_final", "stream final flag"),
            "raw_stream_error": _has(ffi, "litert_lm_stream_chunk_get_error", "stream error accessor"),
        },
        "wrapper_limitation": {
            "collapses_cancel_and_token_limit_to_iterator_end": (
                _has(conversation, '"CANCELLED" in err_msg', "cancel branch")
                and _has(conversation, '"Max number of tokens reached" in err_msg', "token-limit branch")
                and _has(conversation, "break", "iterator termination")
            ),
            "requires_raw_terminal_adapter_for_normal_termination_proof": True,
        },
    }
