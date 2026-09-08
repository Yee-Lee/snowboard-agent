"""Pure contracts for the M4B-MVA encoding efficiency experiment.

The decoders deliberately separate provisional text from a successful terminal.
Callers may use provisional text for future streaming, but must cancel downstream
work if ``finish`` or ``cancel`` raises :class:`EfficiencyContractError`.
"""

from __future__ import annotations

import codecs
import json
from typing import Iterable

from poc_llm.harness.mva_contract import ContractViolation, validate_semantic


P_RESPONSE_REGEX = r"(?:E|S\n\s*[^\s][\s\S]*)"
P_MAX_TEXT_CODEPOINTS = 4096
MAX_WIRE_CODEPOINTS = 16384


def validate_efficiency_semantic(value: object) -> dict[str, object]:
    """Allow optional final speech; reject only blank non-final output."""

    if not isinstance(value, dict) or set(value) != {"text", "end"}:
        raise ContractViolation("semantic output must contain exact text/end keys")
    output_text = value["text"]
    end = value["end"]
    if not isinstance(output_text, str) or not isinstance(end, bool):
        raise ContractViolation("semantic text/end types are invalid")
    if len(output_text) > P_MAX_TEXT_CODEPOINTS:
        raise ContractViolation("semantic text exceeds wire limit")
    if not end and not output_text.strip():
        raise ContractViolation("end=false requires nonblank text")
    return {"text": output_text, "end": end}


class EfficiencyContractError(ContractViolation):
    """A stream can no longer produce an eligible successful result."""


class _Utf8Stream:
    def __init__(self, *, maximum_wire_codepoints: int = MAX_WIRE_CODEPOINTS) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self._input_kind: type[bytes] | type[str] | None = None
        self._wire_codepoints = 0
        self._maximum_wire_codepoints = maximum_wire_codepoints

    def decode(self, chunk: bytes | str, *, final: bool = False) -> str:
        if not isinstance(chunk, (bytes, str)):
            raise EfficiencyContractError("stream chunk must be bytes or text")
        kind = bytes if isinstance(chunk, bytes) else str
        if self._input_kind is not None and kind is not self._input_kind:
            raise EfficiencyContractError("stream chunk type changed")
        self._input_kind = kind
        try:
            if isinstance(chunk, bytes):
                text = self._decoder.decode(chunk, final=final)
            else:
                chunk.encode("utf-8", "strict")
                text = chunk
                if final:
                    text += self._decoder.decode(b"", final=True)
        except UnicodeError as error:
            raise EfficiencyContractError("invalid UTF-8 output") from error
        self._wire_codepoints += len(text)
        if self._wire_codepoints > self._maximum_wire_codepoints:
            raise EfficiencyContractError("wire output exceeds limit")
        return text

    def close(self) -> str:
        if self._input_kind is bytes:
            return self.decode(b"", final=True)
        if self._input_kind is str:
            return self.decode("", final=True)
        return self.decode(b"", final=True)


class PrefixStreamDecoder:
    """Decode exact P output: ``S\n<body>`` or exact ``E``.

    Returned fragments are provisional. A semantic result exists only after
    :meth:`finish` succeeds at normal runtime termination.
    """

    def __init__(self, *, maximum_text_codepoints: int = P_MAX_TEXT_CODEPOINTS) -> None:
        self._utf8 = _Utf8Stream()
        self._maximum_text_codepoints = maximum_text_codepoints
        self._prefix = ""
        self._mode: str | None = None
        self._body: list[str] = []
        self._body_length = 0
        self._failed = False
        self._finished = False

    @property
    def released_text(self) -> str:
        return "".join(self._body)

    def _fail(self, message: str) -> None:
        self._failed = True
        raise EfficiencyContractError(message)

    def feed(self, chunk: bytes | str) -> list[str]:
        if self._failed or self._finished:
            self._fail("stream is no longer active")
        try:
            text = self._utf8.decode(chunk)
            return self._consume(text)
        except EfficiencyContractError:
            self._failed = True
            raise

    def _consume(self, text: str) -> list[str]:
        if not text:
            return []
        if self._mode == "end":
            self._fail("E must not have trailing output")
        if self._mode == "speech":
            return self._append_body(text)

        self._prefix += text
        if self._prefix == "E":
            self._mode = "end"
            self._prefix = ""
            return []
        if "S\n".startswith(self._prefix):
            return []
        if self._prefix.startswith("S\n"):
            body = self._prefix[2:]
            self._prefix = ""
            self._mode = "speech"
            return self._append_body(body)
        self._fail("unknown P output prefix")

    def _append_body(self, text: str) -> list[str]:
        if not text:
            return []
        self._body_length += len(text)
        if self._body_length > self._maximum_text_codepoints:
            self._fail("P text exceeds semantic limit")
        self._body.append(text)
        return [text]

    def finish(self) -> dict[str, object]:
        if self._failed or self._finished:
            self._fail("stream is no longer active")
        try:
            tail = self._utf8.close()
            if tail:
                self._consume(tail)
            if self._mode == "end":
                result = {"text": "", "end": True}
            elif self._mode == "speech":
                result = {"text": self.released_text, "end": False}
            else:
                self._fail("P output ended before a complete prefix")
            validated = validate_semantic(result)
        except (EfficiencyContractError, ContractViolation) as error:
            self._failed = True
            if isinstance(error, EfficiencyContractError):
                raise
            raise EfficiencyContractError(str(error)) from error
        self._finished = True
        return validated

    def cancel(self) -> None:
        if self._finished:
            self._fail("successful stream cannot be cancelled")
        self._failed = True
        raise EfficiencyContractError("stream cancelled before terminal")


class JsonSemanticStreamDecoder:
    """Incrementally decode the exact flat ``text/end`` JSON object.

    The finite-state parser releases decoded ``text`` string fragments without
    waiting for the final object. It still validates the complete JSON bytes and
    exact semantic relation at terminal, so released text never implies success.
    """

    _WHITESPACE = " \t\r\n"
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

    def __init__(self, *, maximum_text_codepoints: int = P_MAX_TEXT_CODEPOINTS) -> None:
        self._utf8 = _Utf8Stream()
        self._maximum_text_codepoints = maximum_text_codepoints
        self._wire: list[str] = []
        self._state = "START"
        self._seen: set[str] = set()
        self._current_key: str | None = None
        self._key: list[str] = []
        self._text: list[str] = []
        self._text_length = 0
        self._end: bool | None = None
        self._escape_target: str | None = None
        self._unicode_digits = ""
        self._high_surrogate: int | None = None
        self._literal = ""
        self._literal_target = ""
        self._failed = False
        self._finished = False

    @property
    def released_text(self) -> str:
        return "".join(self._text)

    def _fail(self, message: str) -> None:
        self._failed = True
        raise EfficiencyContractError(message)

    def feed(self, chunk: bytes | str) -> list[str]:
        if self._failed or self._finished:
            self._fail("stream is no longer active")
        try:
            text = self._utf8.decode(chunk)
            self._wire.append(text)
            released: list[str] = []
            for char in text:
                fragment = self._consume_char(char)
                if fragment:
                    released.append(fragment)
            return released
        except EfficiencyContractError:
            self._failed = True
            raise

    def _consume_char(self, char: str) -> str | None:
        if self._state == "START":
            if char in self._WHITESPACE:
                return None
            if char != "{":
                self._fail("JSON semantic output must start with an object")
            self._state = "KEY_OR_END"
            return None
        if self._state == "KEY_OR_END":
            if char in self._WHITESPACE:
                return None
            if char == "}":
                self._state = "DONE"
                return None
            if char != '"':
                self._fail("JSON object key must be a string")
            self._key = []
            self._state = "KEY_STRING"
            return None
        if self._state in {"KEY_STRING", "TEXT_STRING"}:
            if self._state == "TEXT_STRING" and self._high_surrogate is not None and char != "\\":
                self._fail("high surrogate not followed by low surrogate")
            if char == '"':
                if self._state == "KEY_STRING":
                    key = "".join(self._key)
                    if key not in {"text", "end"} or key in self._seen:
                        self._fail("JSON contains unknown or duplicate key")
                    self._current_key = key
                    self._state = "COLON"
                else:
                    if self._high_surrogate is not None:
                        self._fail("unpaired JSON high surrogate")
                    self._seen.add("text")
                    self._state = "AFTER_VALUE"
                return None
            if char == "\\":
                self._escape_target = "key" if self._state == "KEY_STRING" else "text"
                self._state = "ESCAPE"
                return None
            if ord(char) < 0x20:
                self._fail("unescaped JSON control character")
            if self._state == "KEY_STRING":
                self._key.append(char)
                return None
            return self._append_text(char)
        if self._state == "ESCAPE":
            if char == "u":
                self._unicode_digits = ""
                self._state = "UNICODE"
                return None
            if char not in self._SIMPLE_ESCAPES:
                self._fail("invalid JSON escape")
            value = self._SIMPLE_ESCAPES[char]
            target = self._escape_target
            self._escape_target = None
            self._state = "KEY_STRING" if target == "key" else "TEXT_STRING"
            if target == "key":
                self._key.append(value)
                return None
            if self._high_surrogate is not None:
                self._fail("high surrogate not followed by low surrogate")
            return self._append_text(value)
        if self._state == "UNICODE":
            if char not in "0123456789abcdefABCDEF":
                self._fail("invalid JSON Unicode escape")
            self._unicode_digits += char
            if len(self._unicode_digits) < 4:
                return None
            value = int(self._unicode_digits, 16)
            target = self._escape_target
            self._unicode_digits = ""
            self._escape_target = None
            if target == "key":
                if 0xD800 <= value <= 0xDFFF:
                    self._fail("surrogate is not valid in a JSON key")
                self._key.append(chr(value))
                self._state = "KEY_STRING"
                return None
            self._state = "TEXT_STRING"
            if self._high_surrogate is not None:
                if not 0xDC00 <= value <= 0xDFFF:
                    self._fail("high surrogate not followed by low surrogate")
                combined = 0x10000 + ((self._high_surrogate - 0xD800) << 10) + (value - 0xDC00)
                self._high_surrogate = None
                return self._append_text(chr(combined))
            if 0xD800 <= value <= 0xDBFF:
                self._high_surrogate = value
                return None
            if 0xDC00 <= value <= 0xDFFF:
                self._fail("unpaired JSON low surrogate")
            return self._append_text(chr(value))
        if self._state == "COLON":
            if char in self._WHITESPACE:
                return None
            if char != ":":
                self._fail("JSON object key lacks colon")
            self._state = "BEFORE_VALUE"
            return None
        if self._state == "BEFORE_VALUE":
            if char in self._WHITESPACE:
                return None
            if self._current_key == "text":
                if char != '"':
                    self._fail("JSON text value must be a string")
                self._state = "TEXT_STRING"
                return None
            if char not in {"t", "f"}:
                self._fail("JSON end value must be boolean")
            self._literal_target = "true" if char == "t" else "false"
            self._literal = char
            self._state = "END_LITERAL"
            return None
        if self._state == "END_LITERAL":
            self._literal += char
            if not self._literal_target.startswith(self._literal):
                self._fail("invalid JSON boolean")
            if self._literal == self._literal_target:
                self._end = self._literal == "true"
                self._seen.add("end")
                self._state = "AFTER_VALUE"
            return None
        if self._state == "AFTER_VALUE":
            if char in self._WHITESPACE:
                return None
            if char == ",":
                self._state = "KEY_OR_END"
                return None
            if char == "}":
                self._state = "DONE"
                return None
            self._fail("JSON object has invalid separator")
        if self._state == "DONE":
            if char not in self._WHITESPACE:
                self._fail("JSON has trailing output")
            return None
        self._fail("invalid JSON parser state")

    def _append_text(self, value: str) -> str:
        self._text_length += len(value)
        if self._text_length > self._maximum_text_codepoints:
            self._fail("JSON text exceeds semantic limit")
        self._text.append(value)
        return value

    def finish(self) -> dict[str, object]:
        if self._failed or self._finished:
            self._fail("stream is no longer active")
        try:
            tail = self._utf8.close()
            if tail:
                self._wire.append(tail)
                for char in tail:
                    self._consume_char(char)
            if self._state != "DONE" or self._seen != {"text", "end"}:
                self._fail("JSON output ended before exact text/end object")
            wire_value = json.loads("".join(self._wire))
            result = validate_efficiency_semantic(wire_value)
            if result["text"] != self.released_text or result["end"] is not self._end:
                self._fail("incremental JSON projection disagrees with terminal object")
        except (json.JSONDecodeError, EfficiencyContractError, ContractViolation) as error:
            self._failed = True
            if isinstance(error, EfficiencyContractError):
                raise
            raise EfficiencyContractError(str(error)) from error
        self._finished = True
        return result

    def cancel(self) -> None:
        if self._finished:
            self._fail("successful stream cannot be cancelled")
        self._failed = True
        raise EfficiencyContractError("stream cancelled before terminal")


def decode_chunks(decoder: PrefixStreamDecoder | JsonSemanticStreamDecoder,
                  chunks: Iterable[bytes | str]) -> tuple[list[str], dict[str, object]]:
    """Test/adapter helper returning provisional fragments and final semantics."""

    released: list[str] = []
    for chunk in chunks:
        released.extend(decoder.feed(chunk))
    return released, decoder.finish()
