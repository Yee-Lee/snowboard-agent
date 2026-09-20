from __future__ import annotations

import unittest

from poc_llm.efficiency.raw_stream import RawStreamChunk
from poc_llm.m4c_ss.incremental_s2 import IncrementalS2, partial_text_value
from poc_llm.m4c_ss.s2 import consume_raw_s2


class IncrementalS2Tests(unittest.TestCase):
    def test_releases_punctuation_fragments_before_complete_object(self):
        events: list[str] = []

        def chunks():
            yield RawStreamChunk('{"text":"前段，後', False)
            events.append("after-first")
            yield RawStreamChunk('段。","end":false}', False)
            events.append("after-object")
            yield RawStreamChunk("", True)

        result = consume_raw_s2(chunks(), on_safe_text=events.append)
        self.assertEqual(result.text, "前段,後段。")
        self.assertEqual(events, ["前段,", "after-first", "後段。", "after-object"])

    def test_holds_normalization_segment_until_next_starter(self):
        events: list[str] = []

        def chunks():
            yield RawStreamChunk('{"text":"e', False)
            yield RawStreamChunk('\\u0301，後', False)
            yield RawStreamChunk('段。","end":false}', False)
            yield RawStreamChunk("", True)

        result = consume_raw_s2(chunks(), on_safe_text=events.append)
        self.assertEqual(result.text, "é,後段。")
        self.assertEqual(events, ["é,", "後段。"])

    def test_nfkd_leading_nonstarter_cannot_cross_released_boundary(self):
        prefix = "甲" * 23
        events: list[str] = []

        def chunks():
            yield RawStreamChunk('{"text":"' + prefix + "カ", False)
            yield RawStreamChunk("\\uFF9E。後", False)
            yield RawStreamChunk('段","end":false}', False)
            yield RawStreamChunk("", True)

        result = consume_raw_s2(chunks(), on_safe_text=events.append)
        self.assertEqual("".join(events), result.text)
        self.assertNotIn(prefix + "カ", events)

    def test_partial_surrogate_escape_is_not_exposed(self):
        self.assertEqual(partial_text_value('{"text":"\\uD83D'), ("", False))
        self.assertEqual(partial_text_value('{"text":"\\uD83D\\uDE00'), ("😀", False))

    def test_releases_at_24_codepoints_without_punctuation(self):
        text = "甲" * 25
        events: list[str] = []
        consume_raw_s2([
            RawStreamChunk('{"text":"' + text, False),
            RawStreamChunk('","end":false}', False),
            RawStreamChunk("", True),
        ], on_safe_text=events.append)
        self.assertEqual([len(item) for item in events], [24, 1])
        self.assertEqual("".join(events), text)

    def test_boundary_candidates_share_one_wire_without_rewriting(self):
        text = "甲" * 25
        expected = {
            8: [8, 8, 8, 1],
            12: [12, 12, 1],
            16: [16, 9],
            24: [24, 1],
        }
        for boundary, lengths in expected.items():
            events: list[str] = []
            incremental = IncrementalS2(max_codepoints=boundary)
            wire = '{"text":"' + text
            events.extend(incremental.feed(wire))
            events.extend(incremental.feed(wire + '","end":false}'))
            events.extend(incremental.flush(text))
            self.assertEqual([len(item) for item in events], lengths)
            self.assertEqual("".join(events), text)

    def test_rejects_unbounded_release_boundary(self):
        for value in (0, 257, True):
            with self.assertRaisesRegex(ValueError, "INVALID_RELEASE_BOUNDARY"):
                IncrementalS2(max_codepoints=value)



if __name__ == "__main__":
    unittest.main()
