from __future__ import annotations

import itertools
import unittest

from poc_llm.efficiency.contract import (
    EfficiencyContractError,
    JsonSemanticStreamDecoder,
    P_RESPONSE_REGEX,
    PrefixStreamDecoder,
    decode_chunks,
)


def all_byte_splits(value: str):
    raw = value.encode("utf-8")
    for index in range(len(raw) + 1):
        yield [raw[:index], raw[index:]]


class PrefixStreamDecoderTests(unittest.TestCase):
    def test_regex_is_frozen_and_avoids_lookaround(self):
        self.assertEqual(P_RESPONSE_REGEX, r"(?:E|S\n\s*[^\s][\s\S]*)")
        self.assertNotIn("?=", P_RESPONSE_REGEX)

    def test_every_byte_boundary_preserves_utf8_body(self):
        expected = {"text": "天空 S 與 E。", "end": False}
        for chunks in all_byte_splits("S\n天空 S 與 E。"):
            with self.subTest(chunks=chunks):
                released, semantic = decode_chunks(PrefixStreamDecoder(), chunks)
                self.assertEqual("".join(released), expected["text"])
                self.assertEqual(semantic, expected)

    def test_prefix_is_not_released_and_exact_e_waits_for_terminal(self):
        subject = PrefixStreamDecoder()
        self.assertEqual(subject.feed(b"S"), [])
        self.assertEqual(subject.feed(b"\n\xe5\x9b\x9e"), ["回"])
        self.assertEqual(subject.finish(), {"text": "回", "end": False})
        end = PrefixStreamDecoder()
        self.assertEqual(end.feed("E"), [])
        self.assertEqual(end.finish(), {"text": "", "end": True})

    def test_invalid_cases_fail_closed(self):
        cases = [b"", b"X", b"S", b"S\n", b"S\n \t", b"Eextra", b"\xef\xbb\xbfS\nx", b" S\nx"]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(EfficiencyContractError):
                decode_chunks(PrefixStreamDecoder(), [value])
        with self.assertRaises(EfficiencyContractError):
            decode_chunks(PrefixStreamDecoder(), [b"S\n\xff"])
        with self.assertRaises(EfficiencyContractError):
            decode_chunks(PrefixStreamDecoder(maximum_text_codepoints=2), ["S\n三個字"])

    def test_cancel_before_and_after_fragment_never_succeeds(self):
        for chunks in (["S"], ["S\nprovisional"]):
            subject = PrefixStreamDecoder()
            for chunk in chunks:
                subject.feed(chunk)
            with self.assertRaisesRegex(EfficiencyContractError, "cancelled"):
                subject.cancel()
            with self.assertRaises(EfficiencyContractError):
                subject.finish()


class JsonSemanticStreamDecoderTests(unittest.TestCase):
    def test_every_byte_boundary_releases_same_unicode_text(self):
        wire = '{"text":"天空\\n😀","end":false}'
        for chunks in all_byte_splits(wire):
            with self.subTest(chunks=chunks):
                released, semantic = decode_chunks(JsonSemanticStreamDecoder(), chunks)
                self.assertEqual("".join(released), "天空\n😀")
                self.assertEqual(semantic, {"text": "天空\n😀", "end": False})

    def test_key_order_escapes_and_surrogate_pair(self):
        chunks = ['{"end":fal', 'se,"te', 'xt":"A\\"\\/\\b\\f\\n\\r\\t\\uD83D', '\\uDE00"}']
        released, semantic = decode_chunks(JsonSemanticStreamDecoder(), chunks)
        expected = 'A"/\b\f\n\r\t😀'
        self.assertEqual("".join(released), expected)
        self.assertEqual(semantic, {"text": expected, "end": False})

    def test_exact_end_object(self):
        released, semantic = decode_chunks(JsonSemanticStreamDecoder(), [' { "text" : "", "end" : true } '])
        self.assertEqual(released, [])
        self.assertEqual(semantic, {"text": "", "end": True})

    def test_structural_and_terminal_failures(self):
        cases = [
            '{}',
            '{"text":"x"}',
            '{"text":"x","end":false,"extra":0}',
            '{"text":"x","text":"y","end":false}',
            '{"text":"","end":false}',
            '{"text":"x","end":false}junk',
            '{"text":"\\uDC00","end":false}',
            '{"text":"\\uD83Dx","end":false}',
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(EfficiencyContractError):
                decode_chunks(JsonSemanticStreamDecoder(), [value])
        released, semantic = decode_chunks(
            JsonSemanticStreamDecoder(), ['{"text":"再見","end":true}'])
        self.assertEqual("".join(released), "再見")
        self.assertEqual(semantic, {"text": "再見", "end": True})

    def test_overflow_invalid_utf8_truncation_and_cancel(self):
        with self.assertRaises(EfficiencyContractError):
            decode_chunks(JsonSemanticStreamDecoder(maximum_text_codepoints=2), ['{"text":"三個字","end":false}'])
        with self.assertRaises(EfficiencyContractError):
            decode_chunks(JsonSemanticStreamDecoder(), [b'{"text":"\xff'])
        with self.assertRaises(EfficiencyContractError):
            decode_chunks(JsonSemanticStreamDecoder(), ['{"text":"x"'])
        subject = JsonSemanticStreamDecoder()
        self.assertEqual(subject.feed('{"text":"released'), list("released"))
        with self.assertRaisesRegex(EfficiencyContractError, "cancelled"):
            subject.cancel()
        with self.assertRaises(EfficiencyContractError):
            subject.feed('","end":false}')

    def test_bad_late_terminal_invalidates_released_text(self):
        subject = JsonSemanticStreamDecoder()
        self.assertEqual("".join(subject.feed('{"text":"provisional","end":')), "provisional")
        subject.feed("true}")
        with self.assertRaises(EfficiencyContractError):
            subject.feed("junk")
        with self.assertRaises(EfficiencyContractError):
            subject.finish()


if __name__ == "__main__":
    unittest.main()
