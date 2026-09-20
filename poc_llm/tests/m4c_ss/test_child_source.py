from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

from poc_llm.m4c_ss.child_source import ChildS2Source, StreamingChildRuntime


FAKE_CHILD = r'''import json, sys, time
print(json.dumps({"protocol":1,"type":"READY"}), flush=True)
for line in sys.stdin:
    value=json.loads(line)
    if value.get("op")=="GENERATE":
        if value["request"].get("hang"):
            time.sleep(60)
        print(json.dumps({"protocol":1,"type":"CHUNK","text":"{\"text\":\"回答。\",\"end\":false}","is_final":False}), flush=True)
        print(json.dumps({"protocol":1,"type":"CHUNK","text":"","is_final":True}), flush=True)
    elif value.get("op")=="SHUTDOWN":
        print(json.dumps({"protocol":1,"type":"SHUTDOWN_ACK"}), flush=True)
        break
'''


class ChildSourceTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, directory: str) -> StreamingChildRuntime:
        script = Path(directory) / "fake_child.py"
        script.write_text(textwrap.dedent(FAKE_CHILD), encoding="utf-8")
        return StreamingChildRuntime(
            [sys.executable, "-u", str(script)], cwd=directory, env=dict(os.environ),
            startup_timeout_s=2.0, generation_timeout_s=2.0,
        )

    async def test_streams_s2_and_reuses_one_child(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(directory)
            runtime.start()
            try:
                for _ in range(2):
                    emitted = []
                    source = ChildS2Source(runtime, {"case": "public"})
                    terminal = await source.generate(
                        lambda text: asyncio.sleep(0, result=emitted.append(text)),
                    )
                    self.assertEqual((emitted, terminal.text), (["回答。"], "回答。"))
                    self.assertTrue(source.operation_idle())
            finally:
                runtime.close()
            self.assertTrue(runtime.process_group_absent())

    async def test_force_abort_reaps_hung_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.runtime(directory)
            runtime.start()
            source = ChildS2Source(runtime, {"hang": True})
            running = asyncio.create_task(source.generate(lambda _text: asyncio.sleep(0)))
            for _ in range(100):
                if not source.operation_idle():
                    break
                await asyncio.sleep(0.001)
            await source.force_abort()
            with self.assertRaises(Exception):
                await running
            self.assertTrue(source.operation_idle())
            self.assertTrue(runtime.process_group_absent())


if __name__ == "__main__":
    unittest.main()
