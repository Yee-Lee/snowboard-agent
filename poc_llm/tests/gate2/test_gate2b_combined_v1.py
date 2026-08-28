from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

from jsonschema import Draft202012Validator

from poc_llm.harness.gate2b_combined_v1 import Gate2BCombinedCoordinator
from poc_llm.harness.gate2b_resources_v1 import evaluate_resources, process_tree
from poc_llm.tools.run_gate2b_pi_v1 import (
    CombinedLlmDomain,
    combined_exception_disposition,
    main as gate2b_main,
    verify_external_checkouts,
    verify_gate2a_entry,
    verify_audio_kit,
    valid_run_id as valid_gate2b_run_id,
)


ROOT = Path(__file__).resolve().parents[3]
AUDIO_ENTRY = ROOT / "poc_llm/fixtures/gate2/accepted-audio-entry-001.json"
AUDIO_SCHEMA = ROOT / "poc_llm/evidence/m4b/accepted-audio-entry-v1.schema.json"
G2A_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate2a-provisional-receipt-v1.schema.json"
G2B_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate2b-pi-v1-result.schema.json"
G2B_RUNNER = ROOT / "poc_llm/tools/run_gate2b_pi_v1.py"
G2B_LOCK = ROOT / "poc_llm/harness/gate2b-pi-lock-v1.json"


class Domain:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.events = events
        self.alive = False
        self.pid = {"vad":101,"asr":102,"tts":103,"llm":104}[name]
        self.inputs: list[dict] = []

    async def start(self) -> None:
        self.events.append(f"start:{self.name}")
        self.alive = True

    async def stop(self) -> None:
        self.events.append(f"stop:{self.name}")
        self.alive = False

    def residency_identity(self) -> dict:
        return {"pid": self.pid, "alive": self.alive}


class Vad(Domain):
    async def run(self, session: dict) -> dict:
        return {
            "session_id":session["session_id"], "terminal":"SUCCESS",
            "bounded_wav":session["wav_path"], "bounded_sha256":"a" * 64,
        }


class Asr(Domain):
    async def run(self, session: dict) -> dict:
        transcript = f"private transcript {session['session_id']}"
        return {
            "session_id":session["session_id"], "terminal":"SUCCESS",
            "transcript":transcript,
            "transcript_sha256":hashlib.sha256(transcript.encode()).hexdigest(),
            "latency_ms":1.0,
        }


class Llm(Domain):
    async def run(self, session_id: str, transcript: str, nonce: str, trap: str) -> dict:
        self.inputs.append({"session_id":session_id,"transcript":transcript,"nonce":nonce,"trap":trap})
        speech = f"private speech {session_id}"
        return {
            "session_id":session_id, "terminal":"SUCCESS", "request_id":session_id,
            "speech_text":speech,
            "speech_sha256":hashlib.sha256(speech.encode()).hexdigest(),
            "response_sha256":"b" * 64, "prior_marker_leaked":False,
            "current_marker_present_once":True, "current_trap_absent":True,
            "metrics":{"ttft_ms":1.0,"decode_tokens_per_second":10.0,"kv_tokens":10},
        }


class Tts(Domain):
    async def run(self, session: dict) -> dict:
        self.inputs.append(session)
        return {
            "session_id":session["session_id"], "terminal":"SUCCESS",
            "pcm_sha256":"c" * 64, "sample_count":10, "playback_complete":True,
        }


def records() -> list[dict]:
    return [
        {
            "session_id":f"M4-SESSION-{index:02d}", "fixture_id":f"asr-{index:03d}",
            "tts_fixture_id":f"tts-{index:03d}", "filename":f"{index}.wav",
            "sha256":"d" * 64, "wav_path":Path(f"/{index}.wav"),
        }
        for index in range(1, 21)
    ]


def valid_result_session(index: int) -> dict:
    session_id = f"M4-SESSION-{index:02d}"
    return {
        "session_id":session_id,"audio_fixture_id":f"asr-{index:03d}",
        "tts_fixture_id":f"tts-{index:03d}",
        "vad":{"terminal":"SUCCESS","bounded_sha256":"a"*64},
        "asr":{"terminal":"SUCCESS","transcript_sha256":"b"*64,"latency_ms":1.0},
        "llm":{"terminal":"SUCCESS","request_id":session_id,"response_sha256":"c"*64,
               "speech_sha256":"d"*64,"prior_marker_leaked":False,
               "current_marker_present_once":True,"current_trap_absent":True,
               "metrics":{"kv_tokens":10}},
        "tts":{"terminal":"SUCCESS","pcm_sha256":"e"*64,"sample_count":10,
               "playback_complete":True,"input_speech_sha256":"d"*64},
        "timings_ms":{"vad":1.0,"asr":1.0,"llm":1.0,"tts_playback":1.0,"end_to_end":4.0},
    }


class Gate2BCombinedTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_pipeline_keeps_private_text_in_memory_and_stops_reverse(self) -> None:
        events: list[str] = []
        pauses: list[float] = []

        async def pause(value: float) -> None:
            pauses.append(value)

        vad, asr, tts, llm = Vad("vad", events), Asr("asr", events), Tts("tts", events), Llm("llm", events)
        coordinator = Gate2BCombinedCoordinator(vad, asr, llm, tts, pause=pause)
        hooks: list[str] = []
        result = await coordinator.run(
            records(), cadence_s=5.0,
            on_resident=lambda: hooks.append("resident"),
            before_shutdown=lambda: hooks.append("sample-stop"),
        )
        self.assertEqual(len(result), 20)
        self.assertEqual(events[:4], ["start:vad","start:asr","start:tts","start:llm"])
        self.assertEqual(events[-4:], ["stop:llm","stop:tts","stop:asr","stop:vad"])
        self.assertEqual(hooks, ["resident","sample-stop"])
        self.assertEqual(pauses, [5.0] * 19)
        self.assertEqual(len(llm.inputs), 20)
        self.assertEqual(len(tts.inputs), 20)
        self.assertEqual(
            hashlib.sha256(tts.inputs[0]["failure_text"].encode()).hexdigest(),
            tts.inputs[0]["llm_speech_sha256"],
        )
        serialized = json.dumps(result)
        self.assertNotIn("private transcript", serialized)
        self.assertNotIn("private speech", serialized)

    async def test_duplicate_session_identity_fails_before_start(self) -> None:
        values = records()
        values[1]["session_id"] = values[0]["session_id"]

        async def pause(_value: float) -> None:
            pass

        events: list[str] = []
        coordinator = Gate2BCombinedCoordinator(
            Vad("vad", events), Asr("asr", events), Llm("llm", events),
            Tts("tts", events), pause=pause,
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            await coordinator.run(values)
        self.assertEqual(events, [])


class Gate2BDefinitionTests(unittest.TestCase):
    def test_run_id_is_single_safe_slug(self) -> None:
        self.assertTrue(valid_gate2b_run_id("G2B-PI-COMBINED-001"))
        for value in ("../escape", "/tmp/escape", "nested/run", "", "a" * 129):
            self.assertFalse(valid_gate2b_run_id(value))

    def test_combined_session_failure_is_fail_not_infrastructure_inconclusive(self) -> None:
        p_results, result = combined_exception_disposition(
            combined_entered=True, sessions_completed=False
        )
        self.assertEqual(p_results, {"P9":"Blocked","P10B":"FAIL"})
        self.assertEqual(result, "FAIL")
        p_results, result = combined_exception_disposition(
            combined_entered=False, sessions_completed=False
        )
        self.assertEqual(p_results, {"P9":"Blocked","P10B":"Blocked"})
        self.assertEqual(result, "INCONCLUSIVE")

    def test_gate2b_lock_authenticates_repository_surface(self) -> None:
        lock = json.loads(G2B_LOCK.read_text())
        self.assertEqual(lock["packet_id"], "G2B-PI-COMBINED-001")
        self.assertEqual(lock["fault_schedule"], [])
        self.assertEqual(lock["session_count"], 20)
        for item in lock["artifacts"].values():
            path = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)
        for candidate in lock["candidates"].values():
            for item in candidate.values():
                path = ROOT / item["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"], path)

    def test_accepted_audio_entry_is_exact_and_schema_valid(self) -> None:
        entry = json.loads(AUDIO_ENTRY.read_text())
        validator = Draft202012Validator(json.loads(AUDIO_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(entry))
        self.assertEqual(entry["tag"], "audio_m4")
        self.assertEqual(entry["tag_object_sha"], "24b2571a23dde2f77027242b61142b0c1a59924c")
        self.assertEqual(entry["status"], "POC_ACCEPTED_M4_COMPLETE")

    def test_external_audio_tag_and_completion_are_distinct_exact_identities(self) -> None:
        accepted = json.loads(AUDIO_ENTRY.read_text())
        audio = Path("/audio")
        core = Path("/core")

        def output(root: Path, *args: str) -> str:
            key = (str(root), args)
            values = {
                (str(audio), ("rev-parse", "HEAD")): accepted["completion_sha"],
                (str(audio), ("status", "--porcelain")): "",
                (str(audio), ("rev-parse", f"refs/tags/{accepted['tag']}")): accepted["tag_object_sha"],
                (str(audio), ("rev-list", "-n", "1", accepted["tag"])): accepted["completion_sha"],
                (str(core), ("rev-parse", "HEAD")): accepted["core_hal_execution_sha"],
                (str(core), ("status", "--porcelain")): "",
            }
            return values[key]

        with patch("poc_llm.tools.run_gate2b_pi_v1.git_output", side_effect=output):
            observed = verify_external_checkouts(audio, core, accepted)
            self.assertEqual(observed["audio_tag_object_sha"], accepted["tag_object_sha"])
            drift = {**accepted, "tag_object_sha":"f" * 40}
            with self.assertRaisesRegex(Exception, "Audio checkout identity"):
                verify_external_checkouts(audio, core, drift)

    def test_gate2a_receipt_requires_qwen_written_workaround(self) -> None:
        value = {
            "receipt_version":"gate2a-provisional/1", "packet_id":"G2A-PI-LLM-002",
            "candidate_id":"CAND-LRT-Q25-15B-Q8-R1",
            "candidate_disposition":"USER_CORE_DEFECT_WAIVER",
            "execution_sha":"a"*40, "execution_surface_sha256":"b"*64,
            "gate2a_lock_sha256":"c"*64, "candidate_result_sha256":"d"*64,
            "artifact_receipt_sha256":"e"*64, "gate1_entry_sha256":"f"*64,
            "p_results":{"P1":"PASS","P2":"PASS","P3":"PASS","P4":"PASS","P5":"PASS","P6.1":"PASS","P7.1":"FAIL","P8":"PASS","P10A":"PASS","P11":"PASS","P12":"PASS"},
            "user_review":{"approved":True,"review_id":"USER-G2A-001"},
            "core_ack_id":None,"core_ack_required_before_final_delivery":True,
            "p4_threshold_decision":None,
            "workaround":{"disposition":"restart child before next turn","accepted_by_user":True,"accepted_by_core":True,"user_decision_id":"USER-QWEN-001","core_decision_id":"CORE-QWEN-001"},
            "result":"PASS",
        }
        validator = Draft202012Validator(json.loads(G2A_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(value))
        value["workaround"]["accepted_by_core"] = False
        self.assertFalse(validator.is_valid(value))
        value["workaround"]["accepted_by_core"] = True
        value["p_results"]["P7.1"] = "PASS"
        self.assertFalse(validator.is_valid(value))

    def test_gate2a_receipt_is_bound_to_actual_reviewed_result(self) -> None:
        lock_sha = hashlib.sha256((ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json").read_bytes()).hexdigest()
        artifact_sha = "e" * 64
        result = {
            "packet_id":"G2A-PI-LLM-002","run_id":"run",
            "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1","execution_sha":"a"*40,
            "execution_surface_sha256":lock_sha,"gate1_entry":{},"isolation":{},
            "environment":{},"environment_post":{},"runtime":{},
            "artifact_authentication":{"reused_receipt_sha256":artifact_sha,
                "model_sha256":"d"*64,"model_size_bytes":1,
                "full_model_hash_count":0,"metadata_unchanged":True},
            "carried_results":{"P1":"PASS","P6.1":"PASS","P7.1":"PASS","P10A":"PASS","P11":"PASS","P12":"PASS"},
            "executed_results":{"P2":"PASS","P3":"PASS","P4":"PASS","P5":"PASS","P8":"PASS"},
            "samples":{
                "p2":{"ready_ms":1.0,"cases":[{} for _ in range(30)],"error_type":None},
                "p3":[{} for _ in range(10)],
                "p4":{"resident_ready_ms":1.0,"cold":[{} for _ in range(3)],
                      "warmups":[{} for _ in range(3)],"hot":[{} for _ in range(20)],
                      "summary":{str(index):index for index in range(7)},"failures":[]},
                "p5":{"ready_ms":1.0,"terminal":"ERROR","code":"TIMEOUT","elapsed_ms":15000.0,
                      "observation_error_type":None,"marker_counts":{},"same_child_pong":"PONG",
                      "same_child_health_terminal":"RESULT","rebuild_ready_ms":1.0,
                      "rebuild_health_terminal":"RESULT","rebuild_error_type":None},
                "p8":{"ready_ms":1.0,"cases":[{} for _ in range(5)],"error_type":None},
            },
            "cleanup":{
                name:{"exit_code":0,"waited":True,"term_sent":False,
                      "kill_sent":False,"process_group_absent":True}
                for name in ("p2","standard","p8","p5_same_child","p5_rebuild")
            },"violations":[],"gate2a_scope_result":"PASS",
            "provisional_eligibility":"ELIGIBLE_FOR_USER_REVIEW","result":"PASS",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "gate2a.json"
            result_path.write_text(json.dumps(result, sort_keys=True))
            gate1_entry = ROOT / "poc_llm/fixtures/gate2/gate1-closure-entry-001.json"
            receipt = {
                "receipt_version":"gate2a-provisional/1","packet_id":"G2A-PI-LLM-002",
                "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1","candidate_disposition":"NORMAL_FINALIST",
                "execution_sha":"a"*40,"execution_surface_sha256":lock_sha,
                "gate2a_lock_sha256":lock_sha,
                "candidate_result_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest(),
                "artifact_receipt_sha256":artifact_sha,
                "gate1_entry_sha256":hashlib.sha256(gate1_entry.read_bytes()).hexdigest(),
                "p_results":{"P1":"PASS","P2":"PASS","P3":"PASS","P4":"PASS","P5":"PASS","P6.1":"PASS","P7.1":"PASS","P8":"PASS","P10A":"PASS","P11":"PASS","P12":"PASS"},
                "p4_threshold_decision":None,
                "user_review":{"approved":True,"review_id":"USER-G2A-001"},
                "core_ack_id":None,"core_ack_required_before_final_delivery":True,
                "workaround":None,"result":"PASS",
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True))
            observed, bound_result = verify_gate2a_entry(
                receipt_path, result_path, G2A_SCHEMA,
                ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json",
            )
            self.assertEqual(observed["candidate_id"], result["candidate_id"])
            self.assertEqual(bound_result["result"], "PASS")
            result["executed_results"]["P8"] = "FAIL"
            result_path.write_text(json.dumps(result, sort_keys=True))
            with self.assertRaisesRegex(Exception, "result chain"):
                verify_gate2a_entry(
                    receipt_path, result_path, G2A_SCHEMA,
                    ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json",
                )

    def test_process_tree_is_transitive(self) -> None:
        table = {2:1,3:2,4:3,5:1}
        self.assertEqual(process_tree(2, table), {2,3,4})

    def test_resource_gate_requires_memory_thermal_psi_oom_and_owners(self) -> None:
        records_value = [
            {"monotonic_s":float(index) * 0.25,"system_used_mib":3000.0,
             "temperature_c":60.0,"throttled":"throttled=0x0","swap_total_kib":0,
             "psi_full_total":100,"owners":{
                 name:{"root_present":True,"process_count":1,"rss_kib":10,"pss_kib":9,
                       "threads":1,"cpu_ticks":index + 1}
                 for name in ("controller","vad","asr","tts","llm")
             },"collection_duration_s":0.01}
            for index in range(3)
        ]
        passed, summary = evaluate_resources(records_value, oom_before=1, oom_after=1)
        self.assertTrue(passed)
        self.assertEqual(summary["psi_full_total_delta"], 0)
        records_value[-1]["system_used_mib"] = 3584.001
        self.assertFalse(evaluate_resources(records_value, oom_before=1, oom_after=1)[0])
        records_value[-1]["system_used_mib"] = 3000.0
        for record in records_value:
            for owner in record["owners"].values():
                owner["cpu_ticks"] = 1
        self.assertFalse(evaluate_resources(records_value, oom_before=1, oom_after=1)[0])

    def test_combined_llm_uses_speak_only_and_detects_prior_marker(self) -> None:
        class Process:
            pid = 100
            def poll(self):
                return None

        terminal = {
            "type":"RESULT", "request_id":"M4-SESSION-01",
            "response":{"action_kind":"speak","action_payload":{"text":"safe speech G2BN0001"},"next_perceptions":["listen"]},
            "metrics":{"prefill_tokens":20,"decode_tokens":3,"kv_tokens":23,
                       "ttft_ms":1.0,"decode_tokens_per_second":10.0},
        }
        domain = CombinedLlmDomain(
            common={"validator":object()}, stderr=None, engine_capacity=512
        )
        domain.process = Process()
        with patch("poc_llm.tools.run_gate2b_pi_v1.generate", return_value=(terminal, 1.0)) as called:
            observed = domain._run("M4-SESSION-01", "private transcript", "G2BN0001", "G2BT0001")
        prompt = called.call_args.args[3]
        self.assertEqual(prompt["capabilities"]["actions"], ["speak"])
        self.assertIn("private transcript", prompt["perceptions"][0]["text"])
        self.assertNotIn("private transcript", json.dumps(observed))
        self.assertTrue(observed["current_marker_present_once"])
        self.assertTrue(observed["current_trap_absent"])
        terminal["request_id"] = "M4-SESSION-02"
        terminal["response"]["action_payload"]["text"] = "leaked G2BN0001 current G2BN0002"
        with patch("poc_llm.tools.run_gate2b_pi_v1.generate", return_value=(terminal, 1.0)):
            leaked = domain._run("M4-SESSION-02", "next", "G2BN0002", "G2BT0002")
        self.assertTrue(leaked["prior_marker_leaked"])

    def test_audio_kit_verifier_checks_manifest_and_each_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = {}
            for name in ("packet","packet_schema","result_schema","runner"):
                path = root / f"{name}.txt"
                path.write_text(name)
                items[name] = {
                    "path":path.name,
                    "sha256":hashlib.sha256(name.encode()).hexdigest(),
                }
            manifest = {
                "status":"POC_ACCEPTED_M4_COMPLETE", "delivery_id":"delivery",
                "repository":{"corrected_delivery_sha":"a"*40},
                "core_acceptance":{"commit":"b"*40}, "conformance_kit":items,
            }
            manifest_path = root / "poc_audio/evidence/m4/M4-GATE2B-READY-001/manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest))
            accepted = {
                "manifest_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                "delivery_id":"delivery", "corrected_delivery_sha":"a"*40,
                "core_response_sha":"b"*40,
                "conformance_kit":{
                    f"{name}_sha256":item["sha256"] for name,item in items.items()
                },
            }
            report = verify_audio_kit(root, accepted)
            self.assertEqual(report["status"], "POC_ACCEPTED_M4_COMPLETE")
            (root / "runner.txt").write_text("drift")
            with self.assertRaisesRegex(Exception, "kit mismatch"):
                verify_audio_kit(root, accepted)

    def test_gate2b_pass_schema_requires_20_sessions_and_both_p_items(self) -> None:
        accepted_entry = json.loads(AUDIO_ENTRY.read_text())
        value = {
            "packet_id":"G2B-PI-COMBINED-001","run_id":"run",
            "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1","execution_sha":"a"*40,
            "execution_surface_sha256":"b"*64,"gate2a_receipt_sha256":"c"*64,
            "accepted_audio":{
                "audio_completion_sha":accepted_entry["completion_sha"],
                "audio_tag":accepted_entry["tag"],
                "audio_tag_object_sha":accepted_entry["tag_object_sha"],
                "core_hal_execution_sha":accepted_entry["core_hal_execution_sha"],
                "delivery_id":accepted_entry["delivery_id"],
                "manifest_sha256":accepted_entry["manifest_sha256"],
                "status":accepted_entry["status"],
                "core_response_id":accepted_entry["core_response_id"],
                "core_response_sha":accepted_entry["core_response_sha"],
            },"environment":{},"environment_post":{},"runtime":{},
            "artifact_authentication":{"reused_receipt_sha256":"f"*64,
                "model_sha256":"a"*64,"model_size_bytes":1,
                "full_model_hash_count":0,"metadata_unchanged":True},
            "sessions":[valid_result_session(index) for index in range(1,21)],
            "soak":{"cadence_seconds":5.0,"pause_count":19,"pause_elapsed_ms":[5000.0]*19,"total_elapsed_ms":95000.0},
            "resources":{"sample_count":2,"peak_system_used_mib":3000.0,
                "peak_temperature_c":60.0,"max_sample_start_gap_s":0.25,
                "max_collection_duration_s":0.1,"psi_full_total_delta":0,
                "oom_kill_delta":0,"owner_sets_complete":True,
                "cpu_observed_for_all_owners":True,"swap_zero_for_all_samples":True,
                "throttled_zero_for_all_samples":True,
                "owner_peaks":{name:{} for name in ("controller","vad","asr","tts","llm")}},
            "cleanup":{"reverse_order":["llm","tts","asr","vad"],
                "process_groups_absent":{name:True for name in ("vad","asr","tts","llm")},
                "audio_device_owner_count":0,
                "llm":{"exit_code":0,"waited":True,"term_sent":False,
                       "kill_sent":False,"process_group_absent":True}},
            "p_results":{"P9":"PASS","P10B":"PASS"},
            "violations":[],"result":"PASS","publication_status":"REVIEW_REQUIRED",
        }
        validator = Draft202012Validator(json.loads(G2B_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(value))
        empty_resources = {**value, "resources":{}}
        self.assertFalse(validator.is_valid(empty_resources))
        value["sessions"].pop()
        self.assertFalse(validator.is_valid(value))

    def test_formal_runner_has_no_surrogate_or_scored_failure_replay(self) -> None:
        source = G2B_RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("run_p9_residency_surrogate", source)
        self.assertIn('lock.get("fault_schedule") != []', source)
        self.assertIn("full_model_hash_count\": 0", source)
        self.assertIn("TranscriptAsrDomain", source)

    def test_preexisting_gate2b_paths_are_not_deleted(self) -> None:
        run_id = f"g2b-ownership-{uuid.uuid4().hex}"
        install = Path(f"/tmp/llm-poc-g2b-001/install-{run_id}")
        work = Path(f"/tmp/llm-poc-g2b-001/work-{run_id}")
        install.mkdir(parents=True)
        work.mkdir(parents=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                evidence = Path(directory)
                raw = evidence / run_id
                raw.mkdir()
                argv = [
                    "run_gate2b_pi_v1.py", "--packet-lock", str(G2B_LOCK),
                    "--gate2a-receipt", str(raw / "g2a.json"),
                    "--gate2a-result", str(raw / "g2a-result.json"),
                    "--artifact-receipt", str(raw / "artifact.json"),
                    "--accepted-audio-entry", str(AUDIO_ENTRY),
                    "--execution-sha", "a" * 40, "--run-id", run_id,
                    "--evidence-root", str(evidence), "--audio-root", str(raw / "audio"),
                    "--core-root", str(raw / "core"), "--audio-fixture-dir", str(raw / "fixtures"),
                    "--audio-fixture-lock", str(raw / "fixture-lock.json"),
                    "--audio-artifact-dir", str(raw / "artifacts"),
                    "--audio-runtime-python", str(raw / "tts-python"),
                    "--audio-asr-binary", str(raw / "asr"), "--audio-asr-model", str(raw / "asr-model"),
                    "--audio-vad-runtime-python", str(raw / "vad-python"),
                    "--audio-vad-model", str(raw / "vad-model"),
                    "--input-device", "hw:0,0", "--output-device", "hw:0,0", "--input-channel", "0",
                ]
                with patch.object(sys, "argv", argv), patch("sys.stdout", io.StringIO()):
                    self.assertEqual(gate2b_main(), 2)
                self.assertTrue(raw.is_dir())
                self.assertTrue(install.is_dir())
                self.assertTrue(work.is_dir())
        finally:
            for path in (install, work):
                if path.exists():
                    shutil.rmtree(path)


if __name__ == "__main__":
    unittest.main()
