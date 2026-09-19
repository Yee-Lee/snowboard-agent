"""Frozen M4B S2 parsing over the LiteRT raw stream.

The accepted normalization may revise earlier Unicode code points.  Therefore
the safe parser deliberately waits until the complete JSON object is valid,
then releases normalized speech before the native final marker when the raw
runtime makes that interval observable.  It never substitutes the efficiency
experiment's prefix encoding or publishes a terminal Fact.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from typing import Callable, Iterable

from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError


class S2Error(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class S2Terminal:
    text: str
    end: bool
    text_sha256: str
    normalized_codepoints: int


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise S2Error("INVALID_SEMANTIC")
        value[key] = item
    return value


def normalize_text(value: object) -> str:
    if type(value) is not str:
        raise S2Error("INVALID_SEMANTIC")
    text = unicodedata.normalize("NFKC", value)
    if any(
        unicodedata.category(char) == "Cs"
        or (unicodedata.category(char) == "Cc" and char not in "\t\n\r")
        for char in text
    ):
        raise S2Error("INVALID_SEMANTIC")
    return " ".join(text.split())


def validate_semantic(raw: str) -> S2Terminal:
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
        if (
            type(value) is not dict
            or set(value) != {"text", "end"}
            or type(value["text"]) is not str
            or type(value["end"]) is not bool
            or len(value["text"]) > 4096
        ):
            raise S2Error("INVALID_SEMANTIC")
        text = normalize_text(value["text"])
        spoken = sum(
            not char.isspace() and not unicodedata.category(char).startswith("P")
            for char in text
        )
        if (not text and not value["end"]) or spoken > 30:
            raise S2Error("INVALID_SEMANTIC")
        encoded = text.encode("utf-8")
        return S2Terminal(
            text=text,
            end=value["end"],
            text_sha256=hashlib.sha256(encoded).hexdigest(),
            normalized_codepoints=len(text),
        )
    except (json.JSONDecodeError, UnicodeError, TypeError, ValueError, KeyError, RecursionError):
        raise S2Error("INVALID_SEMANTIC") from None


def consume_raw_s2(
    chunks: Iterable[RawStreamChunk],
    *,
    on_safe_text: Callable[[str], None],
) -> S2Terminal:
    """Release at most one normalized S2 fragment and require a native final."""

    wire = ""
    released = ""
    terminal: S2Terminal | None = None
    final_seen = False
    try:
        for chunk in chunks:
            if final_seen:
                raise S2Error("PROTOCOL_ERROR")
            if chunk.is_final:
                if chunk.text:
                    raise S2Error("PROTOCOL_ERROR")
                final_seen = True
                continue
            if type(chunk.text) is not str:
                raise S2Error("PROTOCOL_ERROR")
            wire += chunk.text
            if len(wire) > 65536:
                raise S2Error("WIRE_LIMIT")
            if terminal is None:
                try:
                    candidate = validate_semantic(wire)
                except S2Error:
                    continue
                terminal = candidate
                released = candidate.text
                if released:
                    on_safe_text(released)
        if not final_seen:
            raise S2Error("MISSING_TERMINAL")
        verified = validate_semantic(wire)
        if terminal is None:
            terminal = verified
            released = verified.text
            if released:
                on_safe_text(released)
        if verified != terminal or not verified.text.startswith(released):
            raise S2Error("TERMINAL_PREFIX_MISMATCH")
        return verified
    except RawStreamError as error:
        raise S2Error(error.code) from error
    except Exception:
        # An empty callback is the private rollback/cancel signal used by the
        # raw source adapter.  It is never admitted as a fragment.
        if released:
            on_safe_text("")
        raise
