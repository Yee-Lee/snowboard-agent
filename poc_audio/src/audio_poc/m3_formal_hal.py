"""Authorized Pi-only M3 Core HAL capture and direct-PCM playback phases."""

from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m3_authorization import (
    PUBLICATION_STATUS,
    load_signoff,
    validate_formal_authorization,
    validate_m3_result,
)
from .m3_asr import BINARY_SHA256, MODEL_SHA256, run_direct_asr
from .m3_candidate_lifecycle import run_candidate_lifecycle
from .m3_core_hal import (
    capture_frames,
    make_alsa_config,
    play_stream_pcm,
    process_resource_snapshot,
    read_stream_wav,
    write_stream_wav,
)
from .m3_packet import CORE_HAL_EXECUTION_SHA, PACKET_ID, load_packet, validate_repo_inputs
from .m3_tts_playback import prepare_and_run_matcha
from .m3_vad import run_vad_worker
from .m3_vad_worker import MODEL_SHA256 as VAD_MODEL_SHA256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def child_pids() -> set[int]:
    observed: set[int] = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return observed
    own_pid = os.getpid()
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        status = item / "status"
        try:
            ppid_line = next(
                line for line in status.read_text(encoding="utf-8").splitlines()
                if line.startswith("PPid:")
            )
        except (FileNotFoundError, PermissionError, StopIteration):
            continue
        if int(ppid_line.split()[1]) == own_pid:
            observed.add(int(item.name))
    return observed


def audio_device_owner_count() -> int:
    devices = sorted(glob.glob("/dev/snd/*"))
    if not devices:
        return 0
    completed = subprocess.run(["fuser", *devices], capture_output=True, text=True, check=False)
    return 1 if completed.returncode == 0 else 0


def runtime_snapshot() -> dict[str, Any]:
    local = process_resource_snapshot()
    try:
        tasks = len(asyncio.all_tasks())
    except RuntimeError:
        tasks = 0
    return {
        **local,
        "tasks": tasks,
        "children": child_pids(),
        "device_owners": audio_device_owner_count(),
    }


def cleanup_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    return {
        "child_processes": len(set(after["children"]) - set(before["children"])),
        "threads": max(0, int(after["threads"]) - int(before["threads"])),
        "tasks": max(0, int(after["tasks"]) - int(before["tasks"])),
        "iterators": 0,
        "streams": 0,
        "file_descriptors": max(
            0, int(after["file_descriptors"]) - int(before["file_descriptors"])
        ),
        "device_owners": int(after["device_owners"]),
    }


def assert_target() -> dict[str, str]:
    model_path = Path("/proc/device-tree/model")
    model = (
        model_path.read_bytes().replace(b"\x00", b"").decode("utf-8", "replace")
        if model_path.is_file()
        else "unavailable"
    )
    target = {
        "machine": platform.machine().lower(),
        "model": model,
        "kernel": platform.release(),
        "python": platform.python_version(),
    }
    if target["machine"] not in {"aarch64", "arm64"}:
        raise ValueError("formal M3 HAL execution requires aarch64")
    if not model.startswith("Raspberry Pi 5"):
        raise ValueError("formal M3 HAL execution requires Raspberry Pi 5")
    if not Path("/dev/snd").is_dir():
        raise ValueError("formal M3 HAL execution requires ALSA devices")
    return target


def assert_network_isolated() -> dict[str, Any]:
    """Require a private network namespace with only a non-UP loopback device."""

    if shutil.which("ip") is None:
        raise RuntimeError("formal offline inference requires the ip executable")
    completed = subprocess.run(
        ["ip", "-json", "link"], check=True, capture_output=True, text=True, timeout=10,
    )
    interfaces = json.loads(completed.stdout)
    if not isinstance(interfaces, list):
        raise ValueError("network interface inventory is invalid")
    summary = [
        {
            "ifname": str(item.get("ifname", "")),
            "operstate": str(item.get("operstate", "")),
            "flags": sorted(str(flag) for flag in item.get("flags", [])),
        }
        for item in interfaces
    ]
    isolated = (
        len(summary) == 1
        and summary[0]["ifname"] == "lo"
        and "UP" not in summary[0]["flags"]
    )
    if not isolated:
        raise RuntimeError("formal candidate inference requires a disabled network namespace")
    return {
        "method": "unshare_user_and_network_namespace_loopback_down",
        "network_disabled": True,
        "interfaces": summary,
    }


def _validate_device(value: str, name: str) -> None:
    if not value.startswith("hw:") or value.startswith("plughw:") or any(char.isspace() for char in value):
        raise ValueError(f"{name} must be an exact direct hw: ALSA device")


def validate_case_identity(args: argparse.Namespace) -> None:
    fixed = {
        "preflight": "M3-PREFLIGHT-01",
        "direct-pcm": "M3-PCM-01",
        "tts": "M3-TTS-SET-01",
        "asr-direct": "M3-ASR-DIRECT-PCM-BASELINE-001",
        "asr-hal": "M3-ASR-HAL-PATH-001",
        "vad-hal": "M3-VAD-SET-01",
    }
    expected = fixed.get(args.mode)
    if expected is not None and args.test_id != expected:
        raise ValueError(f"{args.mode} requires test ID {expected}")
    if args.mode == "hal-lifecycle":
        mapping = {
            "start-stop": "M3-LIFE-01",
            "reopen-5": "M3-LIFE-02",
            "invalid-input": "M3-LIFE-03",
            "invalid-output": "M3-LIFE-04",
        }
        if mapping.get(args.lifecycle_scenario) != args.test_id:
            raise ValueError("HAL lifecycle scenario/test ID mismatch")
    if args.mode == "candidate-lifecycle":
        mapping = {"cancel": "M3-LIFE-05", "force-abort": "M3-LIFE-06"}
        if mapping.get(args.candidate_scenario) != args.test_id:
            raise ValueError("candidate lifecycle scenario/test ID mismatch")


def _require_outside_repo(path: Path, repo_root: Path, name: str) -> None:
    """Keep controlled evidence, private PCM and disposable model data out of Git."""

    if path.resolve().is_relative_to(repo_root.resolve()):
        raise ValueError(f"{name} must be outside the POC repository")


def _require_file_sha256(path: Path | None, expected: str, name: str) -> dict[str, Any]:
    if path is None or not path.is_file():
        raise ValueError(f"preflight requires an available {name}")
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(f"{name} checksum mismatch")
    return {"path": str(path.resolve()), "sha256": observed, "size_bytes": path.stat().st_size}


def run_preflight(args: argparse.Namespace, audio: Any, config: Any) -> dict[str, Any]:
    """Validate the complete, pinned Pi execution input set without inference."""

    required = (
        args.artifact_dir, args.runtime_python, args.binary, args.model,
        args.vad_runtime_python, args.vad_model, args.fixture_dir,
    )
    if any(value is None for value in required):
        raise ValueError(
            "preflight requires TTS artifacts/runtime, ASR binary/model, VAD runtime/model "
            "and fixture directory"
        )
    if not args.runtime_python.is_file() or not args.vad_runtime_python.is_file():
        raise ValueError("preflight candidate runtime Python is unavailable")
    expected_fixtures = {
        item["filename"] for item in load_packet(args.packet)["capture_cases"]
    }
    present_fixtures = sorted(
        name for name in expected_fixtures if (args.fixture_dir / name).is_file()
    )
    from .m4a_authorized_preflight import verify_candidate_inputs

    manifest = json.loads(
        (args.repo_root / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text(
            encoding="utf-8"
        )
    )
    verify_candidate_inputs(manifest, "tts-sherpa-matcha-zh-en-1.13.5", args.artifact_dir)
    return {
        "scope": "IDENTITY_AND_READINESS_ONLY_NO_CAPTURE_PLAYBACK_OR_INFERENCE",
        "core_hal_factory": str(Path(audio.__file__).resolve()) if hasattr(audio, "__file__") else type(audio).__name__,
        "stream_format": "16000_HZ_MONO_S16_LE",
        "core_native_output_format": "48000_HZ_STEREO_S32_LE",
        "configured_input_device": config.input.device,
        "configured_output_device": config.output.device,
        "asr_binary": _require_file_sha256(args.binary, BINARY_SHA256, "ASR worker binary"),
        "asr_model": _require_file_sha256(args.model, MODEL_SHA256, "ASR model"),
        "vad_model": _require_file_sha256(args.vad_model, VAD_MODEL_SHA256, "VAD model"),
        "tts_artifacts": "VERIFIED_BY_PINNED_CANDIDATE_MANIFEST",
        "capture_catalog_count": len(expected_fixtures),
        "captures_already_present": present_fixtures,
        "device_owners_at_check": audio_device_owner_count(),
        "capture_performed": False,
        "playback_performed": False,
        "inference_performed": False,
    }


def _result(
    args: argparse.Namespace,
    signoff: dict[str, Any],
    result: str,
    cleanup: dict[str, int],
    evidence_log: Path,
    details: dict[str, Any],
) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "packet_id": PACKET_ID,
        "test_id": args.test_id,
        "publication_status": PUBLICATION_STATUS,
        "result": result,
        "poc_execution_sha": signoff["poc_execution_sha"],
        "core_execution_sha": signoff["core_execution_sha"],
        "command": list(sys.argv),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "phase": args.mode,
        "cleanup": cleanup,
        "controlled_evidence": {
            "locator": args.controlled_locator,
            "sha256": sha256_file(evidence_log),
        },
        "details": details,
    }
    validate_m3_result(document)
    return document


async def _execute(args: argparse.Namespace, core_root: Path) -> dict[str, Any]:
    audio, config = make_alsa_config(
        core_root, args.input_device, args.output_device, args.input_channel,
    )
    if args.mode == "preflight":
        return run_preflight(args, audio, config)
    if args.mode == "capture":
        if args.capture_wav is None or args.capture_wav.exists():
            raise ValueError("capture requires a new --capture-wav path")
        if args.frames is None or args.frames <= 0:
            raise ValueError("capture requires positive --frames")
        source = audio.make_audio_input(config)
        payload = await capture_frames(source, args.frames, args.timeout)
        write_stream_wav(args.capture_wav, payload)
        return {
            "frames_20ms": args.frames,
            "pcm_bytes": len(payload),
            "duration_ms": args.frames * 20,
            "stream_format": "16000_HZ_MONO_S16_LE",
            "capture_wav_sha256": sha256_file(args.capture_wav),
        }
    if args.mode == "hal-lifecycle":
        if args.lifecycle_scenario is None:
            raise ValueError("hal-lifecycle requires --lifecycle-scenario")
        return await run_hal_lifecycle(audio, config, args.lifecycle_scenario, args.timeout)
    if args.mode == "candidate-lifecycle":
        required = (
            args.artifact_dir, args.runtime_python, args.binary, args.model,
            args.fixture_dir, args.work_dir, args.candidate_scenario,
        )
        if any(value is None for value in required):
            raise ValueError(
                "candidate-lifecycle requires artifacts/runtimes, ASR inputs, fixtures, "
                "work directory and --candidate-scenario"
            )
        return await asyncio.to_thread(
            run_candidate_lifecycle,
            args.repo_root,
            args.artifact_dir,
            args.runtime_python,
            args.binary,
            args.model,
            args.fixture_dir,
            args.work_dir,
            args.candidate_scenario,
            args.timeout,
        )
    if args.mode == "tts":
        if args.artifact_dir is None or args.work_dir is None or args.runtime_python is None:
            raise ValueError("tts requires --artifact-dir, --work-dir and --runtime-python")
        return await prepare_and_run_matcha(
            args.repo_root,
            args.artifact_dir,
            args.work_dir,
            args.runtime_python,
            audio,
            config,
            args.timeout,
        )
    if args.mode in {"asr-direct", "asr-hal"}:
        required = (args.fixture_dir, args.binary, args.model, args.work_dir)
        if any(value is None for value in required):
            raise ValueError("asr-direct requires --fixture-dir, --binary, --model and --work-dir")
        if args.mode == "asr-hal" and args.source_fixture_lock is None:
            raise ValueError("asr-hal requires --source-fixture-lock from the direct-PCM run")
        return run_direct_asr(
            args.repo_root,
            args.fixture_dir,
            args.binary,
            args.model,
            args.work_dir,
            args.poc_execution_sha,
            args.timeout,
            (
                "M3-ASR-DIRECT-PCM-BASELINE-001"
                if args.mode == "asr-direct"
                else "M3-ASR-HAL-PATH-001"
            ),
            args.source_fixture_lock,
        )
    if args.mode == "vad-hal":
        required = (args.vad_runtime_python, args.vad_model, args.fixture_dir, args.work_dir)
        if any(value is None for value in required):
            raise ValueError(
                "vad-hal requires --vad-runtime-python, --vad-model, --fixture-dir and --work-dir"
            )
        return run_vad_worker(
            args.repo_root,
            args.vad_runtime_python,
            args.vad_model,
            args.fixture_dir,
            args.work_dir,
            args.timeout,
        )
    if args.pcm_wav is None:
        raise ValueError("direct-pcm requires --pcm-wav")
    payload = read_stream_wav(args.pcm_wav)
    sink = audio.make_audio_output(config)
    await play_stream_pcm(sink, payload, args.timeout, args.samples_per_chunk)
    return {
        "pcm_bytes": len(payload),
        "samples_per_chunk": args.samples_per_chunk,
        "stream_format": "16000_HZ_MONO_S16_LE",
        "core_native_format": "48000_HZ_STEREO_S32_LE",
        "source_wav_sha256": sha256_file(args.pcm_wav),
    }


async def _start_stop(component: Any, timeout: float) -> None:
    await asyncio.wait_for(component.start(), timeout=timeout)
    await asyncio.wait_for(component.stop(), timeout=timeout)


async def _expect_start_error(component: Any, timeout: float) -> str:
    try:
        await asyncio.wait_for(component.start(), timeout=timeout)
    except Exception as error:
        try:
            await asyncio.wait_for(component.stop(), timeout=timeout)
        except Exception:
            pass
        return type(error).__name__
    await asyncio.wait_for(component.stop(), timeout=timeout)
    raise RuntimeError("invalid ALSA device unexpectedly started")


async def run_hal_lifecycle(
    audio: Any,
    config: Any,
    scenario: str,
    timeout: float,
) -> dict[str, Any]:
    """Run the four HAL-owned lifecycle rows without candidate orchestration."""

    silence = bytes(640)
    if scenario == "start-stop":
        await _start_stop(audio.make_audio_input(config), timeout)
        await _start_stop(audio.make_audio_output(config), timeout)
        return {"scenario": scenario, "input_cycles": 1, "output_cycles": 1}
    if scenario == "reopen-5":
        for _ in range(5):
            await capture_frames(audio.make_audio_input(config), 1, timeout)
            await play_stream_pcm(audio.make_audio_output(config), silence, timeout)
        return {
            "scenario": scenario,
            "input_cycles": 5,
            "output_cycles": 5,
            "pcm_per_cycle": "ONE_20MS_SILENCE_FRAME",
        }
    if scenario == "invalid-input":
        invalid = replace(config, input=replace(config.input, device="hw:__m3_invalid_input__,0"))
        error_type = await _expect_start_error(audio.make_audio_input(invalid), timeout)
        await play_stream_pcm(audio.make_audio_output(config), silence, timeout)
        return {
            "scenario": scenario,
            "expected_error_type": error_type,
            "valid_output_recheck": "PASS",
        }
    if scenario == "invalid-output":
        invalid = replace(config, output=replace(config.output, device="hw:__m3_invalid_output__,0"))
        before = await capture_frames(audio.make_audio_input(config), 1, timeout)
        error_type = await _expect_start_error(audio.make_audio_output(invalid), timeout)
        after = await capture_frames(audio.make_audio_input(config), 1, timeout)
        return {
            "scenario": scenario,
            "expected_error_type": error_type,
            "valid_input_recheck": "PASS",
            "capture_bytes_before": len(before),
            "capture_bytes_after": len(after),
        }
    raise ValueError(f"unsupported HAL lifecycle scenario: {scenario}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument(
        "mode", choices=(
            "preflight", "capture", "direct-pcm", "hal-lifecycle", "tts", "asr-direct",
            "asr-hal", "vad-hal", "candidate-lifecycle"
        )
    )
    root.add_argument("--packet", type=Path, required=True)
    root.add_argument("--repo-root", type=Path, required=True)
    root.add_argument("--core-root", type=Path, required=True)
    root.add_argument("--signoff", type=Path, required=True)
    root.add_argument("--test-id", required=True)
    root.add_argument("--input-device", required=True)
    root.add_argument("--output-device", required=True)
    root.add_argument("--input-channel", type=int, choices=(0, 1), required=True)
    root.add_argument("--timeout", type=float, default=10.0)
    root.add_argument("--output", type=Path, required=True)
    root.add_argument("--evidence-log", type=Path, required=True)
    root.add_argument("--controlled-locator", required=True)
    root.add_argument("--capture-wav", type=Path)
    root.add_argument("--frames", type=int)
    root.add_argument("--pcm-wav", type=Path)
    root.add_argument("--samples-per-chunk", type=int, default=320)
    root.add_argument("--artifact-dir", type=Path)
    root.add_argument("--work-dir", type=Path)
    root.add_argument("--runtime-python", type=Path)
    root.add_argument("--fixture-dir", type=Path)
    root.add_argument("--source-fixture-lock", type=Path)
    root.add_argument("--binary", type=Path)
    root.add_argument("--model", type=Path)
    root.add_argument("--vad-runtime-python", type=Path)
    root.add_argument("--vad-model", type=Path)
    root.set_defaults(poc_execution_sha=None)
    root.add_argument(
        "--lifecycle-scenario",
        choices=("start-stop", "reopen-5", "invalid-input", "invalid-output"),
    )
    root.add_argument("--candidate-scenario", choices=("cancel", "force-abort"))
    return root


def main() -> int:
    args = parser().parse_args()
    if args.output.exists() or args.evidence_log.exists():
        raise ValueError("formal result and evidence log must be new paths")
    if not args.test_id.startswith("M3-"):
        raise ValueError("formal test ID must start with M3-")
    validate_case_identity(args)
    if args.timeout <= 0:
        raise ValueError("formal timeout must be positive")
    _validate_device(args.input_device, "input device")
    _validate_device(args.output_device, "output device")
    _require_outside_repo(args.evidence_log, args.repo_root, "controlled evidence log")
    for name, path in (
        ("capture WAV", args.capture_wav),
        ("PCM WAV", args.pcm_wav),
        ("fixture directory", args.fixture_dir),
        ("source fixture lock", args.source_fixture_lock),
        ("work directory", args.work_dir),
        ("artifact directory", args.artifact_dir),
    ):
        if path is not None:
            _require_outside_repo(path, args.repo_root, name)
    packet = load_packet(args.packet)
    validate_repo_inputs(packet, args.repo_root)
    if args.mode == "capture":
        matches = [item for item in packet["capture_cases"] if item["test_id"] == args.test_id]
        if len(matches) != 1:
            raise ValueError("capture test ID is absent from the fixed catalog")
        capture_case = matches[0]
        if args.capture_wav is None or args.capture_wav.name != capture_case["filename"]:
            raise ValueError("capture WAV filename does not match the fixed catalog")
        if args.frames != capture_case["frames_20ms"]:
            raise ValueError("capture frame count does not match the fixed catalog")
    signoff = load_signoff(args.signoff)
    validate_formal_authorization(signoff, args.packet, args.repo_root, args.core_root)
    if signoff["core_execution_sha"] != CORE_HAL_EXECUTION_SHA:
        raise ValueError("formal signoff does not bind the packet-pinned Core HAL")
    args.poc_execution_sha = signoff["poc_execution_sha"]
    platform_identity = assert_target()
    network = (
        assert_network_isolated()
        if args.mode in {"tts", "asr-direct", "asr-hal", "vad-hal", "candidate-lifecycle"}
        else None
    )
    before = runtime_snapshot()
    result = "PASS"
    try:
        details = asyncio.run(_execute(args, args.core_root))
        result = str(details.pop("_result_disposition", "PASS"))
    except Exception as error:  # Preserve bounded rejected hardware evidence.
        result = "FAIL"
        details = {
            "error_type": type(error).__name__,
            "error": str(error),
        }
    after = runtime_snapshot()
    cleanup = cleanup_delta(before, after)
    if any(cleanup.values()):
        result = "FAIL"
    details["platform"] = platform_identity
    details["input_device"] = args.input_device
    details["output_device"] = args.output_device
    details["input_channel"] = args.input_channel
    if network is not None:
        details["network"] = network
    evidence = {
        "schema_version": "1.0",
        "packet_id": PACKET_ID,
        "test_id": args.test_id,
        "phase": args.mode,
        "result": result,
        "before": {
            **before,
            "children": sorted(before["children"]),
        },
        "after": {
            **after,
            "children": sorted(after["children"]),
        },
        "cleanup": cleanup,
        "details": details,
    }
    args.evidence_log.parent.mkdir(parents=True, exist_ok=True)
    with args.evidence_log.open("x", encoding="utf-8") as destination:
        json.dump(evidence, destination, indent=2, sort_keys=True)
        destination.write("\n")
    document = _result(args, signoff, result, cleanup, args.evidence_log, details)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(document, destination, indent=2, sort_keys=True)
        destination.write("\n")
    print(json.dumps({"result": result, "test_id": args.test_id, "output": str(args.output)}))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
