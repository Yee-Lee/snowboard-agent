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
    safe_extract_source,
    validate_cmake_cache,
    validate_dynamic_dependencies,
)
from audio_poc.m4a_whispercpp_qualification import (  # noqa: E402
    NativeWhisperWorker,
    WorkerTimeout,
    summarize,
    validate_qualification_report,
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
            "poc_source_sha": "0" * 40,
            "candidate_id": PRIMARY_ID,
            "execution_status": "QUALITY_PASS_PERFORMANCE_FAIL_RETAINED",
            "summary": {"execution_complete": True},
            "cleanup": {"clean": True},
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
            "poc_source_sha": "0" * 40,
            "candidate_id": PRIMARY_ID,
            "execution_status": "QUALITY_PASS_PERFORMANCE_FAIL_RETAINED",
            "summary": {"execution_complete": True},
            "cleanup": {"clean": True},
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
            "poc_source_sha": "0" * 40,
            "candidate_id": PRIMARY_ID,
            "execution_status": "QUALITY_PERFORMANCE_PASS_PENDING_REVIEW_AND_LIFECYCLE",
            "summary": {"execution_complete": True},
            "cleanup": {"clean": True},
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

    def test_build_extracts_the_ack_prefixless_git_archive_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                for name, content in (
                    ("CMakeLists.txt", b"cmake_minimum_required(VERSION 3.16)\n"),
                    ("LICENSE", b"MIT\n"),
                    ("include/whisper.h", b"// pinned API\n"),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    bundle.addfile(info, io.BytesIO(content))
            destination = root / "extracted"
            self.assertEqual(safe_extract_source(archive, destination), destination)

    def test_cpu_only_build_command_contains_every_frozen_flag(self) -> None:
        command = configure_command(Path("/wrapper"), Path("/source"), Path("/build"))
        for name, value in CMAKE_FLAGS.items():
            self.assertIn(f"-D{name}={value}", command)
        self.assertIn("-DBUILD_SHARED_LIBS=OFF", command)
        self.assertIn("-DWHISPER_SOURCE_DIR=/source", command)

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

    def test_native_worker_source_freezes_ack_runtime_profile(self) -> None:
        source = (
            REPO_ROOT / "poc_audio/native/whispercpp_worker/worker.cpp"
        ).read_text(encoding="utf-8")
        for statement in (
            "constexpr int kThreads = 4;",
            "params.no_context = true;",
            "params.no_timestamps = true;",
            'params.language = "zh";',
            "params.temperature = 0.0F;",
            "params.temperature_inc = 0.0F;",
            "params.greedy.best_of = 1;",
            "params.vad = false;",
            "context_params.use_gpu = false;",
        ):
            self.assertIn(statement, source)

    def test_fake_persistent_worker_success_and_clean_quit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker = NativeWhisperWorker(
                [
                    sys.executable,
                    "-m",
                    "audio_poc.m4a_whispercpp_fake_worker",
                    "--model",
                    "fake.bin",
                ],
                Path(temporary) / "worker.stderr.log",
            )
            worker.start()
            first = worker.transcribe(Path(temporary) / "first.wav")
            second = worker.transcribe(Path(temporary) / "second.wav")
            self.assertEqual(first["hypothesis"], "今天外面的天氣很舒服")
            self.assertEqual(second["peak_rss_mib"], 100.0)
            cleanup = worker.stop()
            self.assertTrue(cleanup["clean"])
            self.assertEqual(cleanup["child_processes"], 0)

    def test_fake_persistent_worker_timeout_kills_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker = NativeWhisperWorker(
                [
                    sys.executable,
                    "-m",
                    "audio_poc.m4a_whispercpp_fake_worker",
                    "--model",
                    "fake.bin",
                ],
                Path(temporary) / "worker.stderr.log",
            )
            worker.start()
            with self.assertRaises(WorkerTimeout):
                worker.transcribe(Path(temporary) / "hang.wav", timeout_seconds=0.05)
            cleanup = worker.stop()
            self.assertTrue(cleanup["clean"])
            self.assertEqual(cleanup["child_processes"], 0)

    def test_fake_persistent_worker_force_abort_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker = NativeWhisperWorker(
                [
                    sys.executable,
                    "-m",
                    "audio_poc.m4a_whispercpp_fake_worker",
                    "--model",
                    "stubborn.bin",
                ],
                Path(temporary) / "stubborn.stderr.log",
            )
            worker.start()
            with self.assertRaises(WorkerTimeout):
                worker.transcribe(Path(temporary) / "hang.wav", timeout_seconds=0.05)
            cleanup = worker.stop()
            self.assertTrue(cleanup["clean"])
            self.assertTrue(cleanup["force_abort_used"])

            reopened = NativeWhisperWorker(
                [
                    sys.executable,
                    "-m",
                    "audio_poc.m4a_whispercpp_fake_worker",
                    "--model",
                    "fake.bin",
                ],
                Path(temporary) / "reopened.stderr.log",
            )
            reopened.start()
            self.assertEqual(
                reopened.transcribe(Path(temporary) / "reopened.wav")["hypothesis"],
                "今天外面的天氣很舒服",
            )
            self.assertTrue(reopened.stop()["clean"])

    def test_recovery_summary_applies_quality_latency_rtf_and_rss_gates(self) -> None:
        def result(cycle: int, fixture: int) -> dict[str, object]:
            return {
                "fixture_id": f"asr-{fixture:03d}",
                "category": "taiwan_mandarin",
                "latency_ms": 1600.0,
                "native_inference_ms": 1599.0,
                "cpu_ms": 3000.0,
                "peak_rss_mib": 1200.0,
                "audio_duration_seconds": 2.0,
                "rtf": 0.8,
                "reference_length": 10,
                "hypothesis_length": 10,
                "edit_distance": 0,
                "sentence_correct": True,
                "hypothesis_sha256": "0" * 64,
                "raw_transcript_emitted": False,
                "cycle": cycle,
            }

        cold = [
            {
                "terminal_status": "SUCCESS",
                "results": [result(1, fixture) for fixture in range(50)],
                "peak_rss_mib": 1200.0,
            }
            for _ in range(3)
        ]
        hot = {
            "terminal_status": "SUCCESS",
            "results": [
                result(cycle, fixture)
                for cycle in range(1, 21)
                for fixture in range(50)
            ],
            "peak_rss_mib": 1200.0,
        }
        summary = summarize({"cold": cold, "hot": hot})
        self.assertTrue(summary["execution_complete"])
        self.assertTrue(summary["quality"]["gate_pass"])
        self.assertFalse(summary["performance"]["latency_gate_pass"])
        self.assertTrue(summary["performance"]["rtf_gate_pass"])
        self.assertTrue(summary["determinism"]["gate_pass"])
        self.assertTrue(summary["q5_fallback_triggered"])

    def test_q5_review_must_bind_current_candidate_sha(self) -> None:
        result = {
            "report_id": "M4A-G1B-ASR-RECOVERY-QUALIFICATION",
            "review_status": "REVIEWED",
            "poc_source_sha": "0" * 40,
            "candidate_id": PRIMARY_ID,
            "execution_status": "QUALITY_PASS_PERFORMANCE_FAIL_RETAINED",
            "summary": {"execution_complete": True},
            "cleanup": {"clean": True},
            "quality": {
                "taiwan_mandarin_core_cer_percent": 10.0,
                "overall_sentence_correctness_percent": 90.0,
            },
            "performance": {
                "hot_final_transcript_p95_seconds": 1.6,
                "peak_rss_mib": 1000.0,
            },
        }
        with self.assertRaisesRegex(ValueError, "Candidate SHA"):
            q5_fallback_reason(result, "1" * 40)

    def test_qualification_validator_rejects_playback_claim(self) -> None:
        report = {
            "schema_version": "1.0",
            "report_id": "M4A-G1B-ASR-RECOVERY-QUALIFICATION",
            "review_status": "UNREVIEWED",
            "candidate_id": PRIMARY_ID,
            "method": {
                "threads": 4,
                "workers": 1,
                "warmups": 3,
                "cold_repetitions": 3,
                "hot_repetitions": 20,
                "hot_definition": "one_loaded_model_runs_fifty_fixtures_twenty_times",
                "percentile": "nearest_rank",
                "inference_timeout_seconds": 15.0,
            },
            "security": {
                "raw_transcript_emitted": False,
                "pcm_emitted": False,
                "audio_device_opened": False,
                "speaker_playback": True,
            },
            "summary": {"execution_complete": False, "quality": {"gate_pass": False}},
            "execution_status": "INCONCLUSIVE_RETAINED",
            "cleanup": {
                "child_processes": 0,
                "threads": 0,
                "iterators": 0,
                "streams": 0,
                "device_owners": 0,
                "clean": True,
            },
        }
        with self.assertRaisesRegex(ValueError, "security boundary"):
            validate_qualification_report(report)


if __name__ == "__main__":
    unittest.main()
