"""Encoding-neutral stream validation and timing for experiment A/B."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Iterable

from poc_llm.efficiency.contract import JsonSemanticStreamDecoder, P_RESPONSE_REGEX, PrefixStreamDecoder
from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError


PUNCTUATION = frozenset("。！？!?；;，,")


@dataclass(frozen=True)
class StreamResult:
    semantic: dict[str, object]
    first_decodable_text_ms: float | None
    first_chunk_ms: float | None
    first_chunk_codepoints: int | None


def response_format(litert_lm_module: Any, encoding: str, semantic_schema: dict[str, Any]) -> Any:
    if encoding == "J":
        return litert_lm_module.ResponseFormat.json(semantic_schema)
    if encoding == "P":
        return litert_lm_module.ResponseFormat.regex(P_RESPONSE_REGEX)
    raise ValueError("encoding must be J or P")


def consume_raw_stream(
    chunks: Iterable[RawStreamChunk],
    *,
    encoding: str,
    started_ns: int | None = None,
    clock_ns: Callable[[], int] = time.monotonic_ns,
    on_provisional_text: Callable[[str], None] | None = None,
) -> StreamResult:
    """Consume exactly one normally terminated stream; no repair or retry."""

    decoder = JsonSemanticStreamDecoder() if encoding == "J" else PrefixStreamDecoder()
    started = clock_ns() if started_ns is None else started_ns
    first_text: float | None = None
    first_chunk: float | None = None
    accumulated = ""
    chunk_codepoints: int | None = None
    final_seen = False
    try:
        for chunk in chunks:
            if final_seen:
                raise RawStreamError("PROTOCOL_ERROR")
            if chunk.is_final:
                if chunk.text:
                    raise RawStreamError("PROTOCOL_ERROR")
                final_seen = True
                continue
            for fragment in decoder.feed(chunk.text):
                now = clock_ns()
                if fragment and first_text is None:
                    first_text = (now - started) / 1_000_000
                if fragment:
                    accumulated += fragment
                    if on_provisional_text is not None:
                        on_provisional_text(fragment)
                    if first_chunk is None and (len(accumulated) >= 24 or any(c in PUNCTUATION for c in accumulated)):
                        first_chunk = (now - started) / 1_000_000
                        chunk_codepoints = min(len(accumulated), 24)
        if not final_seen:
            raise RawStreamError("MISSING_TERMINAL")
        semantic = decoder.finish()
    except Exception:
        if on_provisional_text is not None and accumulated:
            on_provisional_text("")
        raise
    return StreamResult(semantic, first_text, first_chunk, chunk_codepoints)
