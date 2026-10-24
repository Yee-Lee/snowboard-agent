"""Human diagnostic boundaries: private output, real exit status and safe post-clear."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def debug():
    path = Path(__file__).resolve().parents[1] / "scripts/run-manual-debug.py"
    spec = importlib.util.spec_from_file_location("manual_debug", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_config_snapshot_preserves_relative_assets_and_source(debug, tmp_path):
    import yaml
    source = tmp_path / "source.yaml"
    source.write_text("perception:\n  look:\n    adapter:\n      model_path: relative/model.bin\n")
    before = source.read_bytes()
    run = tmp_path / "run"
    run.mkdir()
    output = run / "config.yaml"
    debug.snapshot_config(source, output)
    saved = yaml.safe_load(output.read_text())
    assert saved["perception"]["look"]["adapter"]["model_path"] == str(tmp_path / "relative/model.bin")
    assert saved["log"]["file"] == str(run / "application.log")
    assert source.read_bytes() == before
    assert output.stat().st_mode & 0o777 == 0o600


def test_display_clear_refuses_active_app_before_touching_devices(debug, monkeypatch):
    monkeypatch.setattr(debug, "load_script", lambda name: NS(no_previous_app=lambda: False))
    def forbidden(*args, **kwargs):
        raise AssertionError("device inspection must not run while App is active")
    monkeypatch.setattr(debug.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="APP_STILL_RUNNING"):
        debug.assert_display_available(NS())


def test_recording_replay_preserves_original_pcm_and_does_not_claim_quality_pass(debug, tmp_path, monkeypatch):
    import array
    import wave
    import sbd.core.config
    from sbd.perception.listen.whispercpp import supervisor
    original = array.array("h", [1200, -1400] * 320).tobytes()
    recording = tmp_path / "original.wav"
    with wave.open(str(recording), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(original)
    before = recording.read_bytes()
    config = NS(perception=NS(listen=NS(adapter=NS(driver="whispercpp", worker_path="worker", model_path="model"))))
    monkeypatch.setattr(sbd.core.config, "load_config", lambda **kwargs: config)
    stopped = []
    class Worker:
        def __init__(self, binary, model, root): pass
        def transcribe(self, path):
            with wave.open(str(path)) as wav:
                assert wav.readframes(wav.getnframes()) == original
            return "辨識結果不代表正確", 3.5
        def terminate(self): stopped.append(True)
    monkeypatch.setattr(supervisor, "NativeWorker", Worker)
    args = NS(config=tmp_path / "config", replay_asr=recording, gain=1, output_root=tmp_path / "private")
    assert debug.replay_asr(args) == 0
    run, = args.output_root.iterdir()
    result = json.loads((run / "result.json").read_text())
    assert result["status"] == "DECODED" and "PASS" not in result.values()
    assert result["clipped_samples"] == 0 and stopped == [True]
    assert recording.read_bytes() == before


def test_failed_panel_present_still_closes_device(debug, tmp_path, monkeypatch):
    import sbd.core.display
    source = tmp_path / "config.yaml"
    source.write_text("{}")
    closed = []
    class Display:
        async def start(self): pass
        def clear(self): pass
        def show(self): raise RuntimeError("panel write failed")
        async def stop(self): closed.append(True)
    monkeypatch.setattr(debug, "assert_display_available", lambda config: None)
    monkeypatch.setattr(sbd.core.display, "make_display", lambda config: Display())
    with pytest.raises(RuntimeError, match="panel write failed"):
        asyncio.run(debug.clear_display(source))
    assert closed == [True]


def test_hung_clear_worker_is_killed_and_reported_without_hiding_app_failure(debug, tmp_path):
    python = tmp_path / "hung-python"
    python.write_text(f"#!{sys.executable}\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n")
    python.chmod(0o700)
    log = tmp_path / "clear.log"
    result = debug.post_exit_clear(python, tmp_path / "config.yaml", log, 0.5)
    assert result == {"attempted": True, "cleared": False, "reason": "CLEAR_TIMEOUT"}
    pid = int(log.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("app_exit,diagnostic_exit", [(4, 2), (0, 0)])
def test_manual_keeps_failed_evidence_and_exit_even_when_panel_clear_succeeds(
        debug, tmp_path, monkeypatch, app_exit, diagnostic_exit):
    source = tmp_path / "source.yaml"
    source.write_text("{}")
    original = {"app_exit_code": app_exit, "disposition": "FAIL" if app_exit else "PENDING_USER_REPORT",
                "cleanup": {"alsa_absent": app_exit == 0}}
    def diagnostic():
        assert "--manual" in sys.argv
        output = Path(sys.argv[sys.argv.index("--output") + 1])
        output.mkdir()
        (output / "result.json").write_text(json.dumps(original))
        return diagnostic_exit
    monkeypatch.setattr(debug, "load_script", lambda name: NS(main=diagnostic))
    calls = []
    def clear(*args):
        calls.append(args)
        return {"attempted": True, "cleared": True, "worker_exit_code": 0}
    monkeypatch.setattr(debug, "post_exit_clear", clear)
    args = NS(output_root=tmp_path / "private", config=source,
              installed_entry=tmp_path / "run.sh", python=Path(sys.executable),
              watchdog=10, cleanup_timeout=2, clear_timeout=2)
    assert debug.run_session(args) == app_exit
    run, = args.output_root.iterdir()
    assert json.loads((run / "observation/result.json").read_text()) == original
    assert json.loads((run / "session-result.json").read_text())["app_exit_code"] == app_exit
    assert bool(calls) is (app_exit != 0)
    assert run.stat().st_mode & 0o777 == 0o700
