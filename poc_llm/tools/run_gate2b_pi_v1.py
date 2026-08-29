#!/usr/bin/env python3
"""Run the final Gate 2B real Audio -> LLM -> Audio validation on Pi 5."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
from typing import Any, TextIO

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_llm.harness.gate2b_combined_v1 import Gate2BCombinedCoordinator
from poc_llm.harness.gate2_errors_v1 import (
    CandidateViolation,
    CleanupViolation,
    EnvironmentInvalid,
    EvidenceInvalid,
    PacketDefect,
    error_result,
    sanitized_error,
    write_json_evidence,
)
from poc_llm.harness.gate2b_resources_v1 import (
    ResourceSampler,
    evaluate_resources,
    oom_kill_count,
    resource_sample,
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
from poc_llm.harness.pi_runtime_v2 import native_library_preflight_v2, require_ready_v2
from poc_llm.tools.run_gate1_pi_compat_v7 import close_child, generate
from poc_llm.tools.run_gate2a_pi_v2 import verify_gate2a_result


PACKET_ID = "G2B-PI-COMBINED-001"
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EXPECTED_AUDIO_SESSIONS = [f"M4-SESSION-{index:02d}" for index in range(1, 21)]
FORBIDDEN_LOG = (
    "raw model output:", "BEGIN PRIVATE PROMPT", "SECRET_PAYLOAD",
    "credential=", "api_key=", "hidden context:", "LEAK_MARKER",
)
SCORED_PIPE_ERRORS = (PiPacketFailure, BrokenPipeError, ConnectionResetError, UnicodeError)


def scored_generate(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], float]:
    """Classify a READY LLM's scored timeout/EOF/frame defect as candidate behavior."""

    try:
        return generate(*args, **kwargs)
    except SCORED_PIPE_ERRORS as error:
        raise CandidateViolation("post-READY scored protocol failure") from error


def require_resource_probe_preflight() -> None:
    """Fail before residency when the frozen P9 probes are unavailable."""

    try:
        resource_sample({"controller": os.getpid()}, time.monotonic())
        oom_kill_count()
    except (OSError, KeyError, RuntimeError, ValueError) as error:
        raise EnvironmentInvalid("Gate 2B resource probes unavailable before residency") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fatal-outcome-self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--diagnostic-session-only", action="store_true")
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
    parser.add_argument("--audio-fixture-manifest", type=Path, required=True)
    parser.add_argument("--audio-artifact-dir", type=Path, required=True)
    parser.add_argument("--audio-controller-closure", type=Path, required=True)
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


def start_gate2b_child(
    *,
    adapter: Path,
    config: Path,
    config_sha256: str,
    config_value: dict[str, Any],
    config_schema: Path,
    protocol_schema: Path,
    prompt_schema: Path,
    response_schema: Path,
    receipt: Path,
    receipt_schema: Path,
    install_root: Path,
    validator: Draft202012Validator,
    stderr: TextIO,
) -> tuple[subprocess.Popen[str], float]:
    """Launch only the frozen Gate 2B prompt adapter."""

    argv = [
        "env", f"PYTHONPATH={install_root}", "python3", str(adapter),
        "--config", str(config), "--config-sha256", config_sha256,
        "--config-schema", str(config_schema),
        "--config-schema-sha256", streaming_digest(config_schema),
        "--protocol-schema", str(protocol_schema),
        "--protocol-schema-sha256", streaming_digest(protocol_schema),
        "--prompt-schema", str(prompt_schema),
        "--prompt-schema-sha256", streaming_digest(prompt_schema),
        "--response-schema", str(response_schema),
        "--response-schema-sha256", streaming_digest(response_schema),
        "--artifact-receipt", str(receipt),
        "--artifact-receipt-sha256", streaming_digest(receipt),
        "--artifact-receipt-schema", str(receipt_schema),
        "--artifact-receipt-schema-sha256", streaming_digest(receipt_schema),
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr,
        text=True,
        start_new_session=True,
        env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )
    try:
        require_ready_v2(process, validator, config_value, config_sha256)
    except Exception:
        stop(process)
        raise
    return process, round((time.monotonic() - started) * 1000, 3)


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


def verify_audio_runtime(
    runtime_python: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    """Authenticate one accepted isolated Audio runtime before residency timing."""

    venv_config = runtime_python.parent.parent / "pyvenv.cfg"
    if (
        not runtime_python.is_file()
        or not venv_config.is_file()
        or "include-system-site-packages = false"
        not in venv_config.read_text(encoding="utf-8")
    ):
        raise PiPacketFailure("Accepted Audio runtime isolation mismatch")
    probe = subprocess.run(
        [
            str(runtime_python),
            "-c",
            (
                "import importlib.metadata as m,json,platform,sys;"
                "print(json.dumps({'package':sys.argv[1],"
                "'version':m.version(sys.argv[1]),"
                "'python_version':platform.python_version(),"
                "'isolated':sys.prefix!=sys.base_prefix},sort_keys=True))"
            ),
            expected["package"],
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={
            **os.environ,
            "PIP_NO_INDEX":"1",
            "HF_HUB_OFFLINE":"1",
            "TRANSFORMERS_OFFLINE":"1",
            "NO_PROXY":"*",
        },
    )
    try:
        observed = json.loads(probe.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise PiPacketFailure("Accepted Audio runtime identity probe failed") from error
    if probe.returncode != 0 or observed != expected:
        raise PiPacketFailure("Accepted Audio runtime identity mismatch")
    return observed


def verify_audio_controller_runtime(
    closure_root: Path, expected: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    """Authenticate and expose the accepted Audio controller closure.

    The Gate 2B runner keeps its own system jsonschema dependency, but Core HAL
    imports must resolve from the isolated, manifest-locked Audio controller
    venv.  This check runs before any model or domain becomes resident.
    """

    closure_root = closure_root.resolve()
    manifest_path = closure_root / "manifest.json"
    wheel_dir = closure_root / "wheels"
    venv = closure_root / "venv"
    venv_python = venv / "bin/python"
    venv_config = venv / "pyvenv.cfg"
    if (
        not manifest_path.is_file()
        or streaming_digest(manifest_path) != expected["manifest_sha256"]
        or not wheel_dir.is_dir()
        or not venv_python.is_file()
        or not venv_config.is_file()
        or "include-system-site-packages = false"
        not in venv_config.read_text(encoding="utf-8")
    ):
        raise PiPacketFailure("Accepted Audio controller closure identity mismatch")
    manifest = load(manifest_path)
    packages = manifest.get("packages")
    interpreter = manifest.get("interpreter", {})
    if (
        manifest.get("schema") != "sbd.m4a.runtime-closure.v1"
        or manifest.get("runtime") != expected["runtime"]
        or interpreter.get("version") != expected["python_version"]
        or not isinstance(packages, list)
        or not packages
    ):
        raise PiPacketFailure("Accepted Audio controller manifest mismatch")
    filenames: set[str] = set()
    package_probe: list[dict[str, str]] = []
    for item in packages:
        if not isinstance(item, dict):
            raise PiPacketFailure("Accepted Audio controller package record mismatch")
        filename = item.get("filename")
        distribution = item.get("distribution")
        version = item.get("version")
        import_name = item.get("import_name")
        size = item.get("size")
        sha256 = item.get("sha256")
        if (
            not all(
                isinstance(value, str) and value
                for value in (filename, distribution, version, import_name, sha256)
            )
            or not isinstance(size, int)
            or size <= 0
        ):
            raise PiPacketFailure("Accepted Audio controller package record mismatch")
        wheel = wheel_dir / filename
        if (
            not wheel.is_file()
            or wheel.stat().st_size != size
            or streaming_digest(wheel) != sha256
        ):
            raise PiPacketFailure("Accepted Audio controller wheel mismatch")
        filenames.add(filename)
        package_probe.append({
            "distribution": distribution,
            "version": version,
            "import_name": import_name,
        })
    if {path.name for path in wheel_dir.glob("*.whl")} != filenames:
        raise PiPacketFailure("Accepted Audio controller wheel inventory mismatch")

    probe_code = (
        "import importlib,importlib.metadata as m,json,platform,sys;"
        "from pathlib import Path;"
        "items=json.loads(sys.argv[1]);"
        "locations={i['import_name']:str(Path(importlib.import_module(i['import_name'])"
        ".__file__).resolve()) for i in items};"
        "versions={i['distribution']:m.version(i['distribution']) for i in items};"
        "print(json.dumps({'python_version':platform.python_version(),"
        "'prefix':str(Path(sys.prefix).resolve()),"
        "'base_prefix':str(Path(sys.base_prefix).resolve()),"
        "'locations':locations,'versions':versions},sort_keys=True))"
    )
    probe = subprocess.run(
        [str(venv_python), "-I", "-c", probe_code, json.dumps(package_probe)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PIP_NO_INDEX": "1",
            "NO_PROXY": "*",
        },
    )
    try:
        observed = json.loads(probe.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise PiPacketFailure("Accepted Audio controller import probe failed") from error
    expected_versions = {
        item["distribution"]: item["version"] for item in package_probe
    }
    prefix = Path(str(observed.get("prefix", ""))).resolve()
    locations = observed.get("locations")
    if (
        probe.returncode != 0
        or observed.get("python_version") != expected["python_version"]
        or prefix != venv
        or observed.get("base_prefix") == observed.get("prefix")
        or observed.get("versions") != expected_versions
        or not isinstance(locations, dict)
        or any(not Path(value).resolve().is_relative_to(venv) for value in locations.values())
    ):
        raise PiPacketFailure("Accepted Audio controller import identity mismatch")
    python_major_minor = ".".join(expected["python_version"].split(".")[:2])
    site_packages = venv / "lib" / f"python{python_major_minor}" / "site-packages"
    if not site_packages.is_dir() or any(
        name.split(".", 1)[0] in sys.modules
        for name in (item["import_name"] for item in package_probe)
    ):
        raise PiPacketFailure("Accepted Audio controller activation order mismatch")
    sys.path.insert(0, str(site_packages))
    return dict(expected), site_packages


def verify_audio_controlled_inputs(
    *,
    fixture_lock: Path,
    fixture_manifest: Path,
    artifact_dir: Path,
    controller_closure: Path,
    tts_runtime_python: Path,
    asr_binary: Path,
    asr_model: Path,
    vad_runtime_python: Path,
    vad_model: Path,
    accepted: dict[str, Any],
) -> dict[str, Any]:
    """Pin every external Audio input before any model becomes resident."""

    controlled = accepted["controlled_inputs"]
    finalists = accepted["finalists"]
    expected_files = {
        "fixture_lock_sha256": (fixture_lock, controlled["fixture_lock_sha256"]),
        "fixture_manifest_sha256": (
            fixture_manifest,
            controlled["delivered_fixture_manifest_sha256"],
        ),
        "vad_model_sha256": (vad_model, finalists["vad"]["model_sha256"]),
        "asr_binary_sha256": (
            asr_binary,
            finalists["asr"]["worker_binary_sha256"],
        ),
        "asr_model_sha256": (asr_model, finalists["asr"]["model_sha256"]),
        "tts_archive_sha256": (
            artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
            finalists["tts"]["archive_sha256"],
        ),
        "tts_vocoder_sha256": (
            artifact_dir / "models/vocos-16khz-univ.onnx",
            finalists["tts"]["vocoder_sha256"],
        ),
        "tts_wrapper_wheel_sha256": (
            artifact_dir
            / "sources/sherpa_onnx-1.13.5-cp313-cp313-manylinux2014_aarch64.whl",
            finalists["tts"]["wrapper_wheel_sha256"],
        ),
        "tts_core_wheel_sha256": (
            artifact_dir
            / "sources/sherpa_onnx_core-1.13.5-py3-none-manylinux2014_aarch64.whl",
            finalists["tts"]["core_wheel_sha256"],
        ),
    }
    observed: dict[str, Any] = {}
    for name, (path, expected_sha256) in expected_files.items():
        if not path.is_file() or streaming_digest(path) != expected_sha256:
            raise PiPacketFailure(f"Accepted Audio controlled input mismatch: {name}")
        observed[name] = expected_sha256

    lock = load(fixture_lock)
    delivered = load(fixture_manifest)
    lock_records = lock.get("records", [])
    delivered_records = delivered.get("records", {})
    if (
        lock.get("audio_execution_sha") != accepted["p9_combined_execution_sha"]
        or lock.get("fixture_count") != controlled["fixture_count"]
        or [item.get("session_id") for item in lock_records]
        != EXPECTED_AUDIO_SESSIONS
        or not isinstance(delivered_records, dict)
        or any(
            delivered_records.get(item.get("fixture_id"), {}).get("derived_sha256")
            != item.get("sha256")
            for item in lock_records
        )
    ):
        raise PiPacketFailure("Accepted Audio fixture provenance mismatch")
    observed["fixture_count"] = len(lock_records)
    observed["controller_runtime"], _controller_site = (
        verify_audio_controller_runtime(
            controller_closure, accepted["runtimes"]["controller"]
        )
    )
    observed["vad_runtime"] = verify_audio_runtime(
        vad_runtime_python, accepted["runtimes"]["vad"]
    )
    observed["tts_runtime"] = verify_audio_runtime(
        tts_runtime_python, accepted["runtimes"]["tts"]
    )
    return observed


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
    catalog = load(repo_artifact(gate2a_lock["artifacts"]["catalog"]))
    p8_fixture = load(repo_artifact(gate2a_lock["artifacts"]["p8_fixture"]))
    product = load(repo_artifact(
        gate2a_lock["candidates"][gate2a_result["candidate_id"]]["product_config"]
    ))
    try:
        verify_gate2a_result(
            gate2a_result, catalog, p8_fixture,
            engine_capacity=product["engine_max_num_tokens"],
            max_output_tokens=product["max_output_tokens"],
        )
    except EvidenceInvalid as error:
        raise PiPacketFailure("Gate 2A reviewed result evidence mismatch") from error
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
            raise CandidateViolation("Gate 2B accepted ASR is unavailable after READY")
        try:
            metrics = worker.transcribe(bounded, self.accepted.timeout)
        except Exception as error:
            raise CandidateViolation("Gate 2B accepted ASR session failed") from error
        transcript = str(metrics.pop("hypothesis"))
        if not transcript.strip():
            raise CandidateViolation("Gate 2B accepted ASR returned an empty transcript")
        return {
            "session_id": session["session_id"],
            "terminal": "SUCCESS",
            "transcript": transcript,
            "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "latency_ms": metrics["latency_ms"],
        }


class ScoredAudioDomain:
    """Classify an accepted Audio domain's post-READY session fault as P10B behavior."""

    def __init__(
        self,
        name: str,
        accepted_domain: Any,
        diagnostics: list[dict[str, Any]] | None = None,
    ) -> None:
        self.name = name
        self.accepted = accepted_domain
        self.diagnostics = diagnostics if diagnostics is not None else []

    async def start(self) -> None:
        await self.accepted.start()

    async def stop(self) -> None:
        await self.accepted.stop()

    def residency_identity(self) -> dict[str, Any]:
        return self.accepted.residency_identity()

    async def run(self, session: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self.accepted.run(session)
        except Exception as error:
            safe_codes = {
                "pyalsaaudio==0.11.0 is required for core.audio.driver=alsa":
                    "CORE_ALSA_BINDING_UNAVAILABLE",
                "M4 Matcha PCM protocol mismatch": "TTS_PCM_PROTOCOL_MISMATCH",
                "M4 Matcha PCM length is invalid": "TTS_PCM_LENGTH_INVALID",
                "M4 Matcha PCM checksum mismatch": "TTS_PCM_CHECKSUM_MISMATCH",
                "Matcha worker closed its protocol stream": "TTS_PROTOCOL_STREAM_CLOSED",
            }
            process = getattr(self.accepted, "process", None)
            returncode = getattr(process, "returncode", None)
            self.diagnostics.append({
                "domain": self.name.lower(),
                "error_type": type(error).__name__,
                "error_code": (
                    "OPERATION_TIMEOUT"
                    if isinstance(error, TimeoutError)
                    else safe_codes.get(str(error), "UNMAPPED_ACCEPTED_RUNTIME_ERROR")
                ),
                "worker_returncode": returncode if isinstance(returncode, int) else None,
            })
            raise CandidateViolation(
                f"Gate 2B accepted {self.name} session failed"
            ) from error


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
        self.log_markers: set[str] = set()

    async def start(self) -> None:
        self.process, self.ready_ms = await asyncio.to_thread(
            start_gate2b_child, **self.common, stderr=self.stderr
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
                    f"USER={transcript}\nREQUIRED_LITERAL={nonce}"
                    f"\nFORBIDDEN_LITERAL={trap}"
                ),
            }],
            "pending_message_count": 0,
            "capabilities": {
                "perceptions": ["listen"],
                "actions": ["speak"],
                "tools": [],
            },
        }
        self.log_markers.update((transcript, nonce, trap))
        terminal, _wall_ms = scored_generate(
            self.process, self.common["validator"], session_id, value,
            timeout_s=(
                self.common["config_value"]["generate_timeout_ms"]
                + self.common["config_value"]["terminal_grace_ms"]
            ) / 1000,
        )
        response = terminal.get("response", {})
        speech = response.get("action_payload", {}).get("text")
        metrics = terminal.get("metrics", {})
        metric_types = all(
            isinstance(metrics.get(name), int)
            for name in ("prefill_tokens", "decode_tokens", "kv_tokens")
        )
        checks = {
            "terminal_result": terminal.get("type") == "RESULT",
            "request_correlated": terminal.get("request_id") == session_id,
            "speak_action": response.get("action_kind") == "speak",
            "speech_nonempty": isinstance(speech, str) and bool(speech.strip()),
            "metric_types": metric_types,
            "prefill_positive": metric_types and metrics["prefill_tokens"] > 0,
            "prefill_within_limit": metric_types and metrics["prefill_tokens"]
            <= self.common["config_value"]["max_input_tokens"],
            "decode_positive": metric_types and metrics["decode_tokens"] > 0,
            "decode_within_limit": metric_types and metrics["decode_tokens"]
            <= self.common["config_value"]["max_output_tokens"],
            "kv_positive": metric_types and metrics["kv_tokens"] > 0,
            "kv_within_capacity": metric_types
            and metrics["kv_tokens"] <= self.engine_capacity,
            "kv_accounted": metric_types and metrics["kv_tokens"]
            <= metrics["prefill_tokens"] + metrics["decode_tokens"] + 16,
        }
        if not all(checks.values()):
            if self.stderr is not None:
                diagnostic = {
                    "checks": checks,
                    "metrics": {
                        name: metrics.get(name)
                        if isinstance(metrics.get(name), (int, float)) else None
                        for name in ("prefill_tokens", "decode_tokens", "kv_tokens", "ttft_ms")
                    },
                }
                self.stderr.write(
                    "GATE2B_LLM_VALIDATION_DIAGNOSTIC "
                    + json.dumps(diagnostic, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
                self.stderr.flush()
            raise CandidateViolation("Gate 2B LLM product result or single-turn metric invalid")
        prior_leak = any(marker in speech for marker in self.prior_markers)
        current_marker_present = speech.count(nonce) == 1
        current_trap_absent = trap not in speech
        self.prior_markers.extend([nonce, trap])
        self.log_markers.add(speech)
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


def scan_owned_logs(paths: list[Path], runtime_markers: set[str]) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    leaked = False
    markers = tuple(FORBIDDEN_LOG) + tuple(
        marker for marker in sorted(runtime_markers) if marker
    )
    for path in paths:
        try:
            content = path.read_bytes()
        except OSError as error:
            raise EvidenceInvalid("Gate 2B owned-log scan failed") from error
        text = content.decode("utf-8", errors="replace")
        files.append({"name": path.name, "sha256": hashlib.sha256(content).hexdigest()})
        if any(marker in text for marker in markers):
            leaked = True
    return {
        "passed": not leaked,
        "scanned_files": files,
        "static_marker_count": len(FORBIDDEN_LOG),
        "runtime_marker_count": len(markers) - len(FORBIDDEN_LOG),
    }


def force_owned_group(name: str, group_id: int) -> dict[str, Any]:
    term_sent = kill_sent = False
    if group_absent(group_id):
        return {"owner": name, "term_sent": False, "kill_sent": False,
                "process_group_absent": True}
    try:
        os.killpg(group_id, signal.SIGTERM)
        term_sent = True
    except (ProcessLookupError, PermissionError):
        pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and not group_absent(group_id):
        time.sleep(0.05)
    if not group_absent(group_id):
        try:
            os.killpg(group_id, signal.SIGKILL)
            kill_sent = True
        except (ProcessLookupError, PermissionError):
            pass
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not group_absent(group_id):
            time.sleep(0.05)
    return {"owner": name, "term_sent": term_sent, "kill_sent": kill_sent,
            "process_group_absent": group_absent(group_id)}


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
        "integration_pairing_revision": "",
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
        "resource_observations": {},
        "cleanup": {},
        "log_hygiene": {},
        "domain_diagnostics": [],
        "partial_trace": [],
        "p_results": {"P9": "Blocked", "P10B": "Blocked"},
        "violations": [],
        "result": "INCONCLUSIVE",
        "publication_status": "REVIEW_REQUIRED",
    }


def combined_exception_disposition(
    error: BaseException, *, combined_entered: bool
) -> tuple[dict[str, str], str]:
    if combined_entered and error_result(error) == "FAIL":
        return {"P9": "Blocked", "P10B": "FAIL"}, "FAIL"
    return {"P9": "Blocked", "P10B": "Blocked"}, "INCONCLUSIVE"


def evaluate_single_session_resources(
    records: list[dict[str, Any]],
    *,
    session_points: list[dict[str, Any]],
    oom_before: int,
    oom_after: int,
) -> tuple[bool, dict[str, Any]]:
    """Check every non-soak P9 invariant without claiming leak credit."""

    if len(records) < 2 or len(session_points) != 1:
        raise EnvironmentInvalid("Gate 2B diagnostic resource coverage is incomplete")
    gaps = [
        records[index]["monotonic_s"] - records[index - 1]["monotonic_s"]
        for index in range(1, len(records))
    ]
    owner_names = {"controller", "vad", "asr", "tts", "llm"}
    owner_sets_complete = all(
        set(record.get("owners", {})) == owner_names
        and all(
            owner.get("root_present") is True
            and owner.get("process_count", 0) >= 1
            and owner.get("rss_kib", 0) > 0
            and owner.get("pss_kib", 0) > 0
            and owner.get("threads", 0) > 0
            for owner in record["owners"].values()
        )
        for record in records
    )
    summary = {
        "sample_count": len(records),
        "session_point_count": len(session_points),
        "peak_system_used_mib": max(item["system_used_mib"] for item in records),
        "peak_temperature_c": max(item["temperature_c"] for item in records),
        "max_sample_start_gap_s": round(max(gaps), 6),
        "oom_kill_delta": oom_after - oom_before,
        "owner_sets_complete": owner_sets_complete,
        "swap_zero_for_all_samples": all(
            item["swap_total_kib"] == 0 for item in records
        ),
        "throttled_zero_for_all_samples": all(
            item["throttled"] == "throttled=0x0" for item in records
        ),
    }
    passed = (
        summary["peak_system_used_mib"] <= 3584
        and summary["peak_temperature_c"] < 80
        and summary["max_sample_start_gap_s"] <= 0.5
        and summary["oom_kill_delta"] == 0
        and summary["owner_sets_complete"]
        and summary["swap_zero_for_all_samples"]
        and summary["throttled_zero_for_all_samples"]
        and session_points[0].get("session_index") == 1
    )
    return passed, summary


@contextmanager
def isolated_audio_cwd(work_dir: Path):
    """Contain cwd-relative side effects from immutable Accepted Audio children."""

    previous = Path.cwd()
    os.chdir(work_dir)
    try:
        yield
    finally:
        os.chdir(previous)


def single_session_diagnostic_output(result: dict[str, Any]) -> dict[str, Any]:
    """Return only sanitized, no-credit convergence observations."""

    return {
        "mode": "diagnostic-single-session",
        "packet_id": result["packet_id"],
        "run_id": result["run_id"],
        "candidate_id": result["candidate_id"],
        "integration_pairing_revision": result["integration_pairing_revision"],
        "execution_sha": result["execution_sha"],
        "execution_surface_sha256": result["execution_surface_sha256"],
        "session": result["sessions"][0] if len(result["sessions"]) == 1 else None,
        "resources": result["resources"],
        "cleanup": result["cleanup"],
        "log_hygiene": result["log_hygiene"],
        "domain_diagnostics": result["domain_diagnostics"],
        "partial_trace": result["partial_trace"],
        "violations": result["violations"],
        "p_results": {"P9": "Blocked", "P10B": "Blocked"},
        "formal_credit": False,
        "evidence_created": False,
        "result": result["result"],
    }


def verify_gate2b_result(
    result: dict[str, Any], *, engine_capacity: int, max_input_tokens: int,
    max_output_tokens: int
) -> dict[str, str]:
    """Independently recompute Gate 2B dispositions from sanitized observations."""

    observations = result.get("resource_observations", {})
    try:
        resources_pass, summary = evaluate_resources(
            observations["continuous_samples"],
            session_points=observations["session_points"],
            oom_before=observations["oom_before"],
            oom_after=observations["oom_after"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EvidenceInvalid("Gate 2B resource observations are incomplete") from error
    if result.get("resources") != summary:
        raise EvidenceInvalid("Gate 2B resource summary does not match observations")
    sessions = result.get("sessions", [])
    expected_ids = EXPECTED_AUDIO_SESSIONS
    session_ids = [item.get("session_id") for item in sessions if isinstance(item, dict)]
    session_ok = len(sessions) == 20 and session_ids == expected_ids
    for item in sessions:
        if not isinstance(item, dict):
            session_ok = False
            continue
        llm = item.get("llm", {})
        metrics = llm.get("metrics", {})
        session_ok = session_ok and bool(
            item.get("vad", {}).get("terminal") == "SUCCESS"
            and item.get("asr", {}).get("terminal") == "SUCCESS"
            and llm.get("terminal") == "SUCCESS"
            and llm.get("request_id") == item.get("session_id")
            and llm.get("prior_marker_leaked") is False
            and llm.get("current_marker_present_once") is True
            and llm.get("current_trap_absent") is True
            and item.get("tts", {}).get("terminal") == "SUCCESS"
            and item.get("tts", {}).get("playback_complete") is True
            and item.get("tts", {}).get("input_speech_sha256") == llm.get("speech_sha256")
            and all(isinstance(metrics.get(name), int) and not isinstance(metrics.get(name), bool)
                    for name in ("prefill_tokens", "decode_tokens", "kv_tokens"))
            and metrics.get("prefill_tokens", 0) > 0
            and metrics.get("prefill_tokens", 0) <= max_input_tokens
            and 0 < metrics.get("decode_tokens", 0) <= max_output_tokens
            and 0 < metrics.get("kv_tokens", 0) <= engine_capacity
            and metrics.get("kv_tokens", 0)
            <= metrics.get("prefill_tokens", 0) + metrics.get("decode_tokens", 0) + 16
        )
    soak = result.get("soak", {})
    soak_ok = (
        soak.get("cadence_seconds") == 5.0
        and soak.get("pause_count") == 19
        and len(soak.get("pause_elapsed_ms", [])) == 19
        and all(value >= 5000 for value in soak.get("pause_elapsed_ms", []))
        and soak.get("total_elapsed_ms", 0) >= 95000
    )
    cleanup = result.get("cleanup", {})
    domain_proofs = cleanup.get("domains", {})
    cleanup_ok = (
        cleanup.get("reverse_order") == ["llm", "tts", "asr", "vad"]
        and set(domain_proofs) == {"vad", "asr", "tts", "llm"}
        and all(
            proof.get("cooperative_stop") is True
            and proof.get("fallback_used") is False
            and proof.get("process_group_absent") is True
            and proof.get("error_type") is None
            for proof in domain_proofs.values()
        )
        and cleanup.get("process_groups_absent") == {
            "vad": True, "asr": True, "tts": True, "llm": True,
        }
        and cleanup.get("audio_device_owner_count") == 0
        and cleanup.get("llm") == {
            "exit_code": 0, "waited": True, "term_sent": False,
            "kill_sent": False, "process_group_absent": True,
        }
    )
    hygiene_ok = result.get("log_hygiene", {}).get("passed") is True
    p_results = {
        "P9": "PASS" if resources_pass else "FAIL",
        "P10B": "PASS" if (
            resources_pass and session_ok and soak_ok and cleanup_ok and hygiene_ok
        ) else "FAIL",
    }
    if result.get("p_results") != p_results:
        raise EvidenceInvalid("Gate 2B claimed dispositions do not match sanitized evidence")
    expected_result = "PASS" if p_results == {"P9":"PASS", "P10B":"PASS"} else "FAIL"
    if result.get("result") != expected_result:
        raise EvidenceInvalid("Gate 2B top-level result does not match P dispositions")
    return p_results


def main() -> int:
    if sys.argv[1:] == ["--fatal-outcome-self-test"]:
        return 4
    args = parse_args()
    if args.fatal_outcome_self_test:
        return 4
    result = initial_result(args)
    if args.preflight_only and args.diagnostic_session_only:
        result["violations"].append("Gate 2B execution modes are mutually exclusive")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    if not valid_run_id(args.run_id):
        result["violations"].append("Gate 2B run ID is not a safe slug")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    evidence_dir = args.evidence_root / args.run_id
    raw_dir = (
        Path(f"/tmp/llm-poc-g2b-001/diagnostic-{args.run_id}")
        if args.diagnostic_session_only
        else evidence_dir
    )
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
    preflight_succeeded = False
    diagnostic_succeeded = False
    try:
        if (
            raw_dir.exists()
            or evidence_dir.exists()
            or install_root.exists()
            or work_dir.exists()
        ):
            raise PiPacketFailure("Gate 2B run-owned path is dirty")
        if raw_dir.resolve().is_relative_to(ROOT):
            raise PiPacketFailure("Gate 2B controlled evidence must remain outside Git")
        audio_root_resolved = args.audio_root.resolve()
        for path in (
            args.audio_fixture_dir, args.audio_fixture_lock,
            args.audio_fixture_manifest, args.audio_artifact_dir,
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
                "oom_kill_delta": 0,
                "leak_slope_mib_per_session_max": 4.0,
                "leak_late_early_median_delta_mib_max": 64.0,
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
            **verify_audio_controlled_inputs(
                fixture_lock=args.audio_fixture_lock,
                fixture_manifest=args.audio_fixture_manifest,
                artifact_dir=args.audio_artifact_dir,
                controller_closure=args.audio_controller_closure,
                tts_runtime_python=args.audio_runtime_python,
                asr_binary=args.audio_asr_binary,
                asr_model=args.audio_asr_model,
                vad_runtime_python=args.audio_vad_runtime_python,
                vad_model=args.audio_vad_model,
                accepted=accepted,
            ),
            "core_response_id": accepted["core_response_id"],
            "core_response_sha": accepted["core_response_sha"],
        }

        if args.gate2a_receipt.resolve() != artifacts["gate2a_receipt"]:
            raise PiPacketFailure("Gate 2A model-finalist receipt path mismatch")
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
        require_resource_probe_preflight()
        preexisting_workers = preexisting_worker_count(args.audio_asr_binary)
        preexisting_audio_owners = audio_device_owner_count()
        if preexisting_workers or preexisting_audio_owners:
            raise PiPacketFailure("Gate 2B pre-existing worker/device ownership detected")
        result["environment"].update({
            "preexisting_combined_workers": preexisting_workers,
            "preexisting_audio_device_owners": preexisting_audio_owners,
        })

        runtime = lock["runtime"]
        runtime_wheel = Path(runtime["wheel_path"])
        if (
            not runtime_wheel.is_file()
            or streaming_digest(runtime_wheel) != runtime["wheel_sha256"]
        ):
            raise PiPacketFailure("Gate 2B runtime wheel mismatch")
        product_config = repo_artifact(candidate["product_config"])
        standard_value = load(product_config)
        gate2a_parent = candidate.get("gate2a_parent", {})
        if (
            gate2a_parent.get("pairing_revision")
            != gate2a["selection"]["gate2b_pairing_revision"]
            or gate2a_parent.get("product_config_sha256")
            != gate2a["selection"]["gate2b_product_config_sha256"]
            or standard_value["pairing_revision"]
            != candidate.get("corrective_pairing_revision")
        ):
            raise PiPacketFailure("Gate 2B corrective integration ancestry mismatch")
        result["integration_pairing_revision"] = standard_value["pairing_revision"]
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
        if args.preflight_only:
            preflight_succeeded = True
            print(json.dumps({
                "mode": "preflight-only",
                "packet_id": PACKET_ID,
                "execution_sha": args.execution_sha,
                "execution_surface_sha256": result["execution_surface_sha256"],
                "candidate_id": candidate_id,
                "accepted_audio_authenticated": True,
                "artifact_receipt_authenticated": True,
                "full_model_hash_count": 0,
                "resource_probes_available": True,
                "preexisting_combined_workers": preexisting_workers,
                "preexisting_audio_device_owners": preexisting_audio_owners,
                "formal_credit": False,
                "evidence_created": False,
                "result": "PASS",
            }, sort_keys=True, separators=(",", ":")))
            return 0

        raw_dir.mkdir(parents=True, exist_ok=False)
        owns_raw_dir = True
        work_dir.mkdir(parents=True, exist_ok=False)
        owns_work_dir = True
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
        vad = ScoredAudioDomain(
            "VAD",
            bindings["PersistentVadDomain"](
                args.audio_root, args.audio_vad_runtime_python, args.audio_vad_model,
                work_dir / "vad-bounded", args.operation_timeout,
            ),
            result["domain_diagnostics"],
        )
        accepted_asr = bindings["PersistentAsrDomain"](
            args.audio_asr_binary, args.audio_asr_model,
            work_dir / "asr", args.operation_timeout,
        )
        asr = TranscriptAsrDomain(accepted_asr)
        tts = ScoredAudioDomain(
            "TTS",
            bindings["PersistentTtsDomain"](
                args.audio_root, args.audio_artifact_dir, args.audio_runtime_python,
                work_dir / "tts", audio, audio_config, args.operation_timeout,
            ),
            result["domain_diagnostics"],
        )

        protocol = artifacts["protocol_schema"]
        prompt_schema = artifacts["prompt_schema"]
        response_schema = artifacts["response_schema"]
        validator = protocol_validator(protocol, prompt_schema, response_schema)
        common = {
            "adapter": artifacts["gate2b_adapter"],
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
                vad, asr, llm_domain, tts, pause=asyncio.sleep,
                group_absent=group_absent, force_cleanup=force_owned_group,
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
                roots_after = dict(coordinator.started_roots)
                try:
                    samples = sampler.stop()
                except Exception as error:
                    raise EnvironmentInvalid("Gate 2B resource sampler failed") from error

            def capture_session(index: int) -> None:
                try:
                    sampler.capture_session(index)
                except Exception as error:
                    raise EnvironmentInvalid("Gate 2B session resource probe failed") from error

            with isolated_audio_cwd(work_dir):
                if args.diagnostic_session_only:
                    sessions = asyncio.run(coordinator.run_single_diagnostic(
                        records[0],
                        on_resident=start_sampling,
                        before_shutdown=stop_sampling,
                        after_session=capture_session,
                    ))
                else:
                    sessions = asyncio.run(coordinator.run(
                        records,
                        cadence_s=args.cadence_seconds,
                        on_resident=start_sampling,
                        before_shutdown=stop_sampling,
                        after_session=capture_session,
                    ))
            sessions_completed = True
            result["runtime"]["llm_inference_ready_ms"] = llm_domain.ready_ms
        oom_after = oom_kill_count()
        if args.diagnostic_session_only:
            resources_pass, resource_summary = evaluate_single_session_resources(
                samples,
                session_points=sampler.session_points,
                oom_before=oom_before,
                oom_after=oom_after,
            )
        else:
            resources_pass, resource_summary = evaluate_resources(
                samples, session_points=sampler.session_points,
                oom_before=oom_before, oom_after=oom_after
            )
        (raw_dir / "resource-samples.json").write_text(
            json.dumps(samples, sort_keys=True), encoding="utf-8"
        )
        result["sessions"] = sessions
        result["resources"] = resource_summary
        result["resource_observations"] = {
            "continuous_samples": samples,
            "session_points": sampler.session_points,
            "oom_before": oom_before,
            "oom_after": oom_after,
        }
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
            "domains": coordinator.cleanup_proofs,
        }
        expected_session_ids = (
            EXPECTED_AUDIO_SESSIONS[:1]
            if args.diagnostic_session_only
            else EXPECTED_AUDIO_SESSIONS
        )
        session_path_pass = (
            len(sessions) == len(expected_session_ids)
            and [item["session_id"] for item in sessions] == expected_session_ids
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
            and all(process_absence.values())
            and result["cleanup"]["audio_device_owner_count"] == 0
        )
        p10b_pass = (
            session_path_pass
            and len(coordinator.cadence_pause_elapsed_ms) == 19
            and all(value >= 5000 for value in coordinator.cadence_pause_elapsed_ms)
        )
        asr_stderr_path = work_dir / "asr/base-q8.stderr.log"
        if not asr_stderr_path.is_file():
            raise EvidenceInvalid("Gate 2B accepted ASR log is unavailable")
        hygiene = scan_owned_logs(
            [
                raw_dir / "offline-install.stdout",
                raw_dir / "offline-install.stderr",
                llm_stderr_path,
                asr_stderr_path,
            ],
            llm_domain.log_markers,
        )
        result["log_hygiene"] = hygiene
        if not hygiene["passed"]:
            result["violations"].append("CandidateViolation: owned log hygiene")
            session_path_pass = False
            p10b_pass = False
        verify_model_receipt(
            receipt["model"], Path(standard_value["model_path"]),
            standard_value["model_sha256"],
        )
        result["artifact_authentication"]["metadata_unchanged"] = True
        result["environment_post"] = target_preflight(args.execution_sha)
        if args.diagnostic_session_only:
            cleanup_pass = (
                result["cleanup"].get("reverse_order")
                == ["llm", "tts", "asr", "vad"]
                and result["cleanup"].get("process_groups_absent")
                == {"vad": True, "asr": True, "tts": True, "llm": True}
                and result["cleanup"].get("audio_device_owner_count") == 0
                and all(
                    proof.get("cooperative_stop") is True
                    and proof.get("fallback_used") is False
                    and proof.get("process_group_absent") is True
                    and proof.get("error_type") is None
                    for proof in result["cleanup"].get("domains", {}).values()
                )
                and len(result["cleanup"].get("domains", {})) == 4
            )
            diagnostic_succeeded = (
                resources_pass
                and session_path_pass
                and cleanup_pass
                and hygiene["passed"]
                and result["domain_diagnostics"] == []
            )
            result["p_results"] = {"P9": "Blocked", "P10B": "Blocked"}
            result["result"] = "PASS" if diagnostic_succeeded else "FAIL"
        else:
            result["p_results"]["P9"] = "PASS" if resources_pass else "FAIL"
            result["p_results"]["P10B"] = (
                "PASS" if p10b_pass and resources_pass else "FAIL"
            )
            result["result"] = (
                "PASS"
                if result["p_results"] == {"P9": "PASS", "P10B": "PASS"}
                else "FAIL"
            )
            verify_gate2b_result(
                result,
                engine_capacity=standard_value["engine_max_num_tokens"],
                max_input_tokens=standard_value["max_input_tokens"],
                max_output_tokens=standard_value["max_output_tokens"],
            )
    except (
        PiPacketFailure, OSError, subprocess.SubprocessError, KeyError, TypeError,
        ValueError, RuntimeError, json.JSONDecodeError,
    ) as error:
        error_evidence = sanitized_error(error)
        result["violations"].append(
            f"{error_evidence['category']}: {error_evidence['error_type']}"
        )
        result["p_results"], result["result"] = combined_exception_disposition(
            error, combined_entered=combined_entered,
        )
        if coordinator is not None:
            result["partial_trace"] = coordinator.trace
            result["cleanup"]["reverse_order"] = coordinator.stop_order
            result["cleanup"]["domains"] = coordinator.cleanup_proofs
            cleanup_roots = roots_after or dict(coordinator.started_roots)
            if cleanup_roots:
                result["cleanup"]["process_groups_absent"] = {
                    name: group_absent(pid) for name, pid in cleanup_roots.items()
                }
            try:
                result["cleanup"]["audio_device_owner_count"] = audio_device_owner_count()
            except PiPacketFailure as cleanup_error:
                result["violations"].append(str(cleanup_error))
    finally:
        if preflight_succeeded:
            return 0
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
            if args.diagnostic_session_only:
                shutil.rmtree(raw_dir)
            else:
                resource_samples = raw_dir / "resource-samples.json"
                if samples and not resource_samples.exists():
                    resource_samples.write_text(
                        json.dumps(samples, sort_keys=True), encoding="utf-8"
                    )
                if result_schema is not None:
                    errors = list(
                        Draft202012Validator(load(result_schema)).iter_errors(result)
                    )
                    if errors:
                        result["violations"].append(
                            "Gate 2B result schema validation failed"
                        )
                        result["result"] = "INCONCLUSIVE"
                try:
                    write_json_evidence(raw_dir / "gate2b-sanitized.json", result)
                except EvidenceInvalid as error:
                    evidence = sanitized_error(error)
                    result["violations"].append(
                        f"{evidence['category']}: {evidence['error_type']}"
                    )
                    result["result"] = "INCONCLUSIVE"
        if args.diagnostic_session_only:
            if not diagnostic_succeeded:
                result["result"] = "FAIL"
            result["p_results"] = {"P9": "Blocked", "P10B": "Blocked"}
            print(json.dumps(
                single_session_diagnostic_output(result),
                sort_keys=True,
                separators=(",", ":"),
            ))
        else:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if args.diagnostic_session_only:
        return 0 if diagnostic_succeeded else 1
    return 0 if result["result"] == "PASS" else 1 if result["result"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
