#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
import threading
import types
import unittest
from unittest import mock

from poc_llm.harness.litert_lm_pi_async_child_adapter_v1 import LiteRtAsyncBackend


CONFIG = {
    "model_path": "/tmp/model.litertlm",
    "threads": 4,
    "temperature": 0.0,
    "top_p": 1.0,
    "engine_max_num_tokens": 512,
}


class AsyncAdapterTests(unittest.TestCase):
    def test_cancel_once_discards_conversation_and_new_conversation_is_healthy(self):
        created = []
        first_chunk = threading.Event()
        cancel_seen = threading.Event()

        class Conversation:
            def __init__(self, ordinal):
                self.ordinal = ordinal
                self.cancel_count = 0
                self.closed = False

            def send_message_async(self, prompt):
                yield {"content": [{"type": "text", "text": "chunk"}]}
                if self.ordinal == 0:
                    first_chunk.set()
                    if not cancel_seen.wait(1):
                        raise AssertionError("cancel not observed")

            def cancel_process(self):
                self.cancel_count += 1
                cancel_seen.set()

            def get_benchmark_info(self):
                return types.SimpleNamespace(
                    init_time_in_second=0.1,
                    time_to_first_token_in_second=0.2,
                    last_prefill_token_count=3,
                    last_prefill_tokens_per_second=4.0,
                    last_decode_token_count=5,
                    last_decode_tokens_per_second=6.0,
                )

            @property
            def token_count(self):
                return 8

            def close(self):
                self.closed = True

        class Engine:
            def __init__(self, model_path, **kwargs):
                self.closed = False

            def create_conversation(self, **kwargs):
                conversation = Conversation(len(created))
                created.append(conversation)
                return conversation

            def close(self):
                self.closed = True

        fake = types.SimpleNamespace(
            Engine=Engine,
            Backend=types.SimpleNamespace(CPU=lambda **kwargs: ("CPU", kwargs)),
            SamplerConfig=lambda **kwargs: ("SAMPLER", kwargs),
        )
        with mock.patch.dict(sys.modules, {"litert_lm": fake}):
            backend = LiteRtAsyncBackend(CONFIG)
        outcome = {}

        def generate_first():
            outcome["first"] = backend.generate("first", max_output_tokens=16)

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            worker = threading.Thread(target=generate_first)
            worker.start()
            self.assertTrue(first_chunk.wait(1))
            backend.cancel()
            backend.cancel()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            outcome["health"] = backend.generate("health", max_output_tokens=16)

        self.assertEqual(len(created), 2)
        self.assertEqual(created[0].cancel_count, 1)
        self.assertTrue(created[0].closed)
        self.assertEqual(created[1].cancel_count, 0)
        self.assertTrue(created[1].closed)
        self.assertEqual(outcome["health"].text, "chunk")
        self.assertEqual(stderr.getvalue().count("native_cancel_once"), 1)
        self.assertEqual(stderr.getvalue().count("stream_terminal_cancelled"), 1)
        self.assertEqual(stderr.getvalue().count("stream_terminal_completed"), 1)
        self.assertEqual(stderr.getvalue().count("conversation_discarded"), 2)
        self.assertEqual(stderr.getvalue().count("first_chunk"), 2)
        backend.close()

    def test_invalid_backend_api_failure_is_sanitized_by_type(self):
        class Conversation:
            def send_message_async(self, prompt):
                raise RuntimeError("private detail")
                yield

            def cancel_process(self):
                pass

            def close(self):
                pass

        class Engine:
            def __init__(self, model_path, **kwargs):
                pass

            def create_conversation(self, **kwargs):
                return Conversation()

            def close(self):
                pass

        fake = types.SimpleNamespace(
            Engine=Engine,
            Backend=types.SimpleNamespace(CPU=lambda **kwargs: ("CPU", kwargs)),
            SamplerConfig=lambda **kwargs: ("SAMPLER", kwargs),
        )
        with mock.patch.dict(sys.modules, {"litert_lm": fake}):
            backend = LiteRtAsyncBackend(CONFIG)
        with self.assertRaisesRegex(RuntimeError, "send_message_async failed") as caught:
            backend.generate("secret", max_output_tokens=16)
        self.assertNotIn("private detail", str(caught.exception))
        backend.close()


if __name__ == "__main__":
    unittest.main()
