#!/usr/bin/env python3
"""Gate 1 packet self/negative regressions; never candidate or platform evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "poc_llm/tools/run_gate1_prescreen.py"
SELECTOR = ROOT / "poc_llm/tools/select_gate1_finalists.py"
LOCK = ROOT / "poc_llm/harness/gate1-lock.json"
CATALOG = ROOT / "poc_llm/fixtures/gate1/catalog.json"
TEST_ROOT = ROOT / "poc_llm/tests/gate1"
POSITIVE_MANIFEST = TEST_ROOT / "CAND-PROTOCOL-SELFTEST.json"
NO_LLM_MANIFEST = TEST_ROOT / "CAND-NO-LLM-REPRO.json"
LOG_LEAK_MANIFEST = TEST_ROOT / "CAND-LOG-LEAK-REPRO.json"
P4_COLD_MANIFEST = TEST_ROOT / "CAND-P4-COLD-REPRO.json"
ORPHAN_MANIFEST = TEST_ROOT / "CAND-ORPHAN-REPRO.json"
HOST_PLATFORM = {"x86_64": "ubuntu-x86_64", "aarch64": "ubuntu-aarch64"}.get(platform.machine())
OTHER_PLATFORM = "ubuntu-aarch64" if HOST_PLATFORM == "ubuntu-x86_64" else "ubuntu-x86_64"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_sha256(argv: list[str]) -> str:
    return hashlib.sha256(json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


class Gate1PacketTest(unittest.TestCase):
    def run_candidate(self, temp: Path, manifest: Path, run_id: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RUNNER), "--platform", HOST_PLATFORM, "--run-id", run_id,
             "--candidate-manifest", str(manifest), "--lock", str(LOCK),
             "--raw-dir", str(temp / f"{run_id}-raw")],
            cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
        )

    def run_selector(
        self, manifests: list[Path], results: list[Path],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SELECTOR), "--lock", str(LOCK),
             "--candidate-manifests", *map(str, manifests), "--results", *map(str, results)],
            cwd=ROOT, check=False, capture_output=True, text=True, timeout=30,
        )

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_official_protocol_flow_and_expected_json_printer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-official-") as temporary:
            temp = Path(temporary)
            positive = self.run_candidate(temp, POSITIVE_MANIFEST, "G1-RUN-PROTOCOL-TEST")
            self.assertEqual(positive.returncode, 0, positive.stdout + positive.stderr)
            positive_result = json.loads(positive.stdout)
            self.assertEqual(positive_result["result"], "PASS")
            self.assertEqual(set(positive_result["gates"].values()), {"PASS"})
            self.assertEqual(len(positive_result["cases"]), 60)
            for key in ("cold_total_ms", "cold_ttft_ms", "cold_output_tokens",
                        "cold_tokens_per_second_samples"):
                self.assertEqual(len(positive_result["metrics"][key]), 3)
            self.assertEqual(positive_result["log_hygiene"]["forbidden_sentinel_ids"], [])
            self.assertEqual(positive_result["cleanup"], {
                "exit_code": 0, "waited": True, "term_sent": False,
                "kill_sent": False, "process_group_absent": True,
            })

            negative = self.run_candidate(temp, NO_LLM_MANIFEST, "G1-RUN-NO-LLM-TEST")
            self.assertEqual(negative.returncode, 1, negative.stdout + negative.stderr)
            negative_result = json.loads(negative.stdout)
            self.assertEqual(negative_result["result"], "FAIL")
            self.assertNotEqual(negative_result["gates"]["P1"], "PASS")
            self.assertTrue(negative_result["cleanup"]["process_group_absent"])

            result_paths = []
            for name, result in (("positive", positive_result), ("negative", negative_result)):
                for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                    value = copy.deepcopy(result)
                    value["platform"] = result_platform
                    path = temp / f"{name}-{result_platform}.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    result_paths.append(path)
            selection = self.run_selector([POSITIVE_MANIFEST, NO_LLM_MANIFEST], result_paths)
            self.assertEqual(selection.returncode, 0, selection.stdout + selection.stderr)
            decision = json.loads(selection.stdout)
            self.assertEqual([item["candidate_id"] for item in decision["proposed_finalists"]],
                             ["CAND-PROTOCOL-SELFTEST"])

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_selector_is_deterministic_and_caps_finalists_at_two(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-selector-") as temporary:
            temp = Path(temporary)
            run = self.run_candidate(temp, POSITIVE_MANIFEST, "G1-RUN-RANK-TEST")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            baseline = json.loads(run.stdout)
            source_manifest = json.loads(POSITIVE_MANIFEST.read_text(encoding="utf-8"))
            manifests = []
            results = []
            for index in range(3):
                candidate_id = f"CAND-RANK-{index}"
                manifest = copy.deepcopy(source_manifest)
                manifest["candidate_id"] = candidate_id
                manifest["pairing_revision"] = "selector-test-r1"
                for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                    command = manifest["commands"][result_platform]
                    candidate_index = command["argv"].index("--candidate-id") + 1
                    command["argv"][candidate_index] = candidate_id
                    command["sha256"] = command_sha256(command["argv"])
                manifest_path = temp / f"manifest-{index}.json"
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                manifests.append(manifest_path)
                for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                    value = copy.deepcopy(baseline)
                    value["candidate_id"] = candidate_id
                    value["pairing_revision"] = "selector-test-r1"
                    value["platform"] = result_platform
                    platform_suffix = result_platform.split("-")[-1].replace("_", "").upper()
                    value["run_id"] = f"G1-RUN-RANK-{index}-{platform_suffix}"
                    value["identity"]["manifest_sha256"] = sha256(manifest_path)
                    value["identity"]["command_sha256"] = manifest["commands"][result_platform]["sha256"]
                    value["metrics"]["peak_rss_bytes"] += index
                    path = temp / f"rank-{index}-{result_platform}.json"
                    path.write_text(json.dumps(value), encoding="utf-8")
                    results.append(path)
            selection = self.run_selector(manifests, results)
            self.assertEqual(selection.returncode, 0, selection.stdout + selection.stderr)
            decision = json.loads(selection.stdout)
            self.assertTrue(decision["max_two_enforced"])
            self.assertEqual([item["candidate_id"] for item in decision["proposed_finalists"]],
                             ["CAND-RANK-0", "CAND-RANK-1"])

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_007_a_runner_owns_log_hygiene(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-log-leak-") as temporary:
            result = self.run_candidate(Path(temporary), LOG_LEAK_MANIFEST, "G1-RUN-LOG-LEAK")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["gates"]["P3"], "FAIL")
            self.assertIn("SECRET_PAYLOAD", report["log_hygiene"]["forbidden_sentinel_ids"])
            self.assertTrue(report["log_hygiene"]["candidate_claims_ignored"])

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_007_b_missing_cold_metrics_is_non_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-p4-cold-") as temporary:
            result = self.run_candidate(Path(temporary), P4_COLD_MANIFEST, "G1-RUN-P4-COLD")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["gates"]["P4"], "FAIL")
            self.assertNotEqual(report["result"], "Core threshold decision required")

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_007_c_cleanup_reconciles_child_after_leader_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-orphan-") as temporary:
            temp = Path(temporary)
            result = self.run_candidate(temp, ORPHAN_MANIFEST, "G1-RUN-ORPHAN")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["gates"]["P1"], "FAIL")
            self.assertTrue(report["cleanup"]["term_sent"])
            self.assertTrue(report["cleanup"]["process_group_absent"])
            stderr = (temp / "G1-RUN-ORPHAN-raw/candidate.stderr").read_text(encoding="utf-8")
            orphan_pid = int(stderr.removeprefix("ORPHAN_PID=").strip())
            with self.assertRaises(ProcessLookupError):
                os.kill(orphan_pid, 0)

    @unittest.skipUnless(HOST_PLATFORM, "Gate 1 packet supports x86_64 and aarch64 only")
    def test_007_d_selector_rejects_unavailable_handcrafted_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gate1-handcrafted-") as temporary:
            temp = Path(temporary)
            identity_keys = (
                "lock_sha256","manifest_sha256","command_sha256","runtime_sha256","model_sha256",
                "config_sha256","catalog_sha256","candidate_schema_sha256","validator_sha256",
                "runner_sha256","result_schema_sha256","selection_schema_sha256","selector_sha256",
            )
            cases = [
                {"fixture_id":"G1-P2-001","repetition":(index % 3) + 1,
                 "normalized":{},"log_forbidden_hits":[]}
                for index in range(60)
            ]
            metrics = {
                "cold_total_ms":[3.0] * 3,"cold_ttft_ms":[1.0] * 3,
                "cold_output_tokens":[16] * 3,"cold_tokens_per_second_samples":[8000.0] * 3,
                "hot_total_ms":[3.0] * 20,"hot_ttft_ms":[1.0] * 20,
                "hot_output_tokens":[16] * 20,"hot_tokens_per_second_samples":[8000.0] * 20,
                "cold_total_ms_p50":3.0,"cold_total_ms_p95":3.0,
                "cold_ttft_ms_p50":1.0,"cold_ttft_ms_p95":1.0,
                "cold_tokens_per_second_p50":8000.0,"cold_tokens_per_second_p95":8000.0,
                "hot_total_ms_p50":3.0,"hot_total_ms_p95":3.0,
                "hot_ttft_ms_p50":1.0,"hot_ttft_ms_p95":1.0,
                "hot_tokens_per_second_p50":8000.0,"hot_tokens_per_second_p95":8000.0,
                "peak_rss_bytes":1,"disk_bytes":1,
            }
            paths = []
            for result_platform in (HOST_PLATFORM, OTHER_PLATFORM):
                value = {
                    "packet_id":"G1-UBUNTU-PRESCREEN-003",
                    "run_id":f"G1-RUN-HAND-{result_platform.split('-')[-1].replace('_', '').upper()}",
                    "candidate_id":"CAND-PROTOCOL-SELFTEST","pairing_revision":"test-only-r2",
                    "platform":result_platform,"result":"PASS",
                    "identity":{key:"UNAVAILABLE" for key in identity_keys},
                    "gates":{key:"PASS" for key in ("P1","P2","P3","P4","P5","P6","P8","P11")},
                    "cases":cases,"metrics":metrics,
                    "log_hygiene":{"scanner_version":"1.0.0","stderr_sha256":"0" * 64,
                                   "stderr_bytes_scanned":0,"stdout_frames_scanned":98,
                                   "forbidden_sentinel_ids":[],"candidate_claims_ignored":True},
                    "cleanup":{"exit_code":0,"waited":True,"term_sent":False,
                               "kill_sent":False,"process_group_absent":True},
                    "violations":[],
                }
                path = temp / f"handcrafted-{result_platform}.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                paths.append(path)
            selection = self.run_selector([POSITIVE_MANIFEST], paths)
            self.assertNotEqual(selection.returncode, 0, selection.stdout + selection.stderr)
            decision = json.loads(selection.stdout)
            self.assertEqual(decision["proposed_finalists"], [])


if __name__ == "__main__":
    unittest.main()
