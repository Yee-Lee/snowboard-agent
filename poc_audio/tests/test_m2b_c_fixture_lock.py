from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import wave

from audio_poc.m2b_c_fixture_lock import (
    _derive_internal,
    sha256_file,
    validate_lock,
)


class M2BCFixtureLockTests(unittest.TestCase):
    def _source_wav(self, path: Path, frames: int = 32_000) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16_000)
            target.writeframes(b"\x01\x00" * frames)

    def test_internal_derivation_keeps_three_separate_padding_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "selection" / "sources/internal/item.wav"
            self._source_wav(source)
            preview = root / "preview.wav"
            self._source_wav(preview, frames=16_000)
            record = {
                "review_id": "I99",
                "split": "dev",
                "fixture_id": "item",
                "category": "code_switch",
                "selected_reference_text": "reference",
                "selected_reference_sha256": "refhash",
                "source_relpath": "sources/internal/item.wav",
                "source_sha256": sha256_file(source),
                "speech_start_ms": 500,
                "speech_end_ms": 1500,
                "p0_preview_size_bytes": preview.stat().st_size,
                "p0_preview_sha256": sha256_file(preview),
            }
            sanitized, controlled = _derive_internal(
                record, root / "selection", root / "output"
            )
            self.assertEqual([v["profile"] for v in sanitized["variants"]], ["p0", "p300", "p500"])
            self.assertEqual([v["frames"] for v in sanitized["variants"]], [16_000, 25_600, 32_000])
            self.assertNotIn("reference_text", sanitized)
            self.assertEqual(controlled["reference_text"], "reference")

    def test_sanitized_validator_keeps_internal_and_common_voice_separate(self) -> None:
        internal = [{"variants": [{}, {}, {}]} for _ in range(16)]
        external = [{} for _ in range(8)]
        document = {
            "fixture_lock_id": "M2B-C-PCM-LOCK-001",
            "status": "LOCKED_NOT_EXECUTED",
            "candidate_execution": "NOT_STARTED",
            "records": {"internal": internal, "common_voice": external},
        }
        validate_lock(document)
        document["records"]["common_voice"].pop()
        with self.assertRaisesRegex(ValueError, "8 Common Voice"):
            validate_lock(document)

    def test_sanitized_validator_rejects_controlled_text_fields(self) -> None:
        document = {
            "fixture_lock_id": "M2B-C-PCM-LOCK-001",
            "status": "LOCKED_NOT_EXECUTED",
            "candidate_execution": "NOT_STARTED",
            "records": {
                "internal": [{"variants": [{}, {}, {}]} for _ in range(16)],
                "common_voice": [{"reference_text": "private"}] + [{} for _ in range(7)],
            },
        }
        with self.assertRaisesRegex(ValueError, "controlled fields"):
            validate_lock(document)


if __name__ == "__main__":
    unittest.main()
