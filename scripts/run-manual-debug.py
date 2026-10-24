#!/usr/bin/env python3
"""Run physical human input with private diagnostics and post-exit panel cleanup."""
from __future__ import annotations

import argparse
import array
import asyncio
from dataclasses import is_dataclass
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_json(path, value):
    with path.open("x", encoding="utf-8") as sink:
        os.chmod(path, 0o600)
        json.dump(value, sink, ensure_ascii=False, indent=2)
        sink.write("\n")


def rebase_paths(raw, resolved):
    """Relocate a config snapshot without changing the meaning of relative assets."""
    if isinstance(resolved, Path) and raw is not None:
        return str(resolved.absolute())
    if isinstance(raw, dict) and is_dataclass(resolved):
        return {key: rebase_paths(value, getattr(resolved, key)) for key, value in raw.items()}
    return raw


def snapshot_config(source, destination):
    from sbd.core.config import load_config
    resolved = load_config(local_path=source, dotenv_path=ROOT / ".env")
    raw = rebase_paths(yaml.safe_load(source.read_text()) or {}, resolved)
    raw.setdefault("log", {})["file"] = str(destination.parent / "application.log")
    with destination.open("x") as sink:
        os.chmod(destination, 0o600)
        yaml.safe_dump(raw, sink, allow_unicode=True, sort_keys=False)


def assert_display_available(config):
    # Reuse the runner's App check rather than interrupting an unrelated process.
    if not load_script("run-alpha-pv").no_previous_app():
        raise RuntimeError("APP_STILL_RUNNING")
    if config.driver != "ssd1351" or config.gpio_chip_index is None:
        raise RuntimeError("PHYSICAL_DISPLAY_REQUIRED")
    devices = [Path(f"/dev/spidev0.{config.spi_chip_select}"),
               Path(f"/dev/gpiochip{config.gpio_chip_index}")]
    if not all(path.exists() for path in devices):
        raise RuntimeError("DISPLAY_DEVICE_MISSING")
    owners = subprocess.run(["fuser", *map(str, devices)], capture_output=True, timeout=2)
    if owners.returncode == 0:
        raise RuntimeError("DISPLAY_DEVICE_BUSY")
    if owners.returncode != 1 or owners.stdout.strip() or owners.stderr.strip():
        raise RuntimeError("DISPLAY_OWNER_CHECK_FAILED")


async def clear_display(config_path):
    from sbd.core.config import load_config
    from sbd.core.display import make_display
    config = load_config(local_path=config_path, dotenv_path=ROOT / ".env")
    assert_display_available(config.core.display)
    display = make_display(config.core.display)
    await display.start()
    try:
        display.clear()
        display.show()
    finally:
        await display.stop()


def post_exit_clear(python, config, log, seconds):
    """A native hang cannot keep the failed App or the diagnostic wrapper alive."""
    command = [str(python), str(Path(__file__).absolute()),
               "--clear-display-worker", "--config", str(config)]
    with log.open("xb") as sink:
        os.chmod(log, 0o600)
        try:
            result = subprocess.run(command, stdout=sink, stderr=subprocess.STDOUT, timeout=seconds)
        except subprocess.TimeoutExpired:
            return {"attempted": True, "cleared": False, "reason": "CLEAR_TIMEOUT"}
        except OSError:
            return {"attempted": True, "cleared": False, "reason": "CLEAR_START_FAILED"}
    return {"attempted": True, "cleared": result.returncode == 0,
            "worker_exit_code": result.returncode}


def new_run(output_root, prefix):
    output_root = output_root.expanduser().resolve()
    if output_root.is_relative_to(ROOT):
        raise ValueError("PRIVATE_OUTPUT_INSIDE_REPOSITORY")
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=output_root))


def replay_asr(args):
    """Decode a saved native input without microphone, VAD, LLM or speaker."""
    from sbd.core.config import load_config
    from sbd.perception.listen.whispercpp.supervisor import NativeWorker
    config = load_config(local_path=args.config.resolve(), dotenv_path=ROOT / ".env")
    asr = config.perception.listen.adapter
    if asr.driver != "whispercpp":
        raise ValueError("WHISPERCPP_REQUIRED")
    run = new_run(args.output_root, "asr-replay-")
    source = args.replay_asr.resolve()
    with wave.open(str(source)) as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype()) != (16000, 1, 2, "NONE"):
            raise ValueError("ASR_WAV_FORMAT_INVALID")
        pcm = wav.readframes(wav.getnframes())
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    scaled = [round(sample * args.gain) for sample in samples]
    clipped = sum(not -32768 <= sample <= 32767 for sample in scaled)
    converted = array.array("h", [max(-32768, min(32767, sample)) for sample in scaled])
    if sys.byteorder != "little":
        converted.byteswap()
    native_input = run / "native-input.wav"
    with wave.open(str(native_input), "wb") as wav:
        os.chmod(native_input, 0o600)
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(converted.tobytes())
    result = {"mode": "ASR_RECORDING_REPLAY", "source": str(source), "gain": args.gain,
              "clipped_samples": clipped, "input_samples": len(samples), "status": "ERROR"}
    worker = NativeWorker(asr.worker_path, asr.model_path, run)
    try:
        result["text"], result["latency_ms"] = worker.transcribe(native_input)
        result["status"] = "DECODED"
    except Exception as error:
        result.update(error_type=type(error).__name__, reason=str(error))
        if isinstance(error, UnicodeDecodeError):
            path = run / "invalid-native-text.bin"
            path.write_bytes(error.object)
            path.chmod(0o600)
    finally:
        worker.terminate()
    private_json(run / "result.json", result)
    print(f"ASR replay {result['status']}; private result saved: {run}", flush=True)
    return 0 if result["status"] == "DECODED" else 2


def run_session(args):
    run = new_run(args.output_root, "manual-")
    config = run / "product.local.yaml"
    snapshot_config(args.config.resolve(), config)
    print(f"Diagnostic record: {run}", flush=True)
    print("Wait for standby, then use the physical Button and microphone.", flush=True)
    print("Private ASR text/audio are recorded. Stop with long press or Ctrl+C.", flush=True)
    print("After a failed exit, this wrapper attempts a separate bounded display clear.", flush=True)
    acoustic = load_script("run-acoustic-asr")
    previous = sys.argv
    sys.argv = ["run-acoustic-asr", "--manual", "--installed-entry", str(args.installed_entry.absolute()),
                "--config", str(config), "--python", str(args.python.absolute()),
                "--output", str(run / "observation"), "--watchdog", str(args.watchdog),
                "--cleanup-timeout", str(args.cleanup_timeout)]
    try:
        diagnostic_exit = acoustic.main()
    finally:
        sys.argv = previous
    result = json.loads((run / "observation/result.json").read_text())
    app_exit = result.get("app_exit_code")
    # The App's failure remains a failure even when a separate panel clear succeeds.
    exit_code = app_exit if isinstance(app_exit, int) and app_exit != 0 else diagnostic_exit
    cleanup = {"attempted": False, "cleared": None}
    if exit_code != 0:
        cleanup = post_exit_clear(args.python.absolute(), config, run / "display-clear.log", args.clear_timeout)
        print("Post-exit display clear: " + ("OK" if cleanup["cleared"] else "FAILED; see display-clear.log"), flush=True)
    private_json(run / "session-result.json", {
        "diagnostic_exit_code": diagnostic_exit, "app_exit_code": app_exit,
        "exit_code": exit_code, "display_cleanup": cleanup})
    print(f"Records saved: {run}", flush=True)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--installed-entry", type=Path, default=ROOT / "scripts/run-app.sh")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output-root", type=Path, default=Path.home() / "snowboard-debug")
    parser.add_argument("--watchdog", type=int, default=1800)
    parser.add_argument("--cleanup-timeout", type=int, default=20)
    parser.add_argument("--clear-timeout", type=int, default=10)
    parser.add_argument("--replay-asr", type=Path, help="Decode a saved 16 kHz mono WAV; no live App or hardware.")
    parser.add_argument("--gain", type=float, default=1, help="Gain for a replay copy only; product capture is unchanged.")
    parser.add_argument("--clear-display-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.umask(0o077)
    if min(args.watchdog, args.cleanup_timeout, args.clear_timeout) <= 0:
        parser.error("timeouts must be positive")
    if not math.isfinite(args.gain) or not 0 < args.gain <= 32:
        parser.error("replay gain must be finite and between 0 and 32")
    if args.gain != 1 and args.replay_asr is None:
        parser.error("--gain requires --replay-asr")
    if args.clear_display_worker:
        try:
            asyncio.run(clear_display(args.config))
        except Exception as error:
            print(json.dumps({"cleared": False, "error_type": type(error).__name__,
                              "reason": str(error)}), flush=True)
            return 1
        print(json.dumps({"cleared": True, "display_closed": True}), flush=True)
        return 0
    if args.replay_asr:
        return replay_asr(args)
    return run_session(args)


if __name__ == "__main__":
    raise SystemExit(main())
