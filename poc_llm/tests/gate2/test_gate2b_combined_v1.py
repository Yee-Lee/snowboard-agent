from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

from jsonschema import Draft202012Validator

from poc_llm.harness.gate2b_combined_v1 import Gate2BCombinedCoordinator
from poc_llm.harness.gate2b_resources_v1 import ResourceSampler, evaluate_resources, process_tree
from poc_llm.harness.litert_lm_gate2b_child_adapter_v1 import gate2b_product_prompt
from poc_llm.harness.gate2_errors_v1 import (
    CandidateViolation, CleanupViolation, EnvironmentInvalid, EvidenceInvalid, PacketDefect,
    write_json_evidence,
)
from poc_llm.harness.pi_runtime import PiPacketFailure
from test_gate2a_pi_v2 import complete_cleanup, complete_samples
from poc_llm.tools.run_gate2b_pi_v1 import (
    CombinedLlmDomain,
    ScoredAudioDomain,
    combined_exception_disposition,
    main as gate2b_main,
    scan_owned_logs,
    verify_external_checkouts,
    verify_audio_controlled_inputs,
    verify_audio_runtime,
    verify_gate2a_entry,
    verify_audio_kit,
    verify_gate2b_result,
    valid_run_id as valid_gate2b_run_id,
)


ROOT = Path(__file__).resolve().parents[3]
AUDIO_ENTRY = ROOT / "poc_llm/fixtures/gate2/accepted-audio-entry-001.json"
AUDIO_SCHEMA = ROOT / "poc_llm/evidence/m4b/accepted-audio-entry-v1.schema.json"
G2A_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate2a-model-finalist-receipt-v1.schema.json"
G2A_RECEIPT = ROOT / "poc_llm/fixtures/gate2/gate2a-gemma-model-finalist-001.json"
G2B_SCHEMA = ROOT / "poc_llm/evidence/m4b/gate2b-pi-v1-result.schema.json"
G2B_RUNNER = ROOT / "poc_llm/tools/run_gate2b_pi_v1.py"
G2B_LOCK = ROOT / "poc_llm/harness/gate2b-pi-lock-v1.json"
G2B_PACKET = ROOT / "poc_llm/tests/gate2/GATE2B-PI-PACKET-001.md"


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
            "metrics":{"prefill_tokens":8,"decode_tokens":2,"ttft_ms":1.0,
                       "decode_tokens_per_second":10.0,"kv_tokens":10},
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
               "metrics":{"prefill_tokens":8,"decode_tokens":2,"kv_tokens":10,
                          "ttft_ms":1.0,"decode_tokens_per_second":10.0}},
        "tts":{"terminal":"SUCCESS","pcm_sha256":"e"*64,"sample_count":10,
               "playback_complete":True,"input_speech_sha256":"d"*64},
        "timings_ms":{"vad":1.0,"asr":1.0,"llm":1.0,"tts_playback":1.0,"end_to_end":4.0},
    }


def resource_values(leak_per_session: float = 0.0) -> tuple[list[dict], list[dict]]:
    def sample(index: int, *, session: bool) -> dict:
        value = {
            "monotonic_s":float(index) * 0.25,"mem_total_kib":4_000_000,
            "mem_available_kib":1_000_000,"system_used_mib":3000.0 + leak_per_session * index,
            "temperature_c":60.0,"throttled":"throttled=0x0","swap_total_kib":0,
            "psi_full_total":100,"owners":{
                name:{"root_pid":100 + offset,"root_present":True,"process_count":1,
                      "rss_kib":1000,"pss_kib":900 + int(leak_per_session * 1024 * index / 5),
                      "threads":1,"cpu_ticks":index + 1}
                for offset,name in enumerate(("controller","vad","asr","tts","llm"))
            },"unique_process_count":5,
        }
        if session:
            value["session_index"] = index + 1
        else:
            value["collection_duration_s"] = 0.01
        return value
    return [sample(index, session=False) for index in range(3)], [
        sample(index, session=True) for index in range(20)
    ]


class Gate2BCombinedTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_ready_audio_stage_fault_is_candidate_violation(self) -> None:
        events: list[str] = []
        accepted = Vad("vad", events)

        async def fail(_session: dict) -> dict:
            raise RuntimeError("private backend detail")

        accepted.run = fail  # type: ignore[method-assign]
        wrapped = ScoredAudioDomain("VAD", accepted)
        await wrapped.start()
        with self.assertRaises(CandidateViolation):
            await wrapped.run({"session_id":"M4-SESSION-01"})
        await wrapped.stop()

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

    async def test_each_domain_stop_failure_forces_all_owned_groups_absent(self) -> None:
        async def pause(_value: float) -> None:
            pass

        async def injected_stop(self) -> None:
            self.events.append(f"stop:{self.name}")
            raise RuntimeError("injected stop failure")

        for failed_name in ("vad", "asr", "tts", "llm"):
            with self.subTest(domain=failed_name):
                events: list[str] = []
                classes = {"vad":Vad,"asr":Asr,"tts":Tts,"llm":Llm}
                failed_class = type(
                    f"StopFailure{failed_name}", (classes[failed_name],),
                    {"stop": injected_stop},
                )
                domains = {
                    name:(failed_class(name, events) if name == failed_name else classes[name](name, events))
                    for name in classes
                }
                by_pid = {domain.pid:domain for domain in domains.values()}
                coordinator = Gate2BCombinedCoordinator(
                    domains["vad"], domains["asr"], domains["llm"], domains["tts"],
                    pause=pause,
                    group_absent=lambda pid: not by_pid[pid].alive,
                    force_cleanup=lambda _name, pid: (
                        setattr(by_pid[pid], "alive", False)
                        or {"process_group_absent":True}
                    ),
                )
                with self.assertRaises(CleanupViolation):
                    await coordinator.run(records(), cadence_s=0)
                self.assertTrue(all(not domain.alive for domain in domains.values()))
                self.assertTrue(coordinator.cleanup_proofs[failed_name]["fallback_used"])

    async def test_partial_start_failure_still_force_cleans_earlier_owner(self) -> None:
        async def pause(_value: float) -> None:
            pass

        events: list[str] = []
        vad, asr = Vad("vad", events), Asr("asr", events)

        async def vad_stop_failure() -> None:
            events.append("stop:vad")
            raise RuntimeError("injected stop failure")

        async def asr_start_failure() -> None:
            events.append("start:asr")
            raise RuntimeError("injected start failure")

        vad.stop = vad_stop_failure  # type: ignore[method-assign]
        asr.start = asr_start_failure  # type: ignore[method-assign]
        domains = {vad.pid: vad, asr.pid: asr}
        coordinator = Gate2BCombinedCoordinator(
            vad, asr, Llm("llm", events), Tts("tts", events), pause=pause,
            group_absent=lambda pid: not domains.get(pid, vad).alive,
            force_cleanup=lambda _name, pid: (
                setattr(domains[pid], "alive", False) or {"process_group_absent": True}
            ),
        )
        with self.assertRaises(CleanupViolation):
            await coordinator.run(records(), cadence_s=0)
        self.assertFalse(vad.alive)
        self.assertEqual(coordinator.started_roots["vad"], vad.pid)
        self.assertTrue(coordinator.cleanup_proofs["vad"]["fallback_used"])
        self.assertTrue(coordinator.cleanup_proofs["vad"]["process_group_absent"])

    async def test_start_raises_after_becoming_live_and_owner_is_force_cleaned(self) -> None:
        async def pause(_value: float) -> None:
            pass

        events: list[str] = []
        vad = Vad("vad", events)

        async def start_then_raise() -> None:
            events.append("start:vad")
            vad.alive = True
            raise RuntimeError("injected post-allocation start failure")

        async def stop_failure() -> None:
            events.append("stop:vad")
            raise RuntimeError("injected stop failure")

        vad.start = start_then_raise  # type: ignore[method-assign]
        vad.stop = stop_failure  # type: ignore[method-assign]
        coordinator = Gate2BCombinedCoordinator(
            vad, Asr("asr", events), Llm("llm", events), Tts("tts", events), pause=pause,
            group_absent=lambda _pid: not vad.alive,
            force_cleanup=lambda _name, _pid: (
                setattr(vad, "alive", False) or {"process_group_absent": True}
            ),
        )
        with self.assertRaises(CleanupViolation):
            await coordinator.run(records(), cadence_s=0)
        self.assertFalse(vad.alive)
        self.assertEqual(coordinator.started_roots["vad"], vad.pid)
        self.assertTrue(coordinator.cleanup_proofs["vad"]["fallback_used"])


class Gate2BDefinitionTests(unittest.TestCase):
    def test_formal_launch_uses_private_read_only_sysfs(self) -> None:
        packet = G2B_PACKET.read_text(encoding="utf-8")
        self.assertIn(
            "unshare --user --map-root-user --mount --net -- env -i", packet
        )
        self.assertIn("mount -t sysfs -o ro sysfs /sys", packet)
        self.assertNotIn("unshare --user --map-root-user --net -- env -i", packet)

    def test_run_id_is_single_safe_slug(self) -> None:
        self.assertTrue(valid_gate2b_run_id("G2B-PI-COMBINED-001"))
        for value in ("../escape", "/tmp/escape", "nested/run", "", "a" * 129):
            self.assertFalse(valid_gate2b_run_id(value))

    def test_error_category_matrix_is_fail_closed_without_conflation(self) -> None:
        for error in (CandidateViolation("terminal"), CleanupViolation("residue")):
            self.assertEqual(
                combined_exception_disposition(error, combined_entered=True),
                ({"P9":"Blocked","P10B":"FAIL"}, "FAIL"),
            )
        for error in (EnvironmentInvalid("thermal"), EvidenceInvalid("write"),
                      PacketDefect("method"), OSError("protocol I/O")):
            self.assertEqual(
                combined_exception_disposition(error, combined_entered=True),
                ({"P9":"Blocked","P10B":"Blocked"}, "INCONCLUSIVE"),
            )

    def test_entered_llm_protocol_faults_fail_p10b_via_domain_runner(self) -> None:
        domain = CombinedLlmDomain(common={"validator": object()}, stderr=io.StringIO(), engine_capacity=512)
        domain.process = object()  # type: ignore[assignment]
        for injected in (
            PiPacketFailure("protocol frame deadline exceeded"),
            PiPacketFailure("candidate stdout closed"),
            PiPacketFailure("candidate emitted invalid JSONL"),
            PiPacketFailure("candidate emitted protocol-invalid frame"),
            BrokenPipeError("closed"), ConnectionResetError("reset"),
        ):
            with self.subTest(error=type(injected).__name__), patch(
                "poc_llm.tools.run_gate2b_pi_v1.generate",
                side_effect=injected,
            ):
                with self.assertRaises(CandidateViolation) as caught:
                    domain._run("M4-SESSION-01", "transcript", "nonce", "trap")
                self.assertEqual(
                    combined_exception_disposition(caught.exception, combined_entered=True),
                    ({"P9":"Blocked","P10B":"FAIL"}, "FAIL"),
                )
        self.assertEqual(
            combined_exception_disposition(EnvironmentInvalid("sampler"), combined_entered=True),
            ({"P9":"Blocked","P10B":"Blocked"}, "INCONCLUSIVE"),
        )

    def test_gate2b_lock_authenticates_repository_surface(self) -> None:
        lock = json.loads(G2B_LOCK.read_text())
        self.assertEqual(lock["packet_id"], "G2B-PI-COMBINED-001")
        self.assertEqual(lock["fault_schedule"], [])
        self.assertEqual(lock["session_count"], 20)
        self.assertEqual(set(lock["candidates"]), {"CAND-LRT-G4E2B-MOBILE-R1"})
        self.assertEqual(
            lock["candidates"]["CAND-LRT-G4E2B-MOBILE-R1"]["product_config"]["path"],
            "poc_llm/fixtures/gate2/pi-configs-v2/"
            "CAND-LRT-G4E2B-MOBILE-R1-gate2b-product.json",
        )
        self.assertEqual(
            lock["artifacts"]["gate2b_adapter"]["path"],
            "poc_llm/harness/litert_lm_gate2b_child_adapter_v1.py",
        )
        self.assertEqual(
            lock["artifacts"]["gate2a_receipt"]["path"],
            "poc_llm/fixtures/gate2/gate2a-gemma-model-finalist-001.json",
        )
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
        self.assertEqual(
            entry["controlled_inputs"]["fixture_lock_sha256"],
            "d7d3086c578511763b60074ef7c049e37ef814094e399ad3562e3be2fda0e0f8",
        )
        self.assertEqual(
            entry["finalists"]["asr"]["worker_binary_sha256"],
            "64ca4ce45899a39afe467e6249a440e3807e18d8e09ff4c3267242d81d2b1b2b",
        )
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

    def test_gate2a_receipt_preserves_failures_and_user_model_selection(self) -> None:
        value = json.loads(G2A_RECEIPT.read_text())
        validator = Draft202012Validator(json.loads(G2A_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(value))
        value["p_results"]["P2"] = "PASS"
        self.assertFalse(validator.is_valid(value))
        value = json.loads(G2A_RECEIPT.read_text())
        value["candidate_id"] = "CAND-LRT-Q25-15B-Q8-R1"
        self.assertFalse(validator.is_valid(value))
        value = json.loads(G2A_RECEIPT.read_text())
        value["user_review"]["approved"] = False
        self.assertFalse(validator.is_valid(value))

    def test_gate2b_prompt_is_generic_deterministic_and_schema_explicit(self) -> None:
        value = {
            "perceptions":[{"kind":"listen","status":"ok","text":"hello MARKER-X"}],
            "pending_message_count":0,
            "capabilities":{"perceptions":["listen"],"actions":["speak"],"tools":[]},
        }
        first = gate2b_product_prompt(value)
        self.assertEqual(first, gate2b_product_prompt(json.loads(json.dumps(value))))
        self.assertIn('"action_kind":"speak"', first)
        self.assertIn("MARKER-X", first)
        source = (ROOT / "poc_llm/harness/litert_lm_gate2b_child_adapter_v1.py").read_text()
        self.assertNotIn("M4-SESSION-", source)
        self.assertNotIn("P2-00", source)

    def test_gate2a_receipt_is_bound_to_actual_reviewed_result(self) -> None:
        lock_sha = hashlib.sha256((ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json").read_bytes()).hexdigest()
        artifact_sha = "e" * 64
        samples = complete_samples()
        samples["p2"]["cases"][0]["valid"] = False
        samples["p8"]["cases"][0]["current_marker_present_once"] = False
        result = {
            "packet_id":"G2A-PI-LLM-002","run_id":"run",
            "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1","execution_sha":"a"*40,
            "execution_surface_sha256":lock_sha,"gate1_entry":{},"isolation":{},
            "environment":{},"environment_post":{},"runtime":{},
            "artifact_authentication":{"reused_receipt_sha256":artifact_sha,
                "model_sha256":"d"*64,"model_size_bytes":1,
                "full_model_hash_count":0,"metadata_unchanged":True},
            "carried_results":{"P1":"PASS","P6.1":"PASS","P7.1":"PASS","P10A":"PASS","P11":"PASS","P12":"PASS"},
            "executed_results":{"P2":"FAIL","P3":"PASS","P4":"PASS","P5":"PASS","P8":"FAIL"},
            "samples":samples,
            "cleanup":complete_cleanup(),"violations":[],"gate2a_scope_result":"FAIL",
            "provisional_eligibility":"NOT_ELIGIBLE","result":"FAIL",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "gate2a.json"
            result_path.write_text(json.dumps(result, sort_keys=True))
            gate1_entry = ROOT / "poc_llm/fixtures/gate2/gate1-closure-entry-001.json"
            receipt = {
                "receipt_version":"gate2a-model-finalist/1","packet_id":"G2A-PI-LLM-002",
                "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1","candidate_disposition":"USER_SELECTED_MODEL_FINALIST",
                "execution_sha":"a"*40,"execution_surface_sha256":lock_sha,
                "gate2a_lock_sha256":lock_sha,
                "candidate_result_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest(),
                "artifact_receipt_sha256":artifact_sha,
                "gate1_entry_sha256":hashlib.sha256(gate1_entry.read_bytes()).hexdigest(),
                "p_results":{"P1":"PASS","P2":"FAIL","P3":"PASS","P4":"PASS","P5":"PASS","P6.1":"PASS","P7.1":"PASS","P8":"FAIL","P10A":"PASS","P11":"PASS","P12":"PASS"},
                "p8_qualifier":"DEPENDENCY_LIMITED_BY_P2",
                "selection":{"decision":"ADVANCE_MODEL_ONLY","current_product_baseline":"REJECTED",
                    "gate2b_pairing_revision":"litert-lm-v0.16.0-pi-g2b-r1",
                    "gate2b_product_config_sha256":"a"*64,
                    "scoring_policy":"FIRST_MODEL_CONTACT_IS_HELD_OUT_GATE2B"},
                "user_review":{"approved":True,"review_id":"ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW"},
                "core_ack_id":None,"core_ack_required_before_final_delivery":True,
                "result":"MODEL_FINALIST_SELECTED",
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True))
            observed, bound_result = verify_gate2a_entry(
                receipt_path, result_path, G2A_SCHEMA,
                ROOT / "poc_llm/harness/gate2a-pi-lock-v2.json",
            )
            self.assertEqual(observed["candidate_id"], result["candidate_id"])
            self.assertEqual(bound_result["result"], "FAIL")
            result["samples"]["p8"]["cases"][1]["prior_marker_leaked"] = True
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
        records_value, points = resource_values()
        passed, summary = evaluate_resources(
            records_value, session_points=points, oom_before=1, oom_after=1
        )
        self.assertTrue(passed)
        self.assertEqual(summary["psi_full_total_delta"], 0)
        records_value[-1]["system_used_mib"] = 3584.001
        self.assertFalse(evaluate_resources(
            records_value, session_points=points, oom_before=1, oom_after=1
        )[0])
        records_value[-1]["system_used_mib"] = 3000.0
        for record in records_value:
            for owner in record["owners"].values():
                owner["cpu_ticks"] = 1
        self.assertFalse(evaluate_resources(
            records_value, session_points=points, oom_before=1, oom_after=1
        )[0])

    def test_below_capacity_linear_leak_fails_frozen_p10a_rules(self) -> None:
        records_value, points = resource_values(leak_per_session=5.0)
        passed, summary = evaluate_resources(
            records_value, session_points=points, oom_before=1, oom_after=1
        )
        self.assertFalse(passed)
        self.assertGreater(summary["leak"]["system_used"]["slope_mib_per_session"], 4.0)

    def test_thermal_psi_sampler_and_evidence_faults_are_not_valid_passes(self) -> None:
        records_value, points = resource_values()
        hot = json.loads(json.dumps(records_value))
        hot[-1]["temperature_c"] = 80.0
        self.assertFalse(evaluate_resources(
            hot, session_points=points, oom_before=1, oom_after=1
        )[0])
        stalled = json.loads(json.dumps(records_value))
        stalled[-1]["psi_full_total"] += 1
        self.assertFalse(evaluate_resources(
            stalled, session_points=points, oom_before=1, oom_after=1
        )[0])
        sampler = ResourceSampler(lambda: {"controller":1}, interval_s=0.01)
        with patch(
            "poc_llm.harness.gate2b_resources_v1.resource_sample",
            side_effect=OSError("injected sampler I/O"),
        ), self.assertRaisesRegex(RuntimeError, "initial residency sample"):
            sampler.start()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(EvidenceInvalid):
                write_json_evidence(Path(directory), {"result":"PASS"})

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

    def test_runtime_gate2b_canary_leak_is_detected_without_persisting_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "llm.stderr"
            path.write_text("diagnostic G2BN0007 only", encoding="utf-8")
            report = scan_owned_logs([path], {"G2BN0007"})
        self.assertFalse(report["passed"])
        self.assertNotIn("G2BN0007", json.dumps(report))

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

    def test_audio_controlled_inputs_and_runtime_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_dir = root / "artifacts"
            models = artifact_dir / "models"
            models.mkdir(parents=True)
            paths = {
                "vad_model": root / "vad.onnx",
                "asr_binary": root / "asr-worker",
                "asr_model": root / "asr-model.bin",
                "tts_archive": models / "matcha-icefall-zh-en.tar.bz2",
                "tts_vocoder": models / "vocos-16khz-univ.onnx",
            }
            for name, path in paths.items():
                path.write_bytes(name.encode())
            lock = {
                "audio_execution_sha":"8" * 40,
                "fixture_count":20,
                "records":[
                    {"session_id":f"M4-SESSION-{index:02d}",
                     "fixture_id":f"fixture-{index:02d}","sha256":f"{index:064x}"}
                    for index in range(1, 21)
                ],
            }
            delivered = {
                "records":{
                    item["fixture_id"]:{"derived_sha256":item["sha256"]}
                    for item in lock["records"]
                }
            }
            fixture_lock = root / "fixture-lock.json"
            fixture_manifest = root / "fixture-manifest.json"
            fixture_lock.write_text(json.dumps(lock, sort_keys=True))
            fixture_manifest.write_text(json.dumps(delivered, sort_keys=True))
            accepted = json.loads(AUDIO_ENTRY.read_text())
            accepted["p9_combined_execution_sha"] = "8" * 40
            accepted["controlled_inputs"] = {
                "fixture_lock_sha256":hashlib.sha256(fixture_lock.read_bytes()).hexdigest(),
                "delivered_fixture_manifest_sha256":hashlib.sha256(
                    fixture_manifest.read_bytes()
                ).hexdigest(),
                "fixture_count":20,
            }
            accepted["finalists"]["vad"]["model_sha256"] = hashlib.sha256(
                paths["vad_model"].read_bytes()
            ).hexdigest()
            accepted["finalists"]["asr"].update({
                "worker_binary_sha256":hashlib.sha256(
                    paths["asr_binary"].read_bytes()
                ).hexdigest(),
                "model_sha256":hashlib.sha256(paths["asr_model"].read_bytes()).hexdigest(),
            })
            accepted["finalists"]["tts"].update({
                "archive_sha256":hashlib.sha256(paths["tts_archive"].read_bytes()).hexdigest(),
                "vocoder_sha256":hashlib.sha256(paths["tts_vocoder"].read_bytes()).hexdigest(),
            })
            with patch(
                "poc_llm.tools.run_gate2b_pi_v1.verify_audio_runtime",
                side_effect=[accepted["runtimes"]["vad"], accepted["runtimes"]["tts"]],
            ):
                observed = verify_audio_controlled_inputs(
                    fixture_lock=fixture_lock,
                    fixture_manifest=fixture_manifest,
                    artifact_dir=artifact_dir,
                    tts_runtime_python=root / "tts-python",
                    asr_binary=paths["asr_binary"],
                    asr_model=paths["asr_model"],
                    vad_runtime_python=root / "vad-python",
                    vad_model=paths["vad_model"],
                    accepted=accepted,
                )
            self.assertEqual(observed["fixture_count"], 20)
            paths["asr_binary"].write_bytes(b"drift")
            with self.assertRaisesRegex(Exception, "asr_binary_sha256"):
                verify_audio_controlled_inputs(
                    fixture_lock=fixture_lock,
                    fixture_manifest=fixture_manifest,
                    artifact_dir=artifact_dir,
                    tts_runtime_python=root / "tts-python",
                    asr_binary=paths["asr_binary"],
                    asr_model=paths["asr_model"],
                    vad_runtime_python=root / "vad-python",
                    vad_model=paths["vad_model"],
                    accepted=accepted,
                )

            runtime_python = root / "venv/bin/python"
            runtime_python.parent.mkdir(parents=True)
            runtime_python.write_text("stub")
            (root / "venv/pyvenv.cfg").write_text(
                "include-system-site-packages = false\n"
            )
            runtime_expected = accepted["runtimes"]["vad"]
            completed = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps(runtime_expected), stderr=""
            )
            with patch("poc_llm.tools.run_gate2b_pi_v1.subprocess.run", return_value=completed):
                self.assertEqual(
                    verify_audio_runtime(runtime_python, runtime_expected), runtime_expected
                )
            (root / "venv/pyvenv.cfg").write_text(
                "include-system-site-packages = true\n"
            )
            with self.assertRaisesRegex(Exception, "isolation"):
                verify_audio_runtime(runtime_python, runtime_expected)

    def test_gate2b_pass_schema_requires_20_sessions_and_both_p_items(self) -> None:
        accepted_entry = json.loads(AUDIO_ENTRY.read_text())
        continuous, points = resource_values()
        _passed, resource_summary = evaluate_resources(
            continuous, session_points=points, oom_before=1, oom_after=1
        )
        value = {
            "packet_id":"G2B-PI-COMBINED-001","run_id":"run",
            "candidate_id":"CAND-LRT-G4E2B-MOBILE-R1",
            "integration_pairing_revision":"litert-lm-v0.16.0-pi-g2b-r1",
            "execution_sha":"a"*40,
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
                "fixture_lock_sha256":accepted_entry["controlled_inputs"]["fixture_lock_sha256"],
                "fixture_manifest_sha256":accepted_entry["controlled_inputs"]["delivered_fixture_manifest_sha256"],
                "fixture_count":accepted_entry["controlled_inputs"]["fixture_count"],
                "vad_model_sha256":accepted_entry["finalists"]["vad"]["model_sha256"],
                "asr_binary_sha256":accepted_entry["finalists"]["asr"]["worker_binary_sha256"],
                "asr_model_sha256":accepted_entry["finalists"]["asr"]["model_sha256"],
                "tts_archive_sha256":accepted_entry["finalists"]["tts"]["archive_sha256"],
                "tts_vocoder_sha256":accepted_entry["finalists"]["tts"]["vocoder_sha256"],
                "vad_runtime":accepted_entry["runtimes"]["vad"],
                "tts_runtime":accepted_entry["runtimes"]["tts"],
            },"environment":{},"environment_post":{},"runtime":{},
            "artifact_authentication":{"reused_receipt_sha256":"f"*64,
                "model_sha256":"a"*64,"model_size_bytes":1,
                "full_model_hash_count":0,"metadata_unchanged":True},
            "sessions":[valid_result_session(index) for index in range(1,21)],
            "soak":{"cadence_seconds":5.0,"pause_count":19,"pause_elapsed_ms":[5000.0]*19,"total_elapsed_ms":95000.0},
            "resources":resource_summary,
            "resource_observations":{"continuous_samples":continuous,"session_points":points,
                                     "oom_before":1,"oom_after":1},
            "cleanup":{"reverse_order":["llm","tts","asr","vad"],
                "process_groups_absent":{name:True for name in ("vad","asr","tts","llm")},
                "audio_device_owner_count":0,
                "llm":{"exit_code":0,"waited":True,"term_sent":False,
                       "kill_sent":False,"process_group_absent":True},
                "domains":{name:{"root_pid":100+index,"cooperative_stop":True,
                    "fallback_used":False,"process_group_absent":True,"error_type":None}
                    for index,name in enumerate(("vad","asr","tts","llm"))}},
            "log_hygiene":{"passed":True,"scanned_files":[
                {"name":name,"sha256":"9"*64}
                for name in (
                    "offline-install.stdout","offline-install.stderr",
                    "llm.stderr","base-q8.stderr.log",
                )
            ],"static_marker_count":7,"runtime_marker_count":80},
            "partial_trace":[],
            "p_results":{"P9":"PASS","P10B":"PASS"},
            "violations":[],"result":"PASS","publication_status":"REVIEW_REQUIRED",
        }
        validator = Draft202012Validator(json.loads(G2B_SCHEMA.read_text()))
        self.assertTrue(validator.is_valid(value))
        self.assertEqual(verify_gate2b_result(
            value, engine_capacity=1024, max_output_tokens=64
        ), {"P9":"PASS","P10B":"PASS"})
        mismatched = json.loads(json.dumps(value))
        mismatched["sessions"][0]["llm"]["request_id"] = "M4-SESSION-02"
        with self.assertRaises(EvidenceInvalid):
            verify_gate2b_result(mismatched, engine_capacity=1024, max_output_tokens=64)
        incomplete_owner = json.loads(json.dumps(value))
        del incomplete_owner["resource_observations"]["session_points"][0]["owners"]["vad"]
        with self.assertRaises(EvidenceInvalid):
            verify_gate2b_result(incomplete_owner, engine_capacity=1024, max_output_tokens=64)
        residue = json.loads(json.dumps(value))
        residue["cleanup"]["domains"]["tts"]["fallback_used"] = True
        with self.assertRaises(EvidenceInvalid):
            verify_gate2b_result(residue, engine_capacity=1024, max_output_tokens=64)
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
                    "--audio-fixture-manifest", str(raw / "fixture-manifest.json"),
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
