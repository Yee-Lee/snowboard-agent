from __future__ import annotations

import unittest

from poc_llm.efficiency.raw_stream import RawStreamChunk, RawStreamError, _message_text
from poc_llm.efficiency.streaming import consume_raw_stream, response_format


class Module:
    class ResponseFormat:
        @staticmethod
        def json(schema):
            return ("J", schema)
        @staticmethod
        def regex(pattern):
            return ("P", pattern)


class StreamingTests(unittest.TestCase):
    def test_response_format_selects_exact_constraint(self):
        self.assertEqual(response_format(Module, "J", {"type": "object"})[0], "J")
        self.assertTrue(response_format(Module, "P", {})[1].startswith("(?:E|"))

    def test_j_and_p_return_identical_semantics(self):
        j = consume_raw_stream([
            RawStreamChunk('{"text":"回答。","end":false}', False),
            RawStreamChunk("", True),
        ], encoding="J")
        p = consume_raw_stream([
            RawStreamChunk("S\n回", False), RawStreamChunk("答。", False), RawStreamChunk("", True),
        ], encoding="P")
        self.assertEqual(j.semantic, p.semantic)
        self.assertIsNotNone(j.first_decodable_text_ms)
        self.assertEqual(p.first_chunk_codepoints, 3)

    def test_short_unpunctuated_text_becomes_first_chunk_at_terminal(self):
        result = consume_raw_stream([
            RawStreamChunk("S\nshort", False),
            RawStreamChunk("", True),
        ], encoding="P")
        self.assertIsNotNone(result.first_chunk_ms)
        self.assertEqual(result.first_chunk_codepoints, 5)

    def test_missing_or_late_terminal_and_failure_cancel_provisional_sink(self):
        events = []
        with self.assertRaisesRegex(RawStreamError, "MISSING_TERMINAL"):
            consume_raw_stream([RawStreamChunk("S\nreleased", False)], encoding="P", on_provisional_text=events.append)
        self.assertEqual(events[-1], "")
        with self.assertRaises(RawStreamError):
            consume_raw_stream([RawStreamChunk("E", False), RawStreamChunk("", True), RawStreamChunk("x", False)], encoding="P")

    def test_message_json_extraction_rejects_non_text_content(self):
        self.assertEqual(_message_text('{"role":"assistant","content":[{"type":"text","text":"S\\n答案"}]}'), "S\n答案")
        with self.assertRaises(RawStreamError):
            _message_text('{"role":"assistant","content":[{"type":"tool_call","name":"x"}]}')


if __name__ == "__main__":
    unittest.main()
