"""Frozen M4B semantics; private content never appears in diagnostic errors."""

from __future__ import annotations

import codecs
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass


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


# The grammar fixes structural bytes, while json.loads validates escape/surrogate
# decoding. Neither a dict nor re-serialization can prove the original wire bytes.
_WIRE = re.compile(r'\{"text":("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"),"end":(true|false)\}', re.DOTALL)
GRAMMAR_BYTES = (
    'root ::= "{\\"text\\":" string ",\\"end\\":" ("true" | "false") "}"\n'
    'string ::= "\\"" char* "\\""\n'
    'char ::= [^"\\\\\\x00-\\x1F] | "\\\\" (["\\\\/bfnrt] | "u" hex hex hex hex)\n'
    'hex ::= [0-9a-fA-F]\n'
).encode("utf-8")
GRAMMAR_SHA256 = hashlib.sha256(GRAMMAR_BYTES).hexdigest()


def validate_semantic(raw: bytes | str | dict[str, object]) -> SemanticOutput:
    try:
        if type(raw) is bytes:
            raw = raw.decode("utf-8", errors="strict")
        if type(raw) is str:
            if _WIRE.fullmatch(raw) is None:
                raise SemanticError()
            value = json.loads(raw)
        elif type(raw) is dict:
            value = raw
        else:
            raise SemanticError()
        if list(value) != ["text", "end"] or type(value["end"]) is not bool:
            raise SemanticError()
        text = normalize_text(value["text"])
        if (not text and not value["end"]) or spoken_length(text) > 30:
            raise SemanticError()
        return SemanticOutput(text, value["end"])
    except (ValueError, UnicodeError, TypeError, KeyError):
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
        prefix = '{"text":'
        if not (prefix.startswith(self._buffer) or self._buffer.startswith(prefix)):
            self._fail()
        if self._emitted or len(self._buffer) <= len(prefix):
            return ()
        encoded = self._buffer[len(prefix):]
        if not encoded.startswith('"'):
            self._fail()
        # Locate a genuine closing quote, skipping escaped bytes.
        escaped = False
        for index, char in enumerate(encoded[1:], 1):
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                try:
                    text = normalize_text(json.loads(encoded[:index + 1]))
                    if spoken_length(text) > 30:
                        self._fail()
                except (ValueError, UnicodeError):
                    self._fail()
                self._prefix = text
                self._emitted = True
                return (text,) if text else ()
        return ()

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
