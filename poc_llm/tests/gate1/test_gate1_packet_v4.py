#!/usr/bin/env python3
"""Revision 004 deterministic and fail-closed regressions; never candidate evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = ROOT / "poc_llm/tests/gate1"
LOCK = ROOT / "poc_llm/harness/gate1-lock-v4.json"
X86_RUNNER = ROOT / "poc_llm/tools/run_gate1_x86_prescreen_v4.py"
SELECTOR = ROOT / "poc_llm/tools/select_gate1_finalists_v4.py"
GATE2 = ROOT / "poc_llm/tools/run_m4b_gate.py"
FAKE_X86 = ROOT / "poc_llm/tests/gate1/fake_candidate.py"
FAKE_PI = ROOT / "poc_llm/tests/gate1/fake_pi_compat_candidate.py"
MODEL = ROOT / "poc_llm/tests/gate1/fake_model.artifact.txt"
CONFIG = ROOT / "poc_llm/tests/gate1/fake_config.json"
DEPS = ROOT / "poc_llm/requirements-gate1.lock"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_sha256(argv: list[str]) -> str:
    value = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


class Gate1PacketV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="gate1-v4-", dir=TEST_ROOT)
        cls.temp = Path(cls.temporary.name)
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.manifests: list[Path] = []
        cls.acquisitions: list[Path] = []
        cls.manifest_values: list[dict] = []
        cls.acquisition_values: list[dict] = []
        install = ["python3", "-c", "print('offline-install-self-test')"]
        for index in range(3):
            candidate_id = f"CAND-V4-RANK-{index}"
            pairing_revision = "test-only-v4"
            logical_runtime = {
                "name":"test-runtime", "version":"0.0-test",
                "source_sha256":sha256(FAKE_X86), "license":"test-only",
            }
            acquisition = {
                "acquisition_id":f"ACQ-V4-RANK-{index}", "candidate_id":candidate_id,
                "pairing_revision":pairing_revision, "logical_runtime":logical_runtime,
                "platforms":{
                    "ubuntu-x86_64":{
                        "runtime_artifact":{"path":relative(FAKE_X86),"sha256":sha256(FAKE_X86)},
                        "dependency_bundle":{"path":relative(DEPS),"sha256":sha256(DEPS)},
                        "install_argv":install,"install_argv_sha256":command_sha256(install),
                    },
                    "pi-debian13-aarch64":{
                        "runtime_artifact":{"path":relative(FAKE_PI),"sha256":sha256(FAKE_PI)},
                        "dependency_bundle":{"path":relative(DEPS),"sha256":sha256(DEPS)},
                        "install_argv":install,"install_argv_sha256":command_sha256(install),
                    },
                },
            }
            acquisition_path = cls.temp / f"acquisition-{index}.json"
            acquisition_path.write_text(json.dumps(acquisition), encoding="utf-8")
            x86_argv = [
                "python3", relative(FAKE_X86), "--catalog", "poc_llm/fixtures/gate1/catalog.json",
                "--candidate-id", candidate_id, "--runtime-sha", sha256(FAKE_X86),
                "--model-sha", sha256(MODEL), "--config-sha", sha256(CONFIG),
            ]
            pi_argv = [
                "python3", relative(FAKE_PI), "--candidate-id", candidate_id,
                "--runtime-version", logical_runtime["version"], "--runtime-sha", sha256(FAKE_PI),
                "--model-sha", sha256(MODEL), "--config-sha", sha256(CONFIG),
            ]
            manifest = {
                "candidate_id":candidate_id, "pairing_revision":pairing_revision,
                "logical_runtime":logical_runtime,
                "runtime":{"name":"x86-test-adapter","version":"1","path":relative(FAKE_X86),"sha256":sha256(FAKE_X86)},
                "model":{"name":"test-model","version":"1","path":relative(MODEL),"sha256":sha256(MODEL)},
                "config":{"name":"test-config","version":"1","path":relative(CONFIG),"sha256":sha256(CONFIG)},
                "quantization":"test-only","license":"test-only","offline":True,
                "acquisition_manifest":{"path":relative(acquisition_path),"sha256":sha256(acquisition_path)},
                "commands":{
                    "ubuntu-x86_64":{"argv":x86_argv,"sha256":command_sha256(x86_argv)},
                    "pi-debian13-aarch64":{"argv":pi_argv,"sha256":command_sha256(pi_argv)},
                },
            }
            manifest_path = cls.temp / f"candidate-{index}.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            cls.acquisitions.append(acquisition_path)
            cls.manifests.append(manifest_path)
            cls.acquisition_values.append(acquisition)
            cls.manifest_values.append(manifest)

        raw_dir = cls.temp / "baseline-raw"
        run = subprocess.run(
            ["python3", str(X86_RUNNER), "--run-id", "G1-X86-RUN-V4-BASELINE",
             "--candidate-manifest", str(cls.manifests[0]), "--lock", str(LOCK),
             "--raw-dir", str(raw_dir)],
            cwd=ROOT, check=False, capture_output=True, text=True, timeout=40,
        )
        if run.returncode != 0:
            raise AssertionError(run.stdout + run.stderr)
        cls.baseline = json.loads(run.stdout)
        cls.x86_paths = []
        for index, (manifest, acquisition) in enumerate(zip(cls.manifest_values, cls.acquisition_values)):
            value = copy.deepcopy(cls.baseline)
            value["run_id"] = f"G1-X86-RUN-V4-RANK-{index}"
            value["candidate_id"] = manifest["candidate_id"]
            value["pairing_revision"] = manifest["pairing_revision"]
            value["identity"].update({
                "manifest_sha256":sha256(cls.manifests[index]),
                "acquisition_manifest_sha256":sha256(cls.acquisitions[index]),
                "command_sha256":manifest["commands"]["ubuntu-x86_64"]["sha256"],
                "logical_runtime_source_sha256":manifest["logical_runtime"]["source_sha256"],
                "runtime_sha256":acquisition["platforms"]["ubuntu-x86_64"]["runtime_artifact"]["sha256"],
                "dependency_bundle_sha256":acquisition["platforms"]["ubuntu-x86_64"]["dependency_bundle"]["sha256"],
                "model_sha256":manifest["model"]["sha256"],"config_sha256":manifest["config"]["sha256"],
            })
            value["metrics"]["peak_rss_bytes"] += index
            result_path = cls.temp / f"x86-{index}.json"
            result_path.write_text(json.dumps(value), encoding="utf-8")
            cls.x86_paths.append(result_path)
        cls.preselection = cls.temp / "preselection.json"
        preselect = cls.run_selector("preselect")
        if preselect.returncode != 0:
            raise AssertionError(preselect.stdout + preselect.stderr)
        cls.preselection.write_text(preselect.stdout, encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def run_selector(
        cls, stage: str, pi_paths: list[Path] | None = None, x86_paths: list[Path] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "python3", str(SELECTOR), "--stage", stage,
            "--selection-cycle-id", "G1-CYCLE-V4-TEST", "--lock", str(LOCK),
            "--candidate-manifests", *map(str, cls.manifests),
            "--x86-results", *map(str, x86_paths or cls.x86_paths),
        ]
        if stage == "final":
            command.extend(["--preselection", str(cls.preselection), "--pi-results", *map(str, pi_paths or [])])
        return subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, timeout=30)

    @classmethod
    def pi_result(cls, index: int, result: str, name: str) -> Path:
        manifest, acquisition = cls.manifest_values[index], cls.acquisition_values[index]
        native = acquisition["platforms"]["pi-debian13-aarch64"]
        checks = {key:("PASS" if result == "PASS" else "Pending") for key in (
            "preselected","artifacts","offline_install","runtime_import","runtime_version","model_load",
            "ready","ping","minimal_generation","shutdown","exit","orphan_zero","isolated_cleanup",
        )}
        value = {
            "packet_id":"G1-X86-PI-COMPAT-004","test_id":"G1-PI-COMPAT-004",
            "selection_cycle_id":"G1-CYCLE-V4-TEST","run_id":f"G1-PI-RUN-V4-{index}-{name.upper()}",
            "candidate_id":manifest["candidate_id"],"pairing_revision":manifest["pairing_revision"],
            "platform":"pi5-4gb-debian13-aarch64","result":result,
            "identity":{
                "lock_sha256":sha256(LOCK),"manifest_sha256":sha256(cls.manifests[index]),
                "acquisition_manifest_sha256":sha256(cls.acquisitions[index]),
                "preselection_sha256":sha256(cls.preselection),
                "command_sha256":manifest["commands"]["pi-debian13-aarch64"]["sha256"],
                "logical_runtime_source_sha256":manifest["logical_runtime"]["source_sha256"],
                "runtime_sha256":native["runtime_artifact"]["sha256"],
                "dependency_bundle_sha256":native["dependency_bundle"]["sha256"],
                "model_sha256":manifest["model"]["sha256"],"config_sha256":manifest["config"]["sha256"],
                "pi_result_schema_sha256":cls.lock["artifacts"]["pi_result_schema"]["sha256"],
                "runner_sha256":cls.lock["artifacts"]["pi_runner"]["sha256"],
            },
            "environment":{
                "git_sha":"1" * 64,"git_clean":True,"os_id":"debian","os_version":"13",
                "machine":"aarch64","mem_total_bytes":4_246_470_656,
                "network_disabled_proof_sha256":"2" * 64,"raw_path_reused":False,
            },
            "checks":checks,
            "observations":{
                "swap_total_bytes":2_147_483_648,"mem_available_before_bytes":3_000_000_000,
                "mem_available_after_bytes":2_900_000_000,"disk_free_before_bytes":30_000_000_000,
                "disk_free_after_bytes":29_000_000_000,"elapsed_ms":1000.0,"informational_only":True,
            },
            "cleanup":{
                "exit_code":0 if result == "PASS" else None,"waited":result == "PASS",
                "term_sent":False,"kill_sent":False,"process_group_absent":True,
                "isolated_environment_removed":True,
            },
            "violations":[] if result == "PASS" else [f"synthetic {result.lower()}"],
        }
        path = cls.temp / f"pi-{index}-{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_x86_preselection_is_ranked_once_and_capped_at_two(self) -> None:
        value = json.loads(self.preselection.read_text(encoding="utf-8"))
        self.assertEqual(value["stage"], "PRESELECTION")
        self.assertEqual([item["candidate_id"] for item in value["preselected_candidates"]],
                         ["CAND-V4-RANK-0", "CAND-V4-RANK-1"])
        self.assertTrue(value["max_two_enforced"])
        self.assertTrue(value["backfill_forbidden"])

    def test_pi_pass_filters_without_gate2_credit(self) -> None:
        result = self.run_selector("final", [self.pi_result(0, "PASS", "pass"), self.pi_result(1, "FAIL", "fail")])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual([item["candidate_id"] for item in value["proposed_finalists"]], ["CAND-V4-RANK-0"])
        self.assertFalse(value["gate2_credit"])
        self.assertNotIn("CAND-V4-RANK-2", [item["candidate_id"] for item in value["proposed_finalists"]])

    def test_pi_fail_and_inconclusive_do_not_backfill_third(self) -> None:
        paths = [self.pi_result(0, "FAIL", "both-fail"), self.pi_result(1, "INCONCLUSIVE", "inconclusive")]
        result = self.run_selector("final", paths)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["proposed_finalists"], [])
        self.assertEqual(value["result"], "INCONCLUSIVE")
        self.assertTrue(value["backfill_forbidden"])

    def test_third_candidate_backfill_is_rejected(self) -> None:
        result = self.run_selector("final", [self.pi_result(2, "PASS", "third")])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("third-candidate backfill", result.stdout)

    def test_missing_or_forged_identity_is_rejected(self) -> None:
        value = json.loads(self.x86_paths[0].read_text(encoding="utf-8"))
        value["identity"]["manifest_sha256"] = "0" * 64
        forged = self.temp / "x86-forged.json"
        forged.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_selector("preselect", x86_paths=[forged, *self.x86_paths[1:]])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        decision = json.loads(result.stdout)
        self.assertNotIn("CAND-V4-RANK-0", [item["candidate_id"] for item in decision["preselected_candidates"]])
        self.assertTrue(any("identity mismatch" in item["reason"] for item in decision["rejected_pairings"]))

    def test_unapproved_platform_and_incomplete_p4_are_rejected(self) -> None:
        value = json.loads(self.x86_paths[0].read_text(encoding="utf-8"))
        value["platform"] = "ubuntu-aarch64"
        wrong_platform = self.temp / "x86-wrong-platform.json"
        wrong_platform.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_selector("preselect", x86_paths=[wrong_platform, *self.x86_paths[1:]])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

        value = json.loads(self.x86_paths[0].read_text(encoding="utf-8"))
        value["metrics"]["cold_total_ms"].pop()
        incomplete = self.temp / "x86-incomplete-p4.json"
        incomplete.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_selector("preselect", x86_paths=[incomplete, *self.x86_paths[1:]])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sample count is incomplete", result.stdout)

    def test_pi_cleanup_failure_is_rejected(self) -> None:
        path = self.pi_result(0, "PASS", "bad-cleanup")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["cleanup"]["process_group_absent"] = False
        path.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_selector("final", [path, self.pi_result(1, "PASS", "peer")])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_dirty_reused_x86_raw_path_is_non_pass(self) -> None:
        reused = self.temp / "reused-raw"
        reused.mkdir()
        result = subprocess.run(
            ["python3", str(X86_RUNNER), "--run-id", "G1-X86-RUN-V4-REUSED",
             "--candidate-manifest", str(self.manifests[0]), "--lock", str(LOCK),
             "--raw-dir", str(reused)],
            cwd=ROOT, check=False, capture_output=True, text=True, timeout=15,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(json.loads(result.stdout)["result"], "PASS")

    def test_gate1_evidence_cannot_be_ingested_as_gate2a(self) -> None:
        result = subprocess.run(
            ["python3", str(GATE2), "--gate", "2A",
             "--cases", "P1,P2,P3,P4,P5,P6,P7,P8,P10A,P11,P12", "--plan-only",
             "--source-packet-id", "G1-X86-PI-COMPAT-004",
             "--run-id", "G1-PI-RUN-V4-0-PASS", "--evidence-namespace", "evidence/gate1/pi"],
            cwd=ROOT, check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("carry-over is forbidden", result.stdout)


if __name__ == "__main__":
    unittest.main()
