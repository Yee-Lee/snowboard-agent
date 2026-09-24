"""M4C-SS-EXTRACT-001 — punctuation-or-12 safe text extraction."""

from __future__ import annotations

import pytest

from sbd.cognition.semantic import IncrementalSafeTextParser, SemanticOutput


def _feed(wire: bytes, partitions: tuple[int, ...] = ()):
    parser = IncrementalSafeTextParser(12)
    fragments: list[str] = []
    start = 0
    for end in (*partitions, len(wire)):
        fragments.extend(parser.feed(wire[start:end]))
        start = end
    terminal, flushed = parser.finish()
    fragments.extend(flushed)
    return terminal, tuple(fragments)


def test_m4c_ss_extract_001_e01_punctuation_is_earliest_boundary() -> None:
    terminal, fragments = _feed('{"text":"你好。還好嗎","end":false}'.encode())
    assert terminal == SemanticOutput("你好。還好嗎", False)
    assert fragments == ("你好。", "還好嗎")


def test_m4c_ss_extract_001_e02_exactly_twelve_codepoints() -> None:
    text = "甲乙丙丁戊己庚辛壬癸子丑寅"
    terminal, fragments = _feed(f'{{"text":"{text}","end":false}}'.encode())
    assert fragments == (text[:12], text[12:])
    assert "".join(fragments) == terminal.text


def test_m4c_ss_extract_001_e03_terminal_flushes_eleven() -> None:
    text = "甲乙丙丁戊己庚辛壬癸子"
    terminal, fragments = _feed(f'{{"text":"{text}","end":false}}'.encode())
    assert fragments == (text,)
    assert terminal.text == text


def test_m4c_ss_extract_001_e04_combining_sequence_is_stable() -> None:
    wire = b'{"text":"e\\u0301abcdefghijk","end":false}'
    split = wire.index(b"0301") + 2
    terminal, fragments = _feed(wire, (split, split + 2))
    assert terminal.text == "éabcdefghijk"
    assert "".join(fragments) == terminal.text
    assert all(not value.endswith("e") for value in fragments[:-1])


@pytest.mark.parametrize("split", range(9, 16))
def test_m4c_ss_extract_001_e05_split_escape_is_never_exposed(split) -> None:
    wire = b'{"text":"hello\\nworld!","end":false}'
    terminal, fragments = _feed(wire, (split,))
    assert "\\n" not in "".join(fragments)
    assert "".join(fragments) == terminal.text


def test_m4c_ss_extract_001_e06_non_bmp_counts_as_one_codepoint() -> None:
    text = "🙂" * 13
    terminal, fragments = _feed(f'{{"text":"{text}","end":false}}'.encode())
    assert tuple(map(len, fragments)) == (12, 1)
    assert "".join(fragments) == terminal.text


def test_m4c_ss_extract_001_e09_end_true_flushes_terminal() -> None:
    terminal, fragments = _feed(b'{"text":"short","end":true}')
    assert terminal == SemanticOutput("short", True)
    assert fragments == ("short",)


def test_m4c_ss_extract_001_e10_whitespace_only_emits_nothing() -> None:
    terminal, fragments = _feed(b'{"text":" \\t ","end":true}')
    assert terminal == SemanticOutput("", True)
    assert fragments == ()


def test_m4c_ss_extract_001_every_byte_boundary_is_incremental() -> None:
    wire = b'{"text":"answer.","end":false}'
    for boundary in range(len(wire) + 1):
        terminal, fragments = _feed(wire, (boundary,))
        assert terminal == SemanticOutput("answer.", False)
        assert "".join(fragments) == terminal.text
