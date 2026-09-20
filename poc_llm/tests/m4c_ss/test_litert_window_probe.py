from __future__ import annotations

import hashlib
import json
import stat
import tempfile
from pathlib import Path
import unittest

from poc_llm.m4c_ss.litert_window_probe import PrivateChunkJournal


class PrivateChunkJournalTests(unittest.TestCase):
    def test_retains_private_raw_chunks_with_digest_and_owner_only_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw-stream.jsonl"
            journal = PrivateChunkJournal(path)
            journal.append(offset_ns=123, text="private answer", is_final=False)
            journal.append(offset_ns=456, text="", is_final=True)
            journal.close()
            journal.close()

            payload = path.read_bytes()
            rows = [json.loads(line) for line in payload.splitlines()]
            self.assertEqual(rows, [
                {"offset_ns": 123, "text": "private answer", "is_final": False},
                {"offset_ns": 456, "text": "", "is_final": True},
            ])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(journal.bytes, len(payload))
            self.assertEqual(journal.sha256, hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
