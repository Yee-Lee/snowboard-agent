"""Exact-0.16 POC adapter preserving native stream final/error terminals.

LiteRT-LM 0.16's public Python iterator intentionally hides CANCELLED and token
limit as ordinary exhaustion. The efficiency contract requires normal runtime
termination, so this adapter uses the packaged Conversation's frozen private
bridge and C ABI. It is not proposed as a production API.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import queue
from typing import Any, Iterator


class RawStreamError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RawStreamChunk:
    text: str
    is_final: bool


def _message_text(serialized: str) -> str:
    try:
        message = json.loads(serialized)
    except json.JSONDecodeError as error:
        raise RawStreamError("PROTOCOL_ERROR") from error
    if not isinstance(message, dict) or set(message).difference({"role", "content"}):
        raise RawStreamError("PROTOCOL_ERROR")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise RawStreamError("PROTOCOL_ERROR")
    values: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
            raise RawStreamError("PROTOCOL_ERROR")
        if set(item).difference({"type", "text"}):
            raise RawStreamError("PROTOCOL_ERROR")
        values.append(item["text"])
    return "".join(values)


def send_message_raw(conversation: Any, message: str, *, response_format: Any) -> Iterator[RawStreamChunk]:
    """Yield model text and an explicit final marker from frozen Conversation internals."""

    try:
        from litert_lm._ffi import STREAM_CALLBACK_TYPE
        from litert_lm._messages import normalize_message
    except (ImportError, AttributeError) as error:
        raise RawStreamError("UNSUPPORTED") from error
    if getattr(conversation, "automatic_tool_calling", True):
        raise RawStreamError("PROTOCOL_ERROR")
    if not getattr(conversation, "_ptr", None):
        raise RawStreamError("PROTOCOL_ERROR")

    events: queue.Queue[tuple[str, str, bool]] = queue.Queue()

    def callback(unused_data: Any, chunk_ptr: Any) -> None:
        error_value = conversation._lib.litert_lm_stream_chunk_get_error(chunk_ptr)
        if error_value:
            try:
                detail = error_value.decode("utf-8")
            except UnicodeError:
                detail = ""
            events.put(("error", detail, True))
            return
        text_value = conversation._lib.litert_lm_stream_chunk_get_text(chunk_ptr)
        try:
            text = text_value.decode("utf-8") if text_value else ""
        except UnicodeError:
            events.put(("error", "INVALID_UTF8", True))
            return
        final = bool(conversation._lib.litert_lm_stream_chunk_is_final(chunk_ptr))
        events.put(("chunk", text, final))

    c_callback = STREAM_CALLBACK_TYPE(callback)
    conversation._current_callback = c_callback
    try:
        normalized = normalize_message(message)
        active_format = conversation._resolve_response_format(normalized, response_format)
        optional_args = conversation._create_optional_args(
            repetition_penalty_config=None,
            no_repeat_ngram_config=None,
            suppress_tokens_config=None,
            max_output_tokens=None,
            thinking_config=None,
            current_message=normalized,
            response_format=active_format,
        )
        try:
            result = conversation._lib.litert_lm_conversation_send_message_stream(
                conversation._ptr,
                json.dumps(normalized),
                json.dumps(getattr(conversation, "extra_context", {})),
                optional_args,
                c_callback,
                None,
            )
        finally:
            conversation._delete_optional_args(optional_args)
    except RawStreamError:
        raise
    except Exception as error:
        raise RawStreamError("UNSUPPORTED") from error
    if result != 0:
        raise RawStreamError("NATIVE_FAILURE")

    while True:
        kind, value, is_final = events.get()
        if kind == "error":
            if "CANCELLED" in value:
                raise RawStreamError("CANCELLED")
            if "Max number of tokens reached" in value:
                raise RawStreamError("TOKEN_LIMIT")
            if value == "INVALID_UTF8":
                raise RawStreamError("INVALID_UTF8")
            raise RawStreamError("NATIVE_FAILURE")
        if value:
            yield RawStreamChunk(_message_text(value), is_final=False)
        if is_final:
            yield RawStreamChunk("", is_final=True)
            return
