"""Frozen M4B semantics; private content never appears in diagnostic errors."""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import stat
import unicodedata
import re
from dataclasses import dataclass
from pathlib import Path


class SemanticError(ValueError):
    def __init__(self) -> None:
        super().__init__("INVALID_SEMANTIC")


def normalize_text(value: object) -> str:
    if type(value) is not str:
        raise SemanticError()
    text = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(c) == "Cs" or
           (unicodedata.category(c) == "Cc" and c not in "\t\n\r") for c in text):
        raise SemanticError()
    return " ".join(text.split())


def spoken_length(text: str) -> int:
    return sum(not c.isspace() and not unicodedata.category(c).startswith("P") for c in text)


@dataclass(frozen=True, slots=True)
class SemanticOutput:
    text: str
    end: bool


RESPONSE_SCHEMA_LOCATOR = "requirements/m4b/semantic-output-v1.schema.json"
RESPONSE_SCHEMA_SHA256 = "796c31148ea812fc63656313d0afd5d086a5ea907d257af8f214104a69215de9"
RESPONSE_SCHEMA_SIZE_BYTES = 352


class ResponseSchemaError(ValueError):
    def __init__(self) -> None:
        super().__init__("RESPONSE_SCHEMA_IDENTITY_MISMATCH")


def load_response_schema(*, repo_root: Path | None = None) -> dict[str, object]:
    """Authenticate deployed POC bytes, then return that file's decoded mapping."""
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[3]
    path = root / RESPONSE_SCHEMA_LOCATOR
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                             | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ResponseSchemaError()
        raw = b""
        while block := os.read(descriptor, 4096):
            raw += block
            if len(raw) > RESPONSE_SCHEMA_SIZE_BYTES:
                raise ResponseSchemaError()
        if (len(raw) != RESPONSE_SCHEMA_SIZE_BYTES or raw.startswith(b"\xef\xbb\xbf")
                or not raw.endswith(b"\n")
                or hashlib.sha256(raw).hexdigest() != RESPONSE_SCHEMA_SHA256):
            raise ResponseSchemaError()
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=_unique_json_object)
        if type(value) is not dict:
            raise ResponseSchemaError()
        return value
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        raise ResponseSchemaError() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise SemanticError()
        value[key] = item
    return value


def validate_semantic(raw: bytes | str | dict[str, object]) -> SemanticOutput:
    try:
        if type(raw) is bytes:
            raw = raw.decode("utf-8", errors="strict")
        if type(raw) is str:
            value = json.loads(raw, object_pairs_hook=_unique_json_object,
                               parse_constant=lambda _value: (_ for _ in ()).throw(SemanticError()))
        elif type(raw) is dict:
            value = raw
        else:
            raise SemanticError()
        if (type(value) is not dict or set(value) != {"text", "end"}
                or type(value["text"]) is not str or len(value["text"]) > 4096
                or type(value["end"]) is not bool):
            raise SemanticError()
        text = normalize_text(value["text"])
        if (not text and not value["end"]) or spoken_length(text) > 30:
            raise SemanticError()
        return SemanticOutput(text, value["end"])
    except (ValueError, UnicodeError, TypeError, KeyError, RecursionError):
        raise SemanticError() from None


class IncrementalSemanticParser:
    """Strict incremental UTF-8 decoder with irrevocable normalized fragments.

    NFKC may revise an earlier code point when a combining character arrives.
    Therefore this implementation waits for the closing text quote. It emits
    the normalized text once its complete string is known, withholding every
    structural byte; finish proves the terminal grammar and prefix relation.
    """

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self._buffer = ""
        self._prefix = ""
        self._emitted = False
        self._terminal = False
        self._failed = False

    def _fail(self) -> None:
        self._failed = True
        self._buffer = self._prefix = ""
        self._decoder.reset()
        raise SemanticError()

    def feed(self, chunk: bytes) -> tuple[str, ...]:
        if self._terminal or self._failed or type(chunk) is not bytes:
            self._fail()
        try:
            self._buffer += self._decoder.decode(chunk, final=False)
        except UnicodeError:
            self._fail()
        if len(self._buffer) > 65536:
            self._fail()
        if self._emitted:
            return ()
        try:
            result = validate_semantic(self._buffer)
        except SemanticError:
            return ()
        self._prefix = result.text
        self._emitted = True
        return (result.text,) if result.text else ()

    def finish(self) -> SemanticOutput:
        if self._terminal or self._failed:
            self._fail()
        try:
            self._buffer += self._decoder.decode(b"", final=True)
            result = validate_semantic(self._buffer)
            if not result.text.startswith(self._prefix):
                self._fail()
        except (ValueError, UnicodeError):
            self._fail()
        self._terminal = True
        self._buffer = self._prefix = ""
        self._decoder.reset()
        return result


_TEXT_PREFIX = re.compile(r'^\s*\{\s*"text"\s*:\s*')
_SIMPLE_ESCAPES = {
    '"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
    "n": "\n", "r": "\r", "t": "\t",
}


def _partial_json_text(value: str, start: int) -> tuple[str, bool]:
    if start >= len(value) or value[start] != '"':
        raise SemanticError()
    result: list[str] = []
    index = start + 1
    while index < len(value):
        char = value[index]
        if char == '"':
            return "".join(result), True
        if ord(char) < 0x20:
            raise SemanticError()
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
        if escape != "u" or index + 6 > len(value):
            if escape != "u":
                raise SemanticError()
            break
        try:
            codepoint = int(value[index + 2:index + 6], 16)
        except ValueError:
            raise SemanticError() from None
        index += 6
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 6 > len(value):
                break
            if value[index:index + 2] != "\\u":
                raise SemanticError()
            try:
                low = int(value[index + 2:index + 6], 16)
            except ValueError:
                raise SemanticError() from None
            if not 0xDC00 <= low <= 0xDFFF:
                raise SemanticError()
            result.append(chr(0x10000 + ((codepoint - 0xD800) << 10) + low - 0xDC00))
            index += 6
        elif 0xDC00 <= codepoint <= 0xDFFF:
            raise SemanticError()
        else:
            result.append(chr(codepoint))
    return "".join(result), False


class IncrementalSafeTextParser:
    """M4C punctuation-or-12 extraction with irrevocable normalization."""

    def __init__(self, boundary_codepoints: int = 12) -> None:
        if type(boundary_codepoints) is not int or not 1 <= boundary_codepoints <= 256:
            raise ValueError("INVALID_RELEASE_BOUNDARY")
        self._decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self._buffer = ""
        self._released = ""
        self._boundary_codepoints = boundary_codepoints
        self._terminal = False
        self._failed = False

    @property
    def released(self) -> str:
        return self._released

    def _fail(self) -> None:
        self._failed = True
        self._buffer = self._released = ""
        self._decoder.reset()
        raise SemanticError()

    def feed(self, chunk: bytes) -> tuple[str, ...]:
        if self._terminal or self._failed or type(chunk) is not bytes:
            self._fail()
        try:
            self._buffer += self._decoder.decode(chunk, final=False)
            if len(self._buffer) > 65536:
                self._fail()
            match = _TEXT_PREFIX.match(self._buffer)
            if match is None:
                if len(self._buffer) < 12:
                    return ()
                self._fail()
            decoded, closed = _partial_json_text(self._buffer, match.end())
            stable = self._stable_prefix(decoded, closed)
            if not stable.startswith(self._released):
                self._fail()
            fragments: list[str] = []
            while True:
                pending = stable[len(self._released):]
                boundary = self._boundary(pending)
                if boundary is None:
                    break
                fragment = pending[:boundary]
                if not fragment:
                    break
                self._released += fragment
                fragments.append(fragment)
            return tuple(fragments)
        except (UnicodeError, ValueError):
            self._fail()

    def finish(self) -> tuple[SemanticOutput, tuple[str, ...]]:
        if self._terminal or self._failed:
            self._fail()
        try:
            self._buffer += self._decoder.decode(b"", final=True)
            terminal = validate_semantic(self._buffer)
            if not terminal.text.startswith(self._released):
                self._fail()
            remainder = terminal.text[len(self._released):]
            self._released = terminal.text
        except (UnicodeError, ValueError):
            self._fail()
        self._terminal = True
        return terminal, ((remainder,) if remainder else ())

    @staticmethod
    def _stable_prefix(decoded: str, closed: bool) -> str:
        if closed:
            return normalize_text(decoded)
        last_starter = None
        for index, char in enumerate(decoded):
            decomposition = unicodedata.normalize("NFKD", char)
            if decomposition and unicodedata.combining(decomposition[0]) == 0:
                last_starter = index
        if last_starter is None:
            return ""
        return normalize_text(decoded[:last_starter])

    def _boundary(self, pending: str) -> int | None:
        candidates = [
            index + 1 for index, char in enumerate(pending)
            if unicodedata.category(char).startswith("P")
        ]
        if len(pending) >= self._boundary_codepoints:
            candidates.append(self._boundary_codepoints)
        return min(candidates) if candidates else None
