from __future__ import annotations

import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.m4a_whispercpp_preflight import (  # noqa: E402
    FALLBACK_ID,
    PRIMARY_ID,
    q5_fallback_reason,
    resolve_controlled_path,
    validate_recovery_manifest,
    verify_source_license,
)
from audio_poc.m4a_whispercpp_build import (  # noqa: E402
    CMAKE_FLAGS,
    configure_command,
    validate_cmake_cache,
    validate_dynamic_dependencies,
)


class WhisperCppRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(
            (REPO_ROOT / "poc_audio/manifests/m4a_asr_recovery_ack002.json").read_text(
                encoding="utf-8"
            )
        )

    def test_tracked_manifest_matches_ack002(self) -> None:
        validate_recovery_manifest(self.manifest)
        self.assertEqual(
            [candidate["candidate_id"] for candidate in self.manifest["candidates"]],
            [PRIMARY_ID, FALLBACK_ID],
        )
        self.assertEqual(self.manifest["runtime_profile"]["cpu_threads"], 4)

    def test_q5_requires_quality_pass_and_a_frozen_trigger(self) -> None:
        passing = {
            "report_id": "M4A-G1B-ASR-RECOVERY-QUALIFICATION",
            "review_status": "REVIEWED",
            "candidate_id": PRIMARY_ID,
            "quality": {
                "taiwan_mandarin_core_cer_percent": 20.0,
                "overall_sentence_correctness_percent": 70.0,
            },
            "performance": {
                "hot_final_transcript_p95_seconds": 1.51,
                "peak_rss_mib": 1000.0,
            },
        }
        self.assertEqual(q5_fallback_reason(passing), "Q8_LATENCY_HARD_GATE")
        passing["performance"] = {
            "hot_final_transcript_p95_seconds": 1.2,
            "peak_rss_mib": 1250.1,
        }
        self.assertEqual(q5_fallback_reason(passing), "Q8_PEAK_RSS_TRIGGER")

    def test_q5_stops_on_q8_quality_failure(self) -> None:
        result = {
            "report_id": "M4A-G1B-ASR-RECOVERY-QUALIFICATION",
            "review_status": "REVIEWED",
            "candidate_id": PRIMARY_ID,
            "quality": {
                "taiwan_mandarin_core_cer_percent": 20.01,
                "overall_sentence_correctness_percent": 90.0,
            },
            "performance": {
                "hot_final_transcript_p95_seconds": 2.0,
                "peak_rss_mib": 1300.0,
            },
        }
        with self.assertRaisesRegex(ValueError, "quality gate"):
            q5_fallback_reason(result)

    def test_q5_does_not_run_for_comparison_only(self) -> None:
        result = {
            "report_id": "M4A-G1B-ASR-RECOVERY-QUALIFICATION",
            "review_status": "REVIEWED",
            "candidate_id": PRIMARY_ID,
            "quality": {
                "taiwan_mandarin_core_cer_percent": 10.0,
                "overall_sentence_correctness_percent": 90.0,
            },
            "performance": {
                "hot_final_transcript_p95_seconds": 1.5,
                "peak_rss_mib": 1250.0,
            },
        }
        with self.assertRaisesRegex(ValueError, "must not execute"):
            q5_fallback_reason(result)

    def test_controlled_locator_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "invalid"):
                resolve_controlled_path(
                    self.manifest,
                    "controlled://audio-poc/gate1b/../ggml-small-q8_0.bin",
                    "ggml-small-q8_0.bin",
                    root,
                )

    def test_source_archive_requires_license_and_safe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                content = b"MIT\n"
                info = tarfile.TarInfo("whisper.cpp-1.9.2/LICENSE")
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
            verify_source_license(archive, "LICENSE")

    def test_cpu_only_build_command_contains_every_frozen_flag(self) -> None:
        command = configure_command(Path("/source"), Path("/build"))
        for name, value in CMAKE_FLAGS.items():
            self.assertIn(f"-D{name}={value}", command)
        self.assertIn("-DBUILD_SHARED_LIBS=OFF", command)

    def test_build_cache_must_retain_all_frozen_flags(self) -> None:
        validate_cmake_cache(dict(CMAKE_FLAGS))
        changed = dict(CMAKE_FLAGS)
        changed["GGML_BLAS"] = "ON"
        with self.assertRaisesRegex(RuntimeError, "GGML_BLAS=OFF"):
            validate_cmake_cache(changed)

    def test_build_rejects_prohibited_dynamic_dependency(self) -> None:
        validate_dynamic_dependencies("libm.so.6 => /lib/aarch64-linux-gnu/libm.so.6")
        with self.assertRaisesRegex(RuntimeError, "openblas"):
            validate_dynamic_dependencies("libopenblas.so.0 => /usr/lib/libopenblas.so.0")


if __name__ == "__main__":
    unittest.main()
