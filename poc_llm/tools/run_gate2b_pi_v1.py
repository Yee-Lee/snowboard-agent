#!/usr/bin/env python3
"""Run the final Gate 2B real Audio -> LLM -> Audio validation on Pi 5."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, TextIO

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate2b_combined_v1 import Gate2BCombinedCoordinator
from poc_llm.harness.gate2b_resources_v1 import (
    ResourceSampler,
    evaluate_resources,
    oom_kill_count,
)
from poc_llm.harness.pi_artifact_auth import streaming_digest, verify_model_receipt
from poc_llm.harness.pi_runtime import (
    PiPacketFailure,
    group_absent,
    load,
    protocol_validator,
    stop,
    target_preflight,
)
from poc_llm.harness.pi_runtime_v2 import native_library_preflight_v2
from poc_llm.tools.run_gate1_pi_compat_v7 import close_child, generate, start_child


PACKET_ID = "G2B-PI-COMBINED-001"
CANDIDATES = (
    "CAND-LRT-G4E2B-MOBILE-R1",
    "CAND-LRT-Q25-15B-Q8-R1",
)
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EXPECTED_AUDIO_SESSIONS = [f"M4-SESSION-{index:02d}" for index in range(1, 21)]
FORBIDDEN_LOG = (
    "raw model output:", "BEGIN PRIVATE PROMPT", "SECRET_PAYLOAD",
    "credential=", "api_key=", "hidden context:", "LEAK_MARKER",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fatal-outcome-self-test", action="store_true")
    parser.add_argument("--packet-lock", type=Path, required=True)
    parser.add_argument("--gate2a-receipt", type=Path, required=True)
    parser.add_argument("--gate2a-result", type=Path, required=True)
    parser.add_argument("--artifact-receipt", type=Path, required=True)
    parser.add_argument("--accepted-audio-entry", type=Path, required=True)
    parser.add_argument("--execution-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--audio-fixture-dir", type=Path, required=True)
    parser.add_argument("--audio-fixture-lock", type=Path, required=True)
    parser.add_argument("--audio-artifact-dir", type=Path, required=True)
    parser.add_argument("--audio-runtime-python", type=Path, required=True)
    parser.add_argument("--audio-asr-binary", type=Path, required=True)
    parser.add_argument("--audio-asr-model", type=Path, required=True)
    parser.add_argument("--audio-vad-runtime-python", type=Path, required=True)
    parser.add_argument("--audio-vad-model", type=Path, required=True)
    parser.add_argument("--input-device", required=True)
    parser.add_argument("--output-device", required=True)
    parser.add_argument("--input-channel", type=int, choices=(0, 1), required=True)
    parser.add_argument("--operation-timeout", type=float, default=120.0)
    parser.add_argument("--cadence-seconds", type=float, default=5.0)
    return parser.parse_args()


def valid_run_id(value: str) -> bool:
    return RUN_ID_RE.fullmatch(value) is not None


def repo_artifact(item: dict[str, str]) -> Path:
    path = (ROOT / item["path"]).resolve()
    if not path.is_file() or streaming_digest(path) != item["sha256"]:
        raise PiPacketFailure(f"locked repository artifact mismatch: {item['path']}")
    return path


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PiPacketFailure("external Git identity probe failed")
    return completed.stdout.strip()


def verify_external_checkouts(
    audio_root: Path, core_root: Path, accepted: dict[str, Any]
) -> dict[str, str]:
    audio_root = audio_root.resolve()
    core_root = core_root.resolve()
    if (
        git_output(audio_root, "rev-parse", "HEAD") != accepted["completion_sha"]
        or git_output(audio_root, "status", "--porcelain")
        or git_output(audio_root, "rev-parse", f"refs/tags/{accepted['tag']}")
        != accepted["tag_object_sha"]
        or git_output(audio_root, "rev-list", "-n", "1", accepted["tag"])
        != accepted["completion_sha"]
    ):
        raise PiPacketFailure("Accepted Audio checkout identity mismatch")
    if (
        git_output(core_root, "rev-parse", "HEAD") != accepted["core_hal_execution_sha"]
        or git_output(core_root, "status", "--porcelain")
    ):
        raise PiPacketFailure("Accepted Core HAL checkout identity mismatch")
    return {
        "audio_completion_sha": accepted["completion_sha"],
        "audio_tag": accepted["tag"],
        "audio_tag_object_sha": accepted["tag_object_sha"],
        "core_hal_execution_sha": accepted["core_hal_execution_sha"],
    }


def verify_audio_kit(audio_root: Path, accepted: dict[str, Any]) -> dict[str, Any]:
    manifest_path = audio_root / "poc_audio/evidence/m4/M4-GATE2B-READY-001/manifest.json"
    if streaming_digest(manifest_path) != accepted["manifest_sha256"]:
        raise PiPacketFailure("Accepted Audio completion manifest mismatch")
    manifest = load(manifest_path)
    if (
        manifest.get("status") != "POC_ACCEPTED_M4_COMPLETE"
        or manifest.get("delivery_id") != accepted["delivery_id"]
        or manifest.get("repository", {}).get("corrected_delivery_sha")
        != accepted["corrected_delivery_sha"]
        or manifest.get("core_acceptance", {}).get("commit")
        != accepted["core_response_sha"]
    ):
        raise PiPacketFailure("Accepted Audio manifest authority mismatch")
    expected = accepted["conformance_kit"]
    kit = manifest.get("conformance_kit", {})
    mappings = {
        "packet": "packet_sha256",
        "packet_schema": "packet_schema_sha256",
        "result_schema": "result_schema_sha256",
        "runner": "runner_sha256",
    }
    for manifest_name, accepted_name in mappings.items():
        item = kit.get(manifest_name, {})
        path = audio_root / str(item.get("path", ""))
        if (
            item.get("sha256") != expected[accepted_name]
            or not path.is_file()
            or streaming_digest(path) != expected[accepted_name]
        ):
            raise PiPacketFailure("Accepted Audio conformance kit mismatch")
    return {
        "delivery_id": accepted["delivery_id"],
        "manifest_sha256": accepted["manifest_sha256"],
        "status": manifest["status"],
    }


def verify_gate2a_entry(
    receipt_path: Path,
    result_path: Path,
    receipt_schema: Path,
    gate2a_lock_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    gate2a = load(receipt_path)
    if not Draft202012Validator(load(receipt_schema)).is_valid(gate2a):
        raise PiPacketFailure("Gate 2A provisional receipt schema mismatch")
    lock_sha256 = streaming_digest(gate2a_lock_path)
    if (
        gate2a["gate2a_lock_sha256"] != lock_sha256
        or gate2a["execution_surface_sha256"] != lock_sha256
    ):
        raise PiPacketFailure("Gate 2A execution lock identity mismatch")
    gate2a_lock = load(gate2a_lock_path)
    gate2a_result_schema = repo_artifact(
        gate2a_lock["artifacts"]["result_schema"]
    )
    gate1_entry = repo_artifact(gate2a_lock["artifacts"]["gate1_entry"])
    gate2a_result = load(result_path)
    if (
        streaming_digest(result_path) != gate2a["candidate_result_sha256"]
        or streaming_digest(gate1_entry) != gate2a["gate1_entry_sha256"]
        or not Draft202012Validator(load(gate2a_result_schema)).is_valid(gate2a_result)
        or gate2a_result.get("candidate_id") != gate2a["candidate_id"]
        or gate2a_result.get("execution_sha") != gate2a["execution_sha"]
        or gate2a_result.get("execution_surface_sha256")
        != gate2a["execution_surface_sha256"]
        or gate2a_result.get("artifact_authentication", {}).get(
            "reused_receipt_sha256"
        ) != gate2a["artifact_receipt_sha256"]
    ):
        raise PiPacketFailure("Gate 2A reviewed result chain mismatch")
    combined_p_results = {
        **gate2a_result["carried_results"],
        **gate2a_result["executed_results"],
    }
    for item, disposition in gate2a["p_results"].items():
        observed = combined_p_results[item]
        if item == "P4" and disposition == "CORE_THRESHOLD_ACCEPTED":
            if observed != "Core threshold decision required":
                raise PiPacketFailure("Gate 2A P4 threshold receipt mismatch")
        elif observed != disposition:
            raise PiPacketFailure("Gate 2A P-item receipt mismatch")
    return gate2a, gate2a_result


def load_audio_bindings(audio_root: Path) -> dict[str, Any]:
    source_root = (audio_root / "poc_audio/src").resolve()
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    from audio_poc.m3_core_hal import make_alsa_config
    from audio_poc.m4_combined_domains import (
        PersistentAsrDomain,
        PersistentTtsDomain,
        PersistentVadDomain,
    )
    from audio_poc.m4_fixture_lock import load_fixture_lock, verify_fixture_files

    return {
        "make_alsa_config": make_alsa_config,
        "PersistentAsrDomain": PersistentAsrDomain,
        "PersistentTtsDomain": PersistentTtsDomain,
        "PersistentVadDomain": PersistentVadDomain,
        "load_fixture_lock": load_fixture_lock,
        "verify_fixture_files": verify_fixture_files,
    }


class TranscriptAsrDomain:
    """Expose the accepted ASR hypothesis only to the in-memory LLM boundary."""

    def __init__(self, accepted_domain: Any):
        self.accepted = accepted_domain

    async def start(self) -> None:
        await self.accepted.start()

    async def stop(self) -> None:
        await self.accepted.stop()

    def residency_identity(self) -> dict[str, Any]:
        return self.accepted.residency_identity()

    async def run(self, session: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._run, session)

    def _run(self, session: dict[str, Any]) -> dict[str, Any]:
        worker = self.accepted.worker
        bounded = session.get("bounded_wav")
        if worker is None or not isinstance(bounded, Path) or not bounded.is_file():
            raise RuntimeError("Gate 2B accepted ASR is unavailable")
        metrics = worker.transcribe(bounded, self.accepted.timeout)
        transcript = str(metrics.pop("hypothesis"))
        if not transcript.strip():
            raise RuntimeError("Gate 2B accepted ASR returned an empty transcript")
        return {
            "session_id": session["session_id"],
            "terminal": "SUCCESS",
            "transcript": transcript,
            "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "latency_ms": metrics["latency_ms"],
        }


class CombinedLlmDomain:
    def __init__(
        self,
        *,
        common: dict[str, Any],
        stderr: TextIO,
        engine_capacity: int,
    ) -> None:
        self.common = common
        self.stderr = stderr
        self.engine_capacity = engine_capacity
        self.process: subprocess.Popen[str] | None = None
        self.prior_markers: list[str] = []
        self.ready_ms: float | None = None
        self.cleanup: dict[str, Any] = {}

    async def start(self) -> None:
        self.process, self.ready_ms = await asyncio.to_thread(
            start_child, **self.common, stderr=self.stderr
        )

    def residency_identity(self) -> dict[str, Any]:
        return {
            "pid": self.process.pid if self.process is not None else None,
            "alive": self.process is not None and self.process.poll() is None,
        }

    async def run(
        self, session_id: str, transcript: str, nonce: str, trap: str
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._run, session_id, transcript, nonce, trap
        )

    def _run(
        self, session_id: str, transcript: str, nonce: str, trap: str
    ) -> dict[str, Any]:
        if self.process is None:
            raise RuntimeError("Gate 2B LLM is not resident")
        value = {
            "perceptions": [{
                "kind": "listen",
                "status": "ok",
                "text": (
                    transcript
                    + f"\nReply briefly in spoken form and include current session marker {nonce} "
                    + f"exactly once. Never mention trap {trap} or an earlier session marker."
                ),
            }],
            "pending_message_count": 0,
            "capabilities": {
                "perceptions": ["listen"],
                "actions": ["speak"],
                "tools": [],
            },
        }
        terminal, _wall_ms = generate(
            self.process, self.common["validator"], session_id, value,
            timeout_s=15.0,
        )
        response = terminal.get("response", {})
        speech = response.get("action_payload", {}).get("text")
        metrics = terminal.get("metrics", {})
        metric_types = all(
            isinstance(metrics.get(name), int)
            for name in ("prefill_tokens", "decode_tokens", "kv_tokens")
        )
        if (
            terminal.get("type") != "RESULT"
            or terminal.get("request_id") != session_id
            or response.get("action_kind") != "speak"
            or not isinstance(speech, str)
            or not speech.strip()
            or not metric_types
            or metrics["kv_tokens"] <= 0
            or metrics["kv_tokens"] > self.engine_capacity
            or metrics["kv_tokens"]
            > metrics["prefill_tokens"] + metrics["decode_tokens"] + 16
        ):
            raise RuntimeError("Gate 2B LLM product result or single-turn metric invalid")
        prior_leak = any(marker in speech for marker in self.prior_markers)
        current_marker_present = speech.count(nonce) == 1
        current_trap_absent = trap not in speech
        self.prior_markers.extend([nonce, trap])
        return {
            "session_id": session_id,
            "terminal": "SUCCESS",
            "request_id": terminal["request_id"],
            "speech_text": speech,
            "speech_sha256": hashlib.sha256(speech.encode("utf-8")).hexdigest(),
            "response_sha256": hashlib.sha256(
                json.dumps(response, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "prior_marker_leaked": prior_leak,
            "current_marker_present_once": current_marker_present,
            "current_trap_absent": current_trap_absent,
            "metrics": metrics,
        }

    async def stop(self) -> None:
        if self.process is None:
            return
        process = self.process
        try:
            self.cleanup = await asyncio.to_thread(
                close_child, process, self.common["validator"]
            )
        except Exception:
            self.cleanup = stop(process)
            if not self.cleanup.get("process_group_absent"):
                raise RuntimeError("Gate 2B LLM cleanup failed")
        finally:
            self.process = None


def scan_log(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(marker in text for marker in FORBIDDEN_LOG):
        raise PiPacketFailure("Gate 2B LLM log hygiene failure")


def audio_device_owner_count() -> int:
    devices = sorted(Path("/dev/snd").glob("*"))
    if not devices:
        raise PiPacketFailure("Gate 2B ALSA devices unavailable")
    completed = subprocess.run(
        ["fuser", *(str(path) for path in devices)],
        capture_output=True, text=True, check=False,
    )
    return 1 if completed.returncode == 0 else 0


def preexisting_worker_count(asr_binary: Path) -> int:
    count = 0
    expected_asr = asr_binary.resolve()
    for process_dir in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(process_dir.name)
            if pid == os.getpid():
                continue
            cmdline = (process_dir / "cmdline").read_bytes().replace(b"\0", b" ")
            executable = (process_dir / "exe").resolve()
        except (OSError, ValueError):
            continue
        if (
            b"litert_lm_pi_child_adapter" in cmdline
            or b"audio_poc.m4_vad_worker" in cmdline
            or b"audio_poc.m3_tts_worker" in cmdline
            or executable == expected_asr
        ):
            count += 1
    return count


def initial_result(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "packet_id": PACKET_ID,
        "run_id": args.run_id,
        "candidate_id": "UNKNOWN",
        "execution_sha": args.execution_sha,
        "execution_surface_sha256": "",
        "gate2a_receipt_sha256": "",
        "accepted_audio": {},
        "environment": {},
        "environment_post": {},
        "runtime": {},
        "artifact_authentication": {},
        "sessions": [],
        "soak": {},
        "resources": {},
        "cleanup": {},
        "p_results": {"P9": "Blocked", "P10B": "Blocked"},
        "violations": [],
        "result": "INCONCLUSIVE",
        "publication_status": "REVIEW_REQUIRED",
    }


def combined_exception_disposition(
    *, combined_entered: bool, sessions_completed: bool
) -> tuple[dict[str, str], str]:
    if combined_entered and not sessions_completed:
        return {"P9": "Blocked", "P10B": "FAIL"}, "FAIL"
    return {"P9": "Blocked", "P10B": "Blocked"}, "INCONCLUSIVE"


def main() -> int:
    if sys.argv[1:] == ["--fatal-outcome-self-test"]:
        return 4
    args = parse_args()
    if args.fatal_outcome_self_test:
        return 4
    result = initial_result(args)
    if not valid_run_id(args.run_id):
        result["violations"].append("Gate 2B run ID is not a safe slug")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    raw_dir = args.evidence_root / args.run_id
    install_root = Path(f"/tmp/llm-poc-g2b-001/install-{args.run_id}")
    work_dir = Path(f"/tmp/llm-poc-g2b-001/work-{args.run_id}")
    result_schema: Path | None = None
    receipt: dict[str, Any] | None = None
    standard_value: dict[str, Any] | None = None
    sampler: ResourceSampler | None = None
    samples: list[dict[str, Any]] = []
    llm_domain: CombinedLlmDomain | None = None
    coordinator: Gate2BCombinedCoordinator | None = None
    roots_after: dict[str, int] = {}
    owns_raw_dir = False
    owns_install_root = False
    owns_work_dir = False
    combined_entered = False
    sessions_completed = False
    try:
        if raw_dir.exists() or install_root.exists() or work_dir.exists():
            raise PiPacketFailure("Gate 2B run-owned path is dirty")
        if raw_dir.resolve().is_relative_to(ROOT):
            raise PiPacketFailure("Gate 2B controlled evidence must remain outside Git")
        audio_root_resolved = args.audio_root.resolve()
        for path in (
            args.audio_fixture_dir, args.audio_fixture_lock, args.audio_artifact_dir,
        ):
            if path.resolve().is_relative_to(audio_root_resolved):
                raise PiPacketFailure("Gate 2B controlled Audio input must remain outside Git")
        if (
            os.environ.get("OPENBLAS_NUM_THREADS") != "1"
            or os.environ.get("PYTHONNOUSERSITE") != "1"
        ):
            raise PiPacketFailure("Gate 2B controller environment policy mismatch")
        if args.cadence_seconds != 5.0 or args.operation_timeout != 120.0:
            raise PiPacketFailure("Gate 2B cadence/operation timeout drift")
        if any(
            not value.startswith("hw:") or value.startswith("plughw:")
            for value in (args.input_device, args.output_device)
        ):
            raise PiPacketFailure("Gate 2B requires direct hw: ALSA devices")
        lock = load(args.packet_lock)
        if (
            lock.get("packet_id") != PACKET_ID
            or lock.get("session_count") != 20
            or lock.get("cadence_seconds") != 5
            or lock.get("fault_schedule") != []
            or lock.get("thresholds") != {
                "system_used_mib_max": 3584,
                "temperature_c_max_exclusive": 80,
                "sample_interval_seconds": 0.25,
                "sample_gap_seconds_max": 0.5,
                "psi_full_total_delta": 0,
                "oom_kill_delta": 0,
            }
        ):
            raise PiPacketFailure("Gate 2B lock identity mismatch")
        result["execution_surface_sha256"] = streaming_digest(args.packet_lock)
        artifacts = {
            name: repo_artifact(item) for name, item in lock["artifacts"].items()
        }
        result_schema = artifacts["result_schema"]

        accepted_path = artifacts["accepted_audio_entry"]
        if args.accepted_audio_entry.resolve() != accepted_path:
            raise PiPacketFailure("Accepted Audio entry path mismatch")
        accepted = load(accepted_path)
        if not Draft202012Validator(load(artifacts["accepted_audio_entry_schema"])).is_valid(accepted):
            raise PiPacketFailure("Accepted Audio entry schema mismatch")
        result["accepted_audio"] = {
            **verify_external_checkouts(args.audio_root, args.core_root, accepted),
            **verify_audio_kit(args.audio_root, accepted),
            "core_response_id": accepted["core_response_id"],
            "core_response_sha": accepted["core_response_sha"],
        }

        gate2a, _gate2a_result = verify_gate2a_entry(
            args.gate2a_receipt,
            args.gate2a_result,
            artifacts["gate2a_receipt_schema"],
            artifacts["gate2a_lock"],
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", gate2a["execution_sha"], args.execution_sha],
            cwd=ROOT, capture_output=True, check=False,
        )
        if ancestor.returncode != 0:
            raise PiPacketFailure("Gate 2A execution SHA is not an ancestor")
        candidate_id = gate2a["candidate_id"]
        result["candidate_id"] = candidate_id
        result["gate2a_receipt_sha256"] = streaming_digest(args.gate2a_receipt)
        candidate = lock["candidates"].get(candidate_id)
        if candidate is None:
            raise PiPacketFailure("Gate 2B candidate is not frozen")

        result["environment"] = target_preflight(args.execution_sha)
        preexisting_workers = preexisting_worker_count(args.audio_asr_binary)
        preexisting_audio_owners = audio_device_owner_count()
        if preexisting_workers or preexisting_audio_owners:
            raise PiPacketFailure("Gate 2B pre-existing worker/device ownership detected")
        result["environment"].update({
            "preexisting_combined_workers": preexisting_workers,
            "preexisting_audio_device_owners": preexisting_audio_owners,
        })
        raw_dir.mkdir(parents=True, exist_ok=False)
        owns_raw_dir = True
        work_dir.mkdir(parents=True, exist_ok=False)
        owns_work_dir = True
        runtime = lock["runtime"]
        owns_install_root = True
        install = subprocess.run(
            [
                "python3", str(artifacts["installer"]),
                "--wheel", runtime["wheel_path"],
                "--wheel-sha256", runtime["wheel_sha256"],
                "--target", str(install_root),
            ],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=300,
        )
        (raw_dir / "offline-install.stdout").write_text(install.stdout, encoding="utf-8")
        (raw_dir / "offline-install.stderr").write_text(install.stderr, encoding="utf-8")
        if install.returncode != 0 or json.loads(install.stdout).get("result") != "PASS":
            raise PiPacketFailure("Gate 2B offline LLM runtime installation failed")
        result["runtime"] = native_library_preflight_v2(
            install_root / "litert_lm/liblitert-lm.so",
            runtime["native_library_sha256"],
        )

        product_config = repo_artifact(candidate["product_config"])
        standard_value = load(product_config)
        receipt_schema = artifacts["artifact_receipt_schema"]
        receipt = load(args.artifact_receipt)
        if not Draft202012Validator(load(receipt_schema)).is_valid(receipt):
            raise PiPacketFailure("Gate 2B LLM artifact receipt schema mismatch")
        if (
            streaming_digest(args.artifact_receipt) != gate2a["artifact_receipt_sha256"]
            or receipt["candidate_id"] != candidate_id
            or receipt["model"]["sha256"] != standard_value["model_sha256"]
            or receipt["runtime_sha256"] != runtime["wheel_sha256"]
        ):
            raise PiPacketFailure("Gate 2B LLM receipt/candidate mismatch")
        verify_model_receipt(
            receipt["model"], Path(standard_value["model_path"]),
            standard_value["model_sha256"],
        )
        result["artifact_authentication"] = {
            "reused_receipt_sha256": streaming_digest(args.artifact_receipt),
            "model_sha256": receipt["model"]["sha256"],
            "model_size_bytes": receipt["model"]["size_bytes"],
            "full_model_hash_count": 0,
            "metadata_unchanged": False,
        }

        bindings = load_audio_bindings(args.audio_root)
        fixture_lock = bindings["load_fixture_lock"](
            args.audio_fixture_lock, accepted["p9_combined_execution_sha"]
        )
        bindings["verify_fixture_files"](fixture_lock, args.audio_fixture_dir)
        if [record.get("session_id") for record in fixture_lock["records"]] != EXPECTED_AUDIO_SESSIONS:
            raise PiPacketFailure("Accepted Audio 20-session catalog mismatch")
        records = [
            {**record, "wav_path": args.audio_fixture_dir / record["filename"]}
            for record in fixture_lock["records"]
        ]

        audio, audio_config = bindings["make_alsa_config"](
            args.core_root, args.input_device, args.output_device, args.input_channel
        )
        vad = bindings["PersistentVadDomain"](
            args.audio_root, args.audio_vad_runtime_python, args.audio_vad_model,
            work_dir / "vad-bounded", args.operation_timeout,
        )
        accepted_asr = bindings["PersistentAsrDomain"](
            args.audio_asr_binary, args.audio_asr_model,
            work_dir / "asr", args.operation_timeout,
        )
        asr = TranscriptAsrDomain(accepted_asr)
        tts = bindings["PersistentTtsDomain"](
            args.audio_root, args.audio_artifact_dir, args.audio_runtime_python,
            work_dir / "tts", audio, audio_config, args.operation_timeout,
        )

        protocol = artifacts["protocol_schema"]
        prompt_schema = artifacts["prompt_schema"]
        response_schema = artifacts["response_schema"]
        validator = protocol_validator(protocol, prompt_schema, response_schema)
        common = {
            "config": product_config,
            "config_sha256": candidate["product_config"]["sha256"],
            "config_value": standard_value,
            "config_schema": artifacts["product_config_schema"],
            "protocol_schema": protocol,
            "prompt_schema": prompt_schema,
            "response_schema": response_schema,
            "receipt": args.artifact_receipt,
            "receipt_schema": receipt_schema,
            "install_root": install_root,
            "validator": validator,
        }
        llm_stderr_path = raw_dir / "llm.stderr"
        oom_before = oom_kill_count()
        with llm_stderr_path.open("w", encoding="utf-8") as llm_stderr:
            llm_domain = CombinedLlmDomain(
                common=common,
                stderr=llm_stderr,
                engine_capacity=standard_value["engine_max_num_tokens"],
            )
            coordinator = Gate2BCombinedCoordinator(
                vad, asr, llm_domain, tts, pause=asyncio.sleep
            )
            sampler = ResourceSampler(
                lambda: {"controller": os.getpid(), **coordinator.residency_roots()},
                interval_s=0.25,
            )

            def start_sampling() -> None:
                nonlocal combined_entered
                sampler.start()
                combined_entered = True

            def stop_sampling() -> None:
                nonlocal samples, roots_after
                roots_after = coordinator.residency_roots()
                samples = sampler.stop()

            sessions = asyncio.run(coordinator.run(
                records,
                cadence_s=args.cadence_seconds,
                on_resident=start_sampling,
                before_shutdown=stop_sampling,
            ))
            sessions_completed = True
        oom_after = oom_kill_count()
        resources_pass, resource_summary = evaluate_resources(
            samples, oom_before=oom_before, oom_after=oom_after
        )
        (raw_dir / "resource-samples.json").write_text(
            json.dumps(samples, sort_keys=True), encoding="utf-8"
        )
        result["sessions"] = sessions
        result["resources"] = resource_summary
        result["soak"] = {
            "cadence_seconds": args.cadence_seconds,
            "pause_count": len(coordinator.cadence_pause_elapsed_ms),
            "pause_elapsed_ms": coordinator.cadence_pause_elapsed_ms,
            "total_elapsed_ms": coordinator.total_elapsed_ms,
        }
        process_absence = {
            name: group_absent(pid) for name, pid in roots_after.items()
        }
        result["cleanup"] = {
            "reverse_order": coordinator.stop_order,
            "process_groups_absent": process_absence,
            "audio_device_owner_count": audio_device_owner_count(),
            "llm": llm_domain.cleanup,
        }
        p10b_pass = (
            len(sessions) == 20
            and [item["session_id"] for item in sessions] == EXPECTED_AUDIO_SESSIONS
            and all(
                item["vad"]["terminal"] == "SUCCESS"
                and item["asr"]["terminal"] == "SUCCESS"
                and item["llm"]["terminal"] == "SUCCESS"
                and item["llm"]["request_id"] == item["session_id"]
                and item["llm"]["prior_marker_leaked"] is False
                and item["llm"]["current_marker_present_once"] is True
                and item["llm"]["current_trap_absent"] is True
                and item["tts"]["terminal"] == "SUCCESS"
                and item["tts"]["playback_complete"] is True
                for item in sessions
            )
            and coordinator.stop_order == ["llm", "tts", "asr", "vad"]
            and len(coordinator.cadence_pause_elapsed_ms) == 19
            and all(value >= 5000 for value in coordinator.cadence_pause_elapsed_ms)
            and all(process_absence.values())
            and result["cleanup"]["audio_device_owner_count"] == 0
        )
        try:
            scan_log(llm_stderr_path)
        except PiPacketFailure as hygiene_error:
            result["violations"].append(str(hygiene_error))
            p10b_pass = False
        result["p_results"]["P9"] = "PASS" if resources_pass else "FAIL"
        result["p_results"]["P10B"] = "PASS" if p10b_pass and resources_pass else "FAIL"
        verify_model_receipt(
            receipt["model"], Path(standard_value["model_path"]),
            standard_value["model_sha256"],
        )
        result["artifact_authentication"]["metadata_unchanged"] = True
        result["environment_post"] = target_preflight(args.execution_sha)
        result["result"] = (
            "PASS" if result["p_results"] == {"P9": "PASS", "P10B": "PASS"}
            else "FAIL"
        )
    except (
        PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, TypeError,
        ValueError, RuntimeError, json.JSONDecodeError,
    ) as error:
        result["violations"].append(str(error))
        result["p_results"], result["result"] = combined_exception_disposition(
            combined_entered=combined_entered,
            sessions_completed=sessions_completed,
        )
        if combined_entered and coordinator is not None:
            result["cleanup"]["reverse_order"] = coordinator.stop_order
            if roots_after:
                result["cleanup"]["process_groups_absent"] = {
                    name: group_absent(pid) for name, pid in roots_after.items()
                }
            try:
                result["cleanup"]["audio_device_owner_count"] = audio_device_owner_count()
            except PiPacketFailure as cleanup_error:
                result["violations"].append(str(cleanup_error))
    finally:
        if sampler is not None and sampler._thread is not None and sampler._thread.is_alive():
            try:
                samples = sampler.stop()
            except Exception as error:
                result["violations"].append(str(error))
        if llm_domain is not None and llm_domain.process is not None:
            cleanup = stop(llm_domain.process)
            result["cleanup"]["forced_llm"] = cleanup
        if receipt is not None and standard_value is not None:
            try:
                verify_model_receipt(
                    receipt["model"], Path(standard_value["model_path"]),
                    standard_value["model_sha256"],
                )
            except Exception as error:
                result["violations"].append(str(error))
                result["result"] = "INCONCLUSIVE"
        if owns_install_root and install_root.exists():
            shutil.rmtree(install_root)
        if owns_work_dir and work_dir.exists():
            shutil.rmtree(work_dir)
        if owns_raw_dir and raw_dir.exists():
            resource_samples = raw_dir / "resource-samples.json"
            if samples and not resource_samples.exists():
                resource_samples.write_text(
                    json.dumps(samples, sort_keys=True), encoding="utf-8"
                )
            if result_schema is not None:
                errors = list(Draft202012Validator(load(result_schema)).iter_errors(result))
                if errors:
                    result["violations"].append("Gate 2B result schema validation failed")
                    result["result"] = "INCONCLUSIVE"
            (raw_dir / "gate2b-sanitized.json").write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8"
            )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
