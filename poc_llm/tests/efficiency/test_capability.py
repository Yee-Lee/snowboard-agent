from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from poc_llm.efficiency.capability import CapabilityError, inspect_frozen_wheel


class CapabilityTests(unittest.TestCase):
    def _wheel(self, directory: str) -> tuple[Path, str]:
        path = Path(directory) / "runtime.whl"
        with ZipFile(path, "w") as wheel:
            wheel.writestr("litert_lm/interfaces.py", "REGEX = 1\nJSON_OBJECT = 2\ndef regex(cls, pattern: str): pass\n")
            wheel.writestr("litert_lm/conversation.py", '!= LiteRtLmConstraintProviderType.LL_GUIDANCE\n"CANCELLED" in err_msg\n"Max number of tokens reached" in err_msg\nbreak\n')
            wheel.writestr("litert_lm/_ffi.py", "REGEX = 1\nJSON_SCHEMA = 2\nlitert_lm_stream_chunk_is_final\nlitert_lm_stream_chunk_get_error\n")
            wheel.writestr("litert_lm_api-0.16.0.dist-info/METADATA", "Name: litert-lm-api\nVersion: 0.16.0\n")
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_inventory_requires_exact_digest_and_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            path, digest = self._wheel(directory)
            value = inspect_frozen_wheel(path, expected_sha256=digest)
            self.assertTrue(value["python_public_api"]["response_format_regex"])
            self.assertTrue(value["wrapper_limitation"]["requires_raw_terminal_adapter_for_normal_termination_proof"])
            with self.assertRaises(CapabilityError):
                inspect_frozen_wheel(path, expected_sha256="0" * 64)

