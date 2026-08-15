from __future__ import annotations

import array
import json
import sys
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "poc_audio/src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from audio_poc.harness import FakeProcessHarness, Scenario  # noqa: E402
from audio_poc.fixture_recorder import (  # noqa: E402
    CaptureItem,
    archive_existing_record,
    build_capture_items,
    load_plan,
    select_stage_items,
    sha256_file,
    validate_wav,
    verify_records,
)
from audio_poc.fixture_monitor import duplicate_channel_to_stereo  # noqa: E402
from audio_poc.fixture_review import review_collection  # noqa: E402
from audio_poc.fixture_labeler import propose_intervals  # noqa: E402
from audio_poc.fixture_label_review import _parse_override, _preview_ranges  # noqa: E402
from audio_poc.fixture_preflight import (  # noqa: E402
    MANIFEST_NAME as PREFLIGHT_MANIFEST_NAME,
    prepare_pilot,
)
from audio_poc.models import TerminalStatus  # noqa: E402
from audio_poc.option_a_fixtures import generate_fixtures  # noqa: E402
from audio_poc.option_a_conversion import (  # noqa: E402
    OptionAStreamConverter,
    ValidBitMapping,
    decode_s32_interleaved,
    float_to_s16le,
)
from audio_poc.option_a_live import LiveConfig, latency_summary, pcm_node  # noqa: E402
from audio_poc.option_a_valid_bits import analyze_fixture_directory  # noqa: E402
from audio_poc.option_a_validation import (  # noqa: E402
    P4_TEST_IDS,
    create_manifest,
    validate_manifest,
)
from audio_poc.validation import (  # noqa: E402
    validate_candidate_manifest,
    validate_fixture_catalog,
    validate_run_result,
)


class FakeHarnessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.harness = FakeProcessHarness("0" * 40)

    async def assert_scenario(
        self,
        scenario: Scenario,
        expected: TerminalStatus,
    ) -> None:
        result = await self.harness.run(scenario)
        self.assertEqual(result.terminal_status, expected)
        self.assertTrue(result.cleanup.clean)
        self.assertEqual(result.cleanup.child_processes, 0)
        validate_run_result(result.to_dict())

    async def test_success(self) -> None:
        await self.assert_scenario(
            Scenario("success", "success", timeout_seconds=0.5),
            TerminalStatus.SUCCESS,
        )

    async def test_declared_error(self) -> None:
        await self.assert_scenario(
            Scenario("error", "error", timeout_seconds=0.5),
            TerminalStatus.ERROR,
        )

    async def test_timeout(self) -> None:
        await self.assert_scenario(
            Scenario("timeout", "hang", timeout_seconds=0.08),
            TerminalStatus.TIMEOUT,
        )

    async def test_cancel(self) -> None:
        await self.assert_scenario(
            Scenario(
                "cancel",
                "hang",
                timeout_seconds=1.0,
                cancel_after_seconds=0.05,
            ),
            TerminalStatus.CANCELLED,
        )

    async def test_force_abort(self) -> None:
        result = await self.harness.run(
            Scenario("force_abort", "stubborn", timeout_seconds=0.08)
        )
        self.assertEqual(result.terminal_status, TerminalStatus.FORCE_ABORTED)
        self.assertTrue(result.force_abort_used)
        self.assertTrue(result.cleanup.clean)
        self.assertEqual(result.cleanup.child_processes, 0)
        validate_run_result(result.to_dict())


class TrackedDocumentTests(unittest.TestCase):
    def test_option_a_live_config_requires_p4_durations_and_direct_devices(self) -> None:
        with self.assertRaisesRegex(ValueError, "direct ALSA hw"):
            LiveConfig("default", "hw:0,0").validate()
        with self.assertRaisesRegex(ValueError, "at least 300"):
            LiveConfig("hw:0,0", "hw:0,0", duration_seconds=299).validate()
        with self.assertRaisesRegex(ValueError, "at least 10 for P4-A09"):
            LiveConfig("hw:0,0", "hw:0,0", warmup_cycles=9).validate()
        LiveConfig("hw:0,0", "hw:0,0").validate()

    def test_option_a_live_procfs_mapping_and_latency_summary_are_explicit(self) -> None:
        self.assertEqual(pcm_node("hw:0,0", "c"), Path("/proc/asound/card0/pcm0c/sub0/hw_params"))
        self.assertEqual(pcm_node("hw:1,2", "p"), Path("/proc/asound/card1/pcm2p/sub0/hw_params"))
        self.assertIsNone(pcm_node("plughw:0,0", "c"))
        self.assertEqual(latency_summary([])["p95_ms"], None)
        self.assertEqual(latency_summary([1.0, 2.0, 3.0])["p95_ms"], 3.0)

    def test_candidate_manifest_and_fixture_catalog(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "poc_audio/manifests/deterministic_fake.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (REPO_ROOT / "poc_audio/fixtures/catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validate_candidate_manifest(manifest, REPO_ROOT)
        validate_fixture_catalog(catalog, REPO_ROOT)

    def test_schema_documents_are_valid_json(self) -> None:
        for path in sorted((REPO_ROOT / "poc_audio/schemas").glob("*.json")):
            with self.subTest(path=path.name):
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_option_a_packet_starts_with_all_hardware_results_pending(self) -> None:
        config_path = REPO_ROOT / "poc_audio/config/option_a.sanitized.json"
        manifest = create_manifest(
            REPO_ROOT,
            "0" * 40,
            "M1-P4-TEST",
            config_path,
        )
        validate_manifest(manifest, REPO_ROOT)
        self.assertEqual(
            [item["test_id"] for item in manifest["tests"]],
            list(P4_TEST_IDS),
        )
        self.assertTrue(all(item["status"] == "Pending" for item in manifest["tests"]))
        self.assertTrue(all(item["cleanup"]["clean"] is None for item in manifest["tests"]))
        self.assertEqual(
            {item["source_sha256"] for item in manifest["candidates"]},
            {
                "a78a9dca33524b2c9064b34e21f5ab874272313cf324a9a77592f396a5e0fddc",
                "c44dcb6fe680246f8f36588ba1f0fc7a0c5fbce710ad5e9b3812d88e8c39ac7d",
            },
        )

    def test_option_a_fixture_generation_is_deterministic(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = generate_fixtures(root / "first")
            second = generate_fixtures(root / "second")
        self.assertEqual(len(first["fixtures"]), 6)
        self.assertEqual(
            [item["sha256"] for item in first["fixtures"]],
            [item["sha256"] for item in second["fixtures"]],
        )
        self.assertTrue(all(item["sample_count"] == 48000 for item in first["fixtures"]))

    def test_option_a_valid_bit_decode_is_explicit(self) -> None:
        import numpy

        left = numpy.array(
            [[0x40000000, 0], [-0x40000000, 0]],
            dtype="<i4",
        ).tobytes()
        decoded_left = decode_s32_interleaved(
            left,
            ValidBitMapping(channel_index=0, valid_bits=24, alignment="left"),
            numpy,
        )
        numpy.testing.assert_allclose(decoded_left, [0.5, -0.5])

        right = numpy.array([[0, 0x00400000], [0, 0x00C00000]], dtype="<i4").tobytes()
        decoded_right = decode_s32_interleaved(
            right,
            ValidBitMapping(channel_index=1, valid_bits=24, alignment="right"),
            numpy,
        )
        numpy.testing.assert_allclose(decoded_right, [0.5, -0.5])

    def test_option_a_valid_bit_analyzer_reports_no_raw_audio(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wav_path = root / "asr-clear-001.wav"
            with wave.open(str(wav_path), "wb") as generated:
                generated.setnchannels(2)
                generated.setsampwidth(4)
                generated.setframerate(48000)
                for value in range(256):
                    generated.writeframesraw(
                        (((1 << 16) + value) << 8).to_bytes(4, "little", signed=True)
                        + (0).to_bytes(4, "little", signed=True)
                    )
            (root / "fixture_manifest.json").write_text(
                json.dumps(
                    {
                        "source_sha": "0" * 40,
                        "authorization_confirmed": True,
                        "records": {
                            "asr-clear-001": {
                                "file": wav_path.name,
                                "vad_class": "clear_speech",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = analyze_fixture_directory(root, root / "analysis.json")
        self.assertEqual(result["result"], "PASS")
        self.assertTrue(result["mapping_supported_by_raw_analysis"])
        self.assertEqual(result["supported_mapping"]["valid_bits"], 24)
        self.assertEqual(result["channels"][0]["container_low8_or"], 0)
        self.assertEqual(result["channels"][0]["decoded_low8_or"], 255)
        self.assertEqual(result["channels"][1]["nonzero_samples"], 0)
        self.assertFalse(result["raw_audio_emitted"])

    def test_option_a_s16_conversion_saturates_without_wrap(self) -> None:
        import numpy

        converted = numpy.frombuffer(
            float_to_s16le(numpy.array([-2.0, -1.0, 0.0, 1.0, 2.0]), numpy),
            dtype="<i2",
        )
        self.assertEqual(converted.tolist(), [-32768, -32768, 0, 32767, 32767])

    def test_option_a_stream_preserves_partial_container_and_exact_frames(self) -> None:
        import numpy

        class FakeThirdRateResampler:
            def __init__(self) -> None:
                self.remainder = numpy.empty(0, dtype=numpy.float32)

            def process(self, values, ratio, end_of_input=False):
                self.assert_ratio = ratio
                combined = numpy.concatenate((self.remainder, values))
                complete = (combined.size // 3) * 3
                output = combined[:complete:3].copy()
                self.remainder = combined[complete:].copy()
                if end_of_input and self.remainder.size:
                    raise AssertionError("test input must have an exact 3:1 ratio")
                return output

        containers = numpy.zeros((960, 2), dtype="<i4")
        containers[:, 0] = (
            numpy.arange(960, dtype=numpy.int64).clip(max=(1 << 23) - 1) << 8
        ).astype("<i4")
        raw = containers.tobytes()
        converter = OptionAStreamConverter(
            ValidBitMapping(channel_index=0, valid_bits=24, alignment="left"),
            numpy_module=numpy,
            resampler_factory=FakeThirdRateResampler,
        )
        frames = []
        for start in range(0, len(raw), 317):
            frames.extend(converter.feed(raw[start : start + 317]))
        flushed = converter.flush()
        frames.extend(flushed.frames)
        self.assertEqual(converter.total_input_samples, 960)
        self.assertEqual(converter.total_resampled_samples, 320)
        self.assertEqual(len(frames), 1)
        self.assertEqual(len(frames[0]), 640)
        self.assertEqual(flushed.partial_pcm, b"")
        self.assertEqual(converter.drain_input_samples, 0)

        converter.reset()
        self.assertEqual(converter.total_input_samples, 0)
        self.assertEqual(converter.feed(b"\x00"), ())
        with self.assertRaisesRegex(ValueError, "incomplete interleaved container"):
            converter.flush()

    def test_option_a_flush_drains_filter_to_exact_ratio(self) -> None:
        import numpy

        class DelayedThirdRateResampler:
            def __init__(self) -> None:
                self.first = True

            def process(self, values, ratio, end_of_input=False):
                if self.first:
                    self.first = False
                    self.assert_input = values.size
                    return numpy.zeros((values.size // 3) - 2, dtype=numpy.float32)
                self.assert_drain = values.size
                self.assert_final = end_of_input
                return numpy.zeros(values.size // 3, dtype=numpy.float32)

        raw = numpy.zeros((960, 2), dtype="<i4").tobytes()
        converter = OptionAStreamConverter(
            ValidBitMapping(channel_index=0, valid_bits=24, alignment="left"),
            numpy_module=numpy,
            resampler_factory=DelayedThirdRateResampler,
        )
        frames = list(converter.feed(raw))
        flushed = converter.flush()
        frames.extend(flushed.frames)
        self.assertEqual(converter.drain_input_samples, 6)
        self.assertEqual(converter.total_resampled_samples, 320)
        self.assertEqual(len(frames), 1)
        self.assertEqual(flushed.partial_pcm, b"")

    def test_option_a_pass_requires_zero_cleanup_counters(self) -> None:
        config_path = REPO_ROOT / "poc_audio/config/option_a.sanitized.json"
        manifest = create_manifest(REPO_ROOT, "0" * 40, "M1-P4-TEST", config_path)
        manifest["tests"][0]["status"] = "PASS"
        manifest["tests"][0]["command"] = "test-command"
        manifest["tests"][0]["raw_artifact_paths"] = ["raw/a01.json"]
        with self.assertRaisesRegex(ValueError, "PASS requires clean cleanup proof"):
            validate_manifest(manifest, REPO_ROOT)

        manifest["tests"][0]["cleanup"] = {
            "tasks": 0,
            "threads": 0,
            "file_descriptors": 0,
            "alsa_owners": 0,
            "clean": True,
        }
        validate_manifest(manifest, REPO_ROOT)

    def test_option_a_pass_requires_command_and_raw_evidence(self) -> None:
        config_path = REPO_ROOT / "poc_audio/config/option_a.sanitized.json"
        manifest = create_manifest(REPO_ROOT, "0" * 40, "M1-P4-TEST", config_path)
        manifest["tests"][0]["status"] = "PASS"
        manifest["tests"][0]["cleanup"] = {
            "tasks": 0,
            "threads": 0,
            "file_descriptors": 0,
            "alsa_owners": 0,
            "clean": True,
        }
        with self.assertRaisesRegex(ValueError, "PASS requires command and raw evidence"):
            validate_manifest(manifest, REPO_ROOT)

    def test_option_a_manifest_rejects_artifact_path_escape(self) -> None:
        config_path = REPO_ROOT / "poc_audio/config/option_a.sanitized.json"
        manifest = create_manifest(REPO_ROOT, "0" * 40, "M1-P4-TEST", config_path)
        manifest["runner"]["path"] = "../outside"
        with self.assertRaisesRegex(ValueError, "artifact path escapes repository"):
            validate_manifest(manifest, REPO_ROOT)

    def test_option_a_manifest_detects_tracked_artifact_changes(self) -> None:
        config_path = REPO_ROOT / "poc_audio/config/option_a.sanitized.json"
        manifest = create_manifest(REPO_ROOT, "0" * 40, "M1-P4-TEST", config_path)
        manifest["runner"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "artifact checksum mismatch: runner"):
            validate_manifest(manifest, REPO_ROOT)

    def test_authorized_recording_plan_is_complete_but_not_candidate_ready(self) -> None:
        plan = json.loads(
            (
                REPO_ROOT
                / "poc_audio/fixtures/authorized/recording_plan_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(plan["authorization_status"], "authorized_by_user_designer")
        self.assertFalse(plan["audio_git_tracked"])
        self.assertFalse(plan["candidate_ready"])

        set_counts = {item["class"]: item["count"] for item in plan["sets"]}
        self.assertEqual(
            set_counts,
            {"clear_speech": 25, "pause": 25, "silence": 25, "noise": 25},
        )
        non_speech_seconds = sum(
            item["count"] * item["duration_seconds_each"]
            for item in plan["sets"]
            if item["class"] in {"silence", "noise"}
        )
        self.assertGreaterEqual(non_speech_seconds, 600)

        utterances = plan["utterances"]
        self.assertEqual(len(utterances), 50)
        self.assertEqual(len({item["fixture_id"] for item in utterances}), 50)
        self.assertEqual(
            sum(item["vad_class"] == "clear_speech" for item in utterances), 25
        )
        self.assertEqual(sum(item["vad_class"] == "pause" for item in utterances), 25)
        self.assertTrue(all(item["reference_text"] for item in utterances))

        pilot, formal = plan["collection_stages"]
        self.assertEqual(pilot["stage_id"], "pilot")
        self.assertEqual(pilot["expected_count"], 40)
        self.assertEqual(len(pilot["speech_fixture_ids"]), 20)
        self.assertEqual(len(set(pilot["speech_fixture_ids"])), 20)
        self.assertEqual(formal["stage_id"], "formal")
        self.assertEqual(formal["expected_count"], 100)
        self.assertEqual(formal["remaining_after_pilot"], 60)
        items = build_capture_items(plan)
        self.assertEqual(len(select_stage_items(plan, items, "pilot")), 40)
        self.assertEqual(len(select_stage_items(plan, items, "formal")), 60)

    def test_fixture_recorder_validates_a_complete_local_manifest(self) -> None:
        plan_path = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
        plan = load_plan(plan_path)
        for capture_set in plan["sets"]:
            capture_set["duration_seconds_each"] = 1
        plan["_path"] = str(plan_path)
        items = build_capture_items(plan)
        self.assertEqual(len(items), 100)

        with self.subTest("native wav metadata"):
            import tempfile

            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                records = {}
                for item in items:
                    wav_path = root / f"{item.fixture_id}.wav"
                    with wave.open(str(wav_path), "wb") as generated:
                        generated.setnchannels(2)
                        generated.setsampwidth(4)
                        generated.setframerate(48000)
                        generated.writeframes(b"\x00" * (48000 * 2 * 4))
                    metadata = validate_wav(wav_path, plan["native_capture"])
                    records[item.fixture_id] = {
                        "fixture_id": item.fixture_id,
                        "vad_class": item.vad_class,
                        "category": item.category,
                        "file": wav_path.name,
                        "sha256": sha256_file(wav_path),
                        "metadata": metadata,
                    }
                (root / "fixture_manifest.json").write_text(
                    json.dumps(
                        {
                            "schema_version": "1.0",
                            "plan_id": plan["plan_id"],
                            "plan_sha256": sha256_file(plan_path),
                            "authorization_confirmed": True,
                            "native_capture": plan["native_capture"],
                            "records": records,
                        }
                    ),
                    encoding="utf-8",
                )
                outcome = verify_records(plan, root)
                self.assertEqual(outcome["summary"]["result"], "PASS")
                self.assertEqual(outcome["summary"]["valid_files"], 100)
                self.assertEqual(outcome["summary"]["non_speech_seconds"], 50)

    def test_fixture_review_uses_formal_complement_and_keeps_content_human_review(self) -> None:
        import tempfile

        plan_path = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
        plan = load_plan(plan_path)
        for capture_set in plan["sets"]:
            capture_set["duration_seconds_each"] = 1
        plan["_path"] = str(plan_path)
        items = build_capture_items(plan)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review_plan_path = root / "plan.json"
            review_plan_path.write_text(json.dumps(plan), encoding="utf-8")
            records = {}
            for item in items:
                wav_path = root / f"{item.fixture_id}.wav"
                with wave.open(str(wav_path), "wb") as generated:
                    generated.setnchannels(2)
                    generated.setsampwidth(4)
                    generated.setframerate(48000)
                    generated.writeframes(
                        (
                            (123456).to_bytes(4, "little", signed=True)
                            + (0).to_bytes(4, "little", signed=True)
                        )
                        * 48000
                    )
                records[item.fixture_id] = {
                    "fixture_id": item.fixture_id,
                    "file": wav_path.name,
                    "vad_class": item.vad_class,
                    "metadata": validate_wav(wav_path, plan["native_capture"]),
                    "sha256": sha256_file(wav_path),
                }
            (root / "fixture_manifest.json").write_text(json.dumps({
                "plan_id": plan["plan_id"], "native_capture": plan["native_capture"], "records": records,
            }), encoding="utf-8")
            review = review_collection(review_plan_path, root, "formal")
            self.assertEqual(review["reviewed_fixture_count"], 60)
            self.assertEqual(review["result"], "PASS")
            self.assertEqual(len(review["stratified_sample"]), 14)
            self.assertEqual(review["semantic_content_review"], "requires_authorized_human_listener")

    def test_fixture_labeler_proposes_two_intervals_and_a_pause_without_claiming_ground_truth(self) -> None:
        samples = array.array("i", [0] * 4800)
        samples.extend([500_000_000] * 9600)
        samples.extend([0] * 9600)
        samples.extend([500_000_000] * 9600)
        samples.extend([0] * 4800)
        proposal = propose_intervals(samples, 48000)
        self.assertEqual(proposal["method"], "energy_assisted_proposal_requires_human_review")
        self.assertEqual(proposal["utterance_interval_ms"], [100, 700])
        self.assertEqual(proposal["largest_internal_pause_candidate_ms"], [300, 500])

    def test_label_review_accepts_only_valid_class_specific_overrides(self) -> None:
        clear = {"class": "clear_speech", "speech_intervals_ms": [[100, 900]]}
        pause = {"class": "pause", "speech_intervals_ms": [[100, 400], [800, 1200]], "internal_pause_candidate_ms": [400, 800]}
        self.assertEqual(_parse_override("120,880", clear), ([[120, 880]], None))
        self.assertEqual(_parse_override("100,450,820,1200", pause), ([[100, 450], [820, 1200]], [450, 820]))
        self.assertEqual(len(_preview_ranges(pause)), 3)
        with self.assertRaises(ValueError):
            _parse_override("120,880", pause)

    def test_monitor_duplicates_the_requested_channel_without_gain(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            destination = root / "monitor.wav"
            with wave.open(str(source), "wb") as generated:
                generated.setnchannels(2)
                generated.setsampwidth(4)
                generated.setframerate(48000)
                generated.writeframes((123456).to_bytes(4, "little", signed=True))
                generated.writeframes((-654321).to_bytes(4, "little", signed=True))
            duplicate_channel_to_stereo(source, destination, 0)
            with wave.open(str(destination), "rb") as monitored:
                payload = monitored.readframes(1)
            left = int.from_bytes(payload[:4], "little", signed=True)
            right = int.from_bytes(payload[4:], "little", signed=True)
            self.assertEqual((left, right), (123456, 123456))

    def test_monitor_reports_saturation_when_gain_would_clip(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.wav"
            destination = root / "monitor.wav"
            with wave.open(str(source), "wb") as generated:
                generated.setnchannels(2)
                generated.setsampwidth(4)
                generated.setframerate(48000)
                generated.writeframes((2_000_000_000).to_bytes(4, "little", signed=True))
                generated.writeframes((0).to_bytes(4, "little", signed=True))
            metadata = duplicate_channel_to_stereo(source, destination, 0, 12.0)
            self.assertEqual(metadata["clipped_source_samples"], 1)
            with wave.open(str(destination), "rb") as monitored:
                payload = monitored.readframes(1)
            self.assertEqual(int.from_bytes(payload[:4], "little", signed=True), 2147483647)

    def test_replacement_archives_the_previous_raw_recording(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "vad-silence-001.wav"
            source.write_bytes(b"prior raw audio")
            item = CaptureItem("vad-silence-001", "silence", "silence", 12)
            manifest = {"records": {item.fixture_id: {"file": source.name}}}
            archived_file = archive_existing_record(item, root, manifest)
            self.assertIsNotNone(archived_file)
            self.assertFalse(source.exists())
            self.assertTrue((root / str(archived_file)).is_file())
            self.assertNotIn(item.fixture_id, manifest["records"])
            self.assertEqual(
                manifest["superseded_records"][0]["reason"],
                "operator_requested_replace",
            )

    def test_pilot_preflight_creates_complete_16k_mono_revision(self) -> None:
        import tempfile

        plan_path = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
        plan = load_plan(plan_path)
        for capture_set in plan["sets"]:
            capture_set["duration_seconds_each"] = 1
        plan["_path"] = str(plan_path)
        pilot_items = select_stage_items(plan, build_capture_items(plan), "pilot")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native_dir = root / "native"
            native_dir.mkdir()
            records = {}
            for item in pilot_items:
                wav_path = native_dir / f"{item.fixture_id}.wav"
                with wave.open(str(wav_path), "wb") as generated:
                    generated.setnchannels(2)
                    generated.setsampwidth(4)
                    generated.setframerate(48000)
                    generated.writeframes(
                        (100_000_000).to_bytes(4, "little", signed=True)
                        + (0).to_bytes(4, "little", signed=True)
                    )
                    generated.writeframes(b"\x00" * (47999 * 2 * 4))
                records[item.fixture_id] = {
                    "fixture_id": item.fixture_id,
                    "vad_class": item.vad_class,
                    "category": item.category,
                    "file": wav_path.name,
                    "sha256": sha256_file(wav_path),
                    "metadata": validate_wav(wav_path, plan["native_capture"]),
                }
            (native_dir / "fixture_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "plan_id": plan["plan_id"],
                        "plan_sha256": sha256_file(plan_path),
                        "authorization_confirmed": True,
                        "native_capture": plan["native_capture"],
                        "source_sha": "0" * 40,
                        "records": records,
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "preflight"
            result = prepare_pilot(
                plan, plan_path, native_dir, output_dir, REPO_ROOT, replace=False
            )
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["valid_files"], 40)
            document = json.loads(
                (output_dir / PREFLIGHT_MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(document["gate_effect"], "observation_only_no_advance_reject_or_winner")
            self.assertEqual(len(document["records"]), 40)
            with wave.open(str(output_dir / "asr-clear-001.wav"), "rb") as derived:
                self.assertEqual((derived.getframerate(), derived.getnchannels(), derived.getsampwidth()), (16000, 1, 2))
                self.assertEqual(derived.getnframes(), 16000)

    def test_fixture_delivery_prepares_option_a_delivered_revision(self) -> None:
        import tempfile
        from audio_poc.fixture_delivery import prepare as prepare_delivered, MANIFEST_NAME as DELIVERED_MANIFEST_NAME

        plan_path = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
        plan = load_plan(plan_path)
        for capture_set in plan["sets"]:
            capture_set["duration_seconds_each"] = 1
        plan["_path"] = str(plan_path)
        items = build_capture_items(plan)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native_dir = root / "native"
            native_dir.mkdir()
            records = {}
            for item in items:
                wav_path = native_dir / f"{item.fixture_id}.wav"
                with wave.open(str(wav_path), "wb") as generated:
                    generated.setnchannels(2)
                    generated.setsampwidth(4)
                    generated.setframerate(48000)
                    generated.writeframes(
                        (100_000_000).to_bytes(4, "little", signed=True)
                        + (0).to_bytes(4, "little", signed=True)
                    )
                    generated.writeframes(b"\x00" * (47999 * 2 * 4))
                records[item.fixture_id] = {
                    "fixture_id": item.fixture_id,
                    "vad_class": item.vad_class,
                    "category": item.category,
                    "file": wav_path.name,
                    "sha256": sha256_file(wav_path),
                    "metadata": validate_wav(wav_path, plan["native_capture"]),
                }
            (native_dir / "fixture_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "plan_id": plan["plan_id"],
                        "plan_sha256": sha256_file(plan_path),
                        "authorization_confirmed": True,
                        "native_capture": plan["native_capture"],
                        "source_sha": "0" * 40,
                        "records": records,
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "delivered"
            result = prepare_delivered(plan_path, native_dir, output_dir)
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["valid_files"], 100)
            manifest = json.loads((output_dir / DELIVERED_MANIFEST_NAME).read_text(encoding="utf-8"))
            self.assertEqual(manifest["delivered_pcm"]["sample_rate_hz"], 16000)
            self.assertEqual(manifest["delivered_pcm"]["channels"], 1)
            self.assertEqual(manifest["delivered_pcm"]["sample_format"], "S16_LE")
            self.assertEqual(len(manifest["records"]), 100)
            with wave.open(str(output_dir / "asr-clear-001.wav"), "rb") as derived:
                self.assertEqual((derived.getframerate(), derived.getnchannels(), derived.getsampwidth()), (16000, 1, 2))
                self.assertEqual(derived.getnframes(), 16000)


if __name__ == "__main__":
    unittest.main()

