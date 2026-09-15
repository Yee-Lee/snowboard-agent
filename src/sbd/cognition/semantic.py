"""Frozen M4B semantics; private content never appears in diagnostic errors."""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import stat
import unicodedata
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
