#!/usr/bin/env python3
"""Opt-in measurement wrapper around the real ASR supervisor; no wire changes.

Keep numeric observations in memory until shutdown so capture has no diagnostic
disk writes. The production VAD, endpoint detector and native worker run intact.
"""
from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class Trace:
    def __init__(self, path):
        self.path = Path(path)
        self.request_id = None
        self.rows = []

    def record(self, stage, **values):
        self.rows.append({"stage": stage, "request_id": self.request_id,
                          "monotonic_ns": time.monotonic_ns(), **values})

    def save(self):
        descriptor, temporary = tempfile.mkstemp(prefix=".asr-trace-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as sink:
                json.dump({"clock": "pi_monotonic", "events": self.rows}, sink)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def install_observers(target, path):
    trace = Trace(path)
    read_control = target.read_control
    observe = target.EndpointDetector.observe
    add_frame = target.StreamingEndpoint.add_frame
    write_wav = target.write_wav
    transcribe = target.NativeWorker.transcribe
    emit = target.emit
    exit_after_ack = target._exit_after_shutdown_ack

    def control():
        value = read_control()
        if value is not None and value.get("op") == "BEGIN":
            trace.request_id = value["request_id"]
            trace.record("begin_received")
        return value

    def vad_decision(self, probability, window_start_ms):
        result = observe(self, probability, window_start_ms)
        trace.record("vad_window", probability=probability, window_start_ms=window_start_ms,
                     possible_end_ms=self.possible_end_ms, speech_start_ms=self.speech_start_ms,
                     speech_end_ms=self.speech_end_ms, triggered=self.triggered)
        return result

    def intake(self, frame):
        started = time.monotonic_ns()
        result = add_frame(self, frame)
        trace.record("frame_decision", frame_count=self.captured_frames, endpoint=result,
                     processing_ns=time.monotonic_ns() - started)
        return result

    def wav(path, pcm):
        trace.record("wav_begin", samples=len(pcm) // 2)
        result = write_wav(path, pcm)
        retained = trace.path.with_name(f"{trace.path.stem}-{path.parent.name}-request-{trace.request_id}.wav")
        trace.record("wav_end", native_input_file=retained.name)
        # Capture is complete. Keep the exact bounded native input before
        # recovery deletes its workdir; never rebuild it from VAD timestamps.
        with retained.open("xb") as sink, path.open("rb") as source:
            os.chmod(retained, 0o600)
            shutil.copyfileobj(source, sink)
        trace.record("native_input_retained")
        return result

    def native(self, path):
        trace.record("native_command_begin")
        try:
            return transcribe(self, path)
        except Exception as error:
            trace.record("native_exception", kind=type(error).__name__, reason=str(error))
            raise
        finally:
            trace.record("native_command_end")

    if hasattr(target.NativeWorker, "_line"):
        line = target.NativeWorker._line
        def native_line(self, timeout):
            value = line(self, timeout)
            fields = value.split("\t")
            if len(fields) == 5 and fields[0] == "RESULT":
                trace.record("native_compute", wall_us=int(fields[2]), cpu_us=int(fields[3]))
            elif len(fields) == 2 and fields[0] == "ERROR":
                trace.record("native_error", reason=fields[1])
            return value
        target.NativeWorker._line = native_line

    def event(value):
        if value.get("event") in {"ENDPOINT", "RESULT", "ERROR", "CANCELLED"}:
            trace.record(value["event"].lower() + "_emit")
        if value.get("event") == "ERROR":
            # Capture has ended. Retain the failed native request before the
            # parent destroys/replaces this child and removes its workdir.
            trace.save()
        return emit(value)

    def exit_cleanly():
        trace.save()
        exit_after_ack()

    target.read_control = control
    target.EndpointDetector.observe = vad_decision
    target.StreamingEndpoint.add_frame = intake
    target.write_wav = wav
    target.NativeWorker.transcribe = native
    target.emit = event
    target._exit_after_shutdown_ack = exit_cleanly
    return trace


def main():
    index = sys.argv.index("--diagnostic-output")
    path = Path(sys.argv[index + 1])
    del sys.argv[index:index + 2]
    # The isolated VAD runtime has no controller/Pydantic dependencies. Load the
    # same supervisor file directly, as the production child command does.
    spec = importlib.util.spec_from_file_location("acoustic_asr_supervisor",
        ROOT / "src/sbd/perception/listen/whispercpp/supervisor.py")
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    trace = install_observers(supervisor, path)
    try:
        return supervisor.main()
    finally:
        trace.save()


if __name__ == "__main__":
    raise SystemExit(main())
