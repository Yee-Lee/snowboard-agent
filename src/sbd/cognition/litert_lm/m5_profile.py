"""M5.tool profile and bounded runtime facts; no startup content digest."""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from sbd.cognition.llm_child_protocol import LLMReadyIdentity
from sbd.cognition.litert_lm.lock import EXPECTED_CANDIDATE, EXPECTED_MODEL, EXPECTED_RUNTIME
from sbd.cognition.semantic import M5_RESPONSE_SCHEMA_LOCATOR


_FIXED = {
    "profile_id": "core-m5-tool-001",
    "protocol_name": "snowboard.llm/4",
    "response_schema_locator": M5_RESPONSE_SCHEMA_LOCATOR,
    "automatic_tool_calling": False,
    "enabled_intents": ["speak", "end", "tool", "look"],
    "tool_names": ["mock.send"],
    "external_message_enabled": False,
    "voice_wake_enabled": False,
    "max_output_tokens": 128,
    "engine_context_tokens": 1024,
    "temperature": 0.0,
    "top_p": 1.0,
    "threads": 4,
    "network": "disabled",
}
_DYNAMIC = {"profile_stage", "prompt_tokens", "min_mem_available_generate_bytes",
            "min_mem_available_speak_bytes"}


class M5ProfileError(ValueError):
    pass


def load_m5_profile(path: Path, *, allow_template: bool = False) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        if len(raw) > 4096:
            raise M5ProfileError("PROFILE_TOO_LARGE")
        def unique(pairs):
            output = {}
            for key, item in pairs:
                if key in output:
                    raise M5ProfileError("DUPLICATE_FIELD")
                output[key] = item
            return output
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
        if type(value) is not dict or set(value) != set(_FIXED) | _DYNAMIC:
            raise M5ProfileError("PROFILE_FIELDS")
        if any(type(value[key]) is not type(expected) or value[key] != expected
               for key, expected in _FIXED.items()):
            raise M5ProfileError("PROFILE_IDENTITY")
        if value["profile_stage"] == "template" and allow_template:
            if any(value[key] is not None for key in _DYNAMIC - {"profile_stage"}):
                raise M5ProfileError("TEMPLATE_VALUES")
        elif value["profile_stage"] == "release":
            count = value["prompt_tokens"]
            generate = value["min_mem_available_generate_bytes"]
            speak = value["min_mem_available_speak_bytes"]
            if (type(count) is not int or count < 1 or count > 1024 or
                    type(generate) is not int or type(speak) is not int or
                    not 0 < speak <= generate):
                raise M5ProfileError("RELEASE_VALUES")
        else:
            raise M5ProfileError("PROFILE_STAGE")
        return value
    except (OSError, UnicodeError, ValueError, TypeError):
        raise M5ProfileError("INVALID_M5_PROFILE") from None


@dataclass(frozen=True, slots=True)
class M5RuntimeFacts:
    product_profile: Mapping[str, Any]
    runtime: Mapping[str, Any]
    model: Mapping[str, Any]
    identity: LLMReadyIdentity
    digest: str = ""

    @classmethod
    def load(cls, profile_path: Path) -> "M5RuntimeFacts":
        profile = load_m5_profile(profile_path)
        identity = LLMReadyIdentity({
            "protocol_name": "snowboard.llm/4",
            "candidate_id": EXPECTED_CANDIDATE["candidate_id"],
            "pairing_revision": EXPECTED_CANDIDATE["pairing_revision"],
            "profile_id": "core-m5-tool-001",
            "profile_stage": "release",
            "response_schema_locator": M5_RESPONSE_SCHEMA_LOCATOR,
            "prompt_tokens": profile["prompt_tokens"],
            "max_output_tokens": 128, "engine_context_tokens": 1024,
            "temperature": 0.0, "top_p": 1.0, "threads": 4,
            "min_mem_available_generate_bytes": profile["min_mem_available_generate_bytes"],
            "min_mem_available_speak_bytes": profile["min_mem_available_speak_bytes"],
            "conversation_state": "none", "network": "disabled",
        })
        return cls(profile, EXPECTED_RUNTIME, EXPECTED_MODEL, identity)

    def validate_runtime_paths(self, cfg: Any) -> None:
        path = cfg.model_path
        if not isinstance(path, Path) or path.name != self.model["filename"]:
            raise M5ProfileError("MODEL_PATH")
        try:
            metadata = path.lstat()
        except OSError:
            raise M5ProfileError("MODEL_PATH") from None
        if (not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or
                metadata.st_size != self.model["size_bytes"]):
            raise M5ProfileError("MODEL_SHAPE")
