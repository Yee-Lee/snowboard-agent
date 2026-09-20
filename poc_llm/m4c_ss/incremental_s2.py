"""Incremental extraction of non-revisable speech prefixes from compact JSON."""

from __future__ import annotations

import re
import unicodedata

from poc_llm.m4c_ss.s2 import S2Error, normalize_text


_PREFIX = re.compile(r'^\s*\{\s*"text"\s*:\s*')
_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _decode_partial_string(value: str, start: int) -> tuple[str, bool]:
    if start >= len(value) or value[start] != '"':
        raise S2Error("INVALID_SEMANTIC")
    result: list[str] = []
    index = start + 1
    while index < len(value):
        char = value[index]
        if char == '"':
            return "".join(result), True
        if ord(char) < 0x20:
            raise S2Error("INVALID_SEMANTIC")
        if char != "\\":
            result.append(char)
            index += 1
            continue
        if index + 1 >= len(value):
            break
        escape = value[index + 1]
        if escape in _SIMPLE_ESCAPES:
            result.append(_SIMPLE_ESCAPES[escape])
            index += 2
            continue
        if escape != "u":
            raise S2Error("INVALID_SEMANTIC")
        if index + 6 > len(value):
            break
        digits = value[index + 2:index + 6]
        try:
            codepoint = int(digits, 16)
        except ValueError:
            raise S2Error("INVALID_SEMANTIC") from None
        index += 6
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 6 > len(value):
                break
            if value[index:index + 2] != "\\u":
                raise S2Error("INVALID_SEMANTIC")
            try:
                low = int(value[index + 2:index + 6], 16)
            except ValueError:
                raise S2Error("INVALID_SEMANTIC") from None
            if not 0xDC00 <= low <= 0xDFFF:
                raise S2Error("INVALID_SEMANTIC")
            result.append(chr(0x10000 + ((codepoint - 0xD800) << 10) + low - 0xDC00))
            index += 6
        elif 0xDC00 <= codepoint <= 0xDFFF:
            raise S2Error("INVALID_SEMANTIC")
        else:
            result.append(chr(codepoint))
    return "".join(result), False


def partial_text_value(wire: str) -> tuple[str, bool] | None:
    """Return the complete decodable prefix of a first-field text string."""

    match = _PREFIX.match(wire)
    if match is None:
        if len(wire) < 12:
            return None
        raise S2Error("UNSUPPORTED_FIELD_ORDER")
    return _decode_partial_string(wire, match.end())


def stable_normalized_prefix(decoded: str, *, text_closed: bool) -> str:
    """Hold the last normalization segment until a later starter proves it stable."""

    if text_closed:
        return normalize_text(decoded)
    last_starter = None
    for index, char in enumerate(decoded):
        decomposition = unicodedata.normalize("NFKD", char)
        if decomposition and unicodedata.combining(decomposition[0]) == 0:
            last_starter = index
    if last_starter is None:
        return ""
    return normalize_text(decoded[:last_starter])


class IncrementalS2:
    def __init__(self, *, max_codepoints: int = 24) -> None:
        if type(max_codepoints) is not int or not 1 <= max_codepoints <= 256:
            raise ValueError("INVALID_RELEASE_BOUNDARY")
        self.max_codepoints = max_codepoints
        self.released = ""

    def feed(self, wire: str) -> list[str]:
        partial = partial_text_value(wire)
        if partial is None:
            return []
        decoded, closed = partial
        stable = stable_normalized_prefix(decoded, text_closed=closed)
        if not stable.startswith(self.released):
            raise S2Error("TERMINAL_PREFIX_MISMATCH")
        fragments: list[str] = []
        while True:
            pending = stable[len(self.released):]
            boundary = self._boundary(pending, self.max_codepoints)
            if boundary is None:
                break
            fragment = pending[:boundary]
            if not fragment:
                break
            self.released += fragment
            fragments.append(fragment)
        return fragments

    def flush(self, terminal_text: str) -> list[str]:
        if not terminal_text.startswith(self.released):
            raise S2Error("TERMINAL_PREFIX_MISMATCH")
        remainder = terminal_text[len(self.released):]
        if not remainder:
            return []
        self.released = terminal_text
        return [remainder]

    @staticmethod
    def _boundary(pending: str, max_codepoints: int) -> int | None:
        boundaries = [
            index + 1
            for index, char in enumerate(pending)
            if unicodedata.category(char).startswith("P")
        ]
        if len(pending) >= max_codepoints:
            boundaries.append(max_codepoints)
        return min(boundaries) if boundaries else None
