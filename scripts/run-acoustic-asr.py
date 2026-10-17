#!/usr/bin/env python3
"""One acoustic diagnostic through the regular App launcher and live Listen.

Run on Pi with --installed-entry, --config, --fixtures, --python and --output.
After inspecting private/microphone.wav, --annotate OUTPUT --speech-end-sample N
--uncertainty-ms M adds an independent acoustic-end estimate without replay.
Playback drain and parent ENDPOINT receipt are not the physical speech end.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.alpha_oracle import CLEANUP, InvalidObservation, require
from scripts.alpha_product import FIXTURE_TEXT, private_json, resolve_fixtures


def match_reference(captured, reference):
    """Independent signal alignment, never using VAD or playback timestamps.

    Match three speech sections independently. Reject an ambiguous match rather
    than silently treating playback drain as the microphone speech endpoint.
    """
    import numpy as np
    x = np.frombuffer(captured, dtype="<i2").astype(float)
    source = np.frombuffer(reference, dtype="<i2").astype(float)
    nonzero = np.flatnonzero(source)
    require(len(nonzero) > 0, "REFERENCE_SILENT")
    speech = source[nonzero[0]:nonzero[-1] + 1]
    require(len(x) >= len(speech) and len(speech) >= 960, "ALIGNMENT_AUDIO_TOO_SHORT")

    def peak(template):
        template = template - template.mean()
        n = 1 << (len(x) + len(template) - 2).bit_length()
        numerator = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(template[::-1], n), n)
        numerator = numerator[len(template) - 1:len(x)]
        sums = np.r_[0., np.cumsum(x)]
        squares = np.r_[0., np.cumsum(x * x)]
        energy = squares[len(template):] - squares[:-len(template)]
        energy -= (sums[len(template):] - sums[:-len(template)]) ** 2 / len(template)
        scale = float(np.dot(template, template))
        require(scale > 0, "REFERENCE_SEGMENT_SILENT")
        scores = numerator / np.sqrt(np.maximum(energy, 1) * scale)
        index = int(np.argmax(np.abs(scores)))
        return index, float(abs(scores[index]))

    lag, score = peak(speech)
    lags, scores = [], []
    splits = np.linspace(0, len(speech), 4, dtype=int)
    for start, end in zip(splits[:-1], splits[1:]):
        section_lag, section_score = peak(speech[start:end])
        lags.append(section_lag - int(start))
        scores.append(section_score)
    # Three sections agreeing within 3 ms guards against unrelated/background
    # matches. 0.2 is a diagnostic correlation floor, not a product threshold.
    require(min(scores) >= 0.2 and max(lags + [lag]) - min(lags + [lag]) <= 48,
            "REFERENCE_MATCH_AMBIGUOUS")
    signal_end = lag + len(speech)
    require(0 <= signal_end <= len(x), "REFERENCE_END_OUTSIDE_CAPTURE")
    return {"reference_match_sections": 3, "reference_min_correlation": min(scores),
            "reference_full_correlation": score, "alignment_spread_ms": (max(lags) - min(lags)) / 16,
            "matched_reference_end_sample": signal_end,
            "matched_reference_end_to_capture_end_s": (len(x) - signal_end) / 16000,
            "signal_end_definition": "Last nonzero reference sample aligned to microphone waveform; not human audible-end annotation."}


def diagnose(value, child_trace, turn_index=0):
    row = value["turns"][turn_index]
    events = [e for e in child_trace["events"] if e["request_id"] == row["asr_wire"][0]["request_id"]]
    def one(stage):
        matches = [e for e in events if e["stage"] == stage]
        require(len(matches) == 1, "CHILD_DIAGNOSTIC_NODE_MISSING")
        return matches[0]
    endpoint = [e for e in events if e["stage"] == "frame_decision" and e["endpoint"]]
    require(len(endpoint) == 1, "VAD_ENDPOINT_MISSING")
    endpoint = endpoint[0]
    require(endpoint["frame_count"] == len(row["microphone_frames"]), "VAD_FRAME_CORRELATION_INVALID")
    windows = [e for e in events if e["stage"] == "vad_window"]
    require(bool(windows) and windows[-1]["speech_end_ms"] is not None, "VAD_END_MISSING")
    confirmed = next(e for e in windows if e["speech_end_ms"] == windows[-1]["speech_end_ms"])
    compute = one("native_compute")
    native_begin, native_end = one("native_command_begin"), one("native_command_end")
    wav_begin, wav_end = one("wav_begin"), one("wav_end")
    emitted, returned = one("endpoint_emit"), one("result_emit")
    stamps = [endpoint["monotonic_ns"], wav_begin["monotonic_ns"], wav_end["monotonic_ns"],
              emitted["monotonic_ns"], native_begin["monotonic_ns"], compute["monotonic_ns"],
              native_end["monotonic_ns"], returned["monotonic_ns"], row["nodes"]["asr_final"]]
    require(stamps == sorted(stamps), "CHILD_TIMING_ORDER_INVALID")
    native_wall_s = compute["wall_us"] / 1e6
    require(0 < native_wall_s <= (native_end["monotonic_ns"] - native_begin["monotonic_ns"]) / 1e9,
            "NATIVE_COMPUTE_COUNTER_INVALID")
    transitions = [e for e in value.get("state_changes", [])
                   if e["monotonic_ns"] > endpoint["monotonic_ns"]]
    require(bool(transitions) and transitions[0]["state"] == "THINK", "ASR_STATE_TRANSITION_MISSING")
    return {"vad_possible_end_sample_ms": windows[-1]["possible_end_ms"],
            "vad_confirmed_at_window_ms": confirmed["window_start_ms"],
            "vad_endpoint_capture_ms": endpoint["frame_count"] * 20,
            "vad_end_to_endpoint_sample_ms": endpoint["frame_count"] * 20 - windows[-1]["speech_end_ms"],
            "vad_frame_processing_max_ms": max(e["processing_ns"] for e in events if e["stage"] == "frame_decision") / 1e6,
            "wav_preparation_ms": (wav_end["monotonic_ns"] - wav_begin["monotonic_ns"]) / 1e6,
            "native_whisper_compute_s": native_wall_s,
            "native_whisper_cpu_s": compute["cpu_us"] / 1e6,
            "native_command_total_s": (native_end["monotonic_ns"] - native_begin["monotonic_ns"]) / 1e9,
            "native_end_to_result_emit_ms": (returned["monotonic_ns"] - native_end["monotonic_ns"]) / 1e6,
            "endpoint_decision_to_asr_final_s": (row["nodes"]["asr_final"] - endpoint["monotonic_ns"]) / 1e9,
            "app_perception_after_endpoint_s": (transitions[0]["monotonic_ns"] - endpoint["monotonic_ns"]) / 1e9,
            "app_receiving_at_endpoint": row["asr_wire"][0]["app_state"] == "PERCEPTION",
            "display_receiving_at_endpoint": row["asr_wire"][0]["display_state"] == "PERCEPTION",
            "app_receiving_at_asr_result": row["asr_wire"][1]["app_state"] == "PERCEPTION",
            "display_receiving_at_asr_result": row["asr_wire"][1]["display_state"] == "PERCEPTION"}


def summarize(value, turn_index=0, reference_text=None):
    require(value.get("driver_complete") is True, value.get("failure_code", "DRIVER_INCOMPLETE"))
    require(value.get("launcher_exit_code") == 0 and value.get("exit_code") == 0, "APP_EXIT_FAILED")
    require(all(value.get("cleanup", {}).get(k) is True for k in CLEANUP), "OWNER_RELEASE_FAILED")
    rows = value.get("turns", [])
    require(len(rows) in {1, 2}, "TURN_COUNT_INVALID")
    row = rows[turn_index]
    require(row.get("acoustic", {}).get("app_receiving") is True
            and row["acoustic"].get("playback_drained") is True, "ACOUSTIC_INPUT_INCOMPLETE")
    require(row.get("capture_closed") is True and row.get("asr_terminal") is True
            and row.get("llm_terminal") is True and row.get("audio_complete") is True
            and row.get("route_valid") is True, "APP_TURN_INCOMPLETE")
    normalize = lambda text: "".join(c for c in text if c.isalnum())
    expected = FIXTURE_TEXT["FX-SHORT-B"] if reference_text is None else reference_text
    require(normalize(row["asr"][0]["text"]) == normalize(expected),
            "ACOUSTIC_ASR_TEXT_MISMATCH")
    nodes = row["nodes"]
    required = ("first_frame", "last_frame", "stimulus_first_write", "stimulus_play_drained",
                "asr_endpoint_received", "asr_result_received", "asr_final", "audio_complete")
    require(all(type(nodes.get(k)) is int for k in required), "TIMING_NODE_MISSING")
    require(nodes["first_frame"] <= nodes["stimulus_first_write"] <= nodes["last_frame"]
            <= nodes["asr_endpoint_received"] <= nodes["asr_result_received"] <= nodes["asr_final"],
            "TIMING_ORDER_INVALID")
    wire = row.get("asr_wire", [])
    require(len(wire) == 2 and [e["event"] for e in wire] == ["ENDPOINT", "RESULT"]
            and wire[0]["request_id"] == wire[1]["request_id"]
            and wire[0]["captured_frames"] == len(row["microphone_frames"]), "ASR_CORRELATION_INVALID")
    writes = [f["audio_first_write"] for f in row["fragments"] if "audio_first_write" in f]
    require(bool(writes), "RESPONSE_AUDIO_MISSING")
    return {"mode": "APP_ACOUSTIC_DIAGNOSTIC", "disposition": "VALID_OBSERVATION",
            "capture_frames": len(row["microphone_frames"]),
            "asr_text_matched": True, "app_turn_completed": True, "owners_released": True,
            "last_frame_to_endpoint_received_s": (nodes["asr_endpoint_received"] - nodes["last_frame"]) / 1e9,
            "endpoint_received_to_asr_final_s": (nodes["asr_final"] - nodes["asr_endpoint_received"]) / 1e9,
            "last_frame_to_asr_final_s": (nodes["asr_final"] - nodes["last_frame"]) / 1e9,
            "asr_final_to_response_first_write_s": (min(writes) - nodes["asr_final"]) / 1e9,
            "native_command_wait_ms": wire[1]["latency_ms"],
            "acoustic_speech_end": "NOT_ANNOTATED",
            "limits": ["Endpoint is parent event receipt after child WAV preparation, not exact VAD decision.",
                       "Native command wait includes IPC/worker response, not pure Whisper computation.",
                       "Frame receipt timestamps include capture buffering; acoustic end needs annotation uncertainty.",
                       "No human hearing or whole-ALPHA acceptance."]}


def annotate(args):
    output = args.annotate.resolve()
    value = json.loads((output / "private/run-observation.json").read_text())
    reference = output / "private/reference.json"
    expected = json.loads(reference.read_text())["text"] if reference.exists() else None
    report = summarize(value, reference_text=expected)
    row = value["turns"][0]
    sample = args.speech_end_sample
    require(type(sample) is int and 0 <= sample < len(row["microphone_frames"]) * 320,
            "SPEECH_END_SAMPLE_INVALID")
    require(args.uncertainty_ms is not None and args.uncertainty_ms > 0, "ANNOTATION_UNCERTAINTY_REQUIRED")
    frame, offset = divmod(sample, 320)
    # Nominal sample position inside the frame ending at its observed receipt.
    estimate = row["microphone_frames"][frame] - 20_000_000 + round(offset / 16000 * 1e9)
    endpoint = row["nodes"]["asr_endpoint_received"]
    require(estimate <= endpoint, "SPEECH_END_AFTER_ENDPOINT")
    report.update(acoustic_speech_end="ANNOTATED_ESTIMATE",
                  acoustic_end_to_endpoint_received_s=(endpoint - estimate) / 1e9,
                  annotation_uncertainty_ms=args.uncertainty_ms,
                  capture_buffering_error_bound_ms=None)
    private_json(output / "private/acoustic-end-annotation.json",
                 {"sample": sample, "uncertainty_ms": args.uncertainty_ms})
    private_json(output / "acoustic-end-result.json", report)
    print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--installed-entry", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--fixtures", type=Path)
    p.add_argument("--reference-wav", type=Path, help="Custom recording for acoustic diagnosis; not a fixed ALPHA fixture.")
    p.add_argument("--reference-text", help="Expected words in --reference-wav; saved privately.")
    p.add_argument("--python", type=Path, default=Path(sys.executable))
    p.add_argument("--output", type=Path)
    p.add_argument("--turns", type=int, choices=(1, 2), default=1,
                   help="Two Turns reuse one App, Session and the same spoken fixture.")
    p.add_argument("--manual", action="store_true", help="Observe real USER speech/buttons; never play a fixture.")
    p.add_argument("--watchdog", type=int, default=180)
    p.add_argument("--cleanup-timeout", type=int, default=20)
    p.add_argument("--annotate", type=Path)
    p.add_argument("--speech-end-sample", type=int)
    p.add_argument("--uncertainty-ms", type=float)
    args = p.parse_args()
    os.umask(0o077)
    if args.annotate:
        annotate(args)
        return 0
    require(bool(args.reference_wav) == bool(args.reference_text), "CUSTOM_REFERENCE_PAIR_REQUIRED")
    if args.reference_wav:
        require(not args.manual and args.fixtures is None, "CUSTOM_REFERENCE_MODE_INVALID")
        args.fixtures = Path("/dev/null")  # Replaced below by an explicit private custom binding.
    if args.manual and args.fixtures is None:
        args.fixtures = Path("/dev/null")  # Unused: live M has no fixture source.
    require(all((args.installed_entry, args.config, args.fixtures, args.output)), "ARGUMENTS_REQUIRED")
    require(args.watchdog > 0 and args.cleanup_timeout > 0, "TIMEOUT_INVALID")
    output = args.output.resolve()
    require(not output.is_relative_to(ROOT), "OUTPUT_INSIDE_REPOSITORY")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = output / "private"
    private.mkdir(mode=0o700)
    if args.reference_wav:
        args.fixtures = private / "reference-fixtures.json"
        private_json(args.fixtures, {"FX-SHORT-B": str(args.reference_wav.resolve())})
        private_json(private / "reference.json", {
            "text": args.reference_text, "wav": str(args.reference_wav.resolve()),
            "custom_diagnostic": True, "formal_fixed_fixture": False})
    spec = importlib.util.spec_from_file_location("alpha_runner", ROOT / "scripts/run-alpha-pv.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    value = runner.run_child(SimpleNamespace(**vars(args), run="pn", phase="diagnostic",
                             cause_control_reason=None,
                             diagnostic_role=None if args.manual else "paired_turns" if args.turns == 2 else "single_request",
                             acoustic=not args.manual),
                             private, "pn")
    private_json(private / "run-observation.json", value)
    if args.manual:
        failed = (bool(value.get("errors")) or value.get("exit_code") != 0 or value.get("launcher_exit_code") != 0
                  or value.get("failure_code") == "RUNNER_WATCHDOG"
                  or not all(value.get("cleanup", {}).get(k) is True for k in CLEANUP))
        report = {"mode": "APP_MANUAL_DIAGNOSTIC", "disposition": "FAIL" if failed else "PENDING_USER_REPORT",
                  "turn_count": len(value.get("turns", [])),
                  "session_count": len({r["session_id"] for r in value.get("turns", [])}),
                  "app_exit_code": value.get("exit_code"), "cleanup": value.get("cleanup"),
                  "errors": value.get("errors", [])}
        private_json(output / "result.json", report)
        print(json.dumps(report, indent=2))
        return 2 if failed else 0
    try:
        require(len(value.get("turns", [])) == args.turns, value.get("failure_code", "TURN_COUNT_INVALID"))
        if args.turns == 2:
            first, second = value["turns"]
            require(first["session_id"] == second["session_id"] and first["turn_id"] != second["turn_id"]
                    and value.get("engine_reused") is True and value.get("child_reused") is True
                    and all(s.get("backend_reused") is True for s in value["sessions"]), "SAME_SESSION_REUSE_REQUIRED")
            require(first["asr_wire"][0]["request_id"] != second["asr_wire"][0]["request_id"],
                    "ASR_REQUEST_REUSE_INVALID")
        child_trace = json.loads((private / "asr-child-trace.json").read_text())
        import wave
        reports = []
        reference = resolve_fixtures(args.fixtures, {"FX-SHORT-B"})["FX-SHORT-B"]
        for index, row in enumerate(value["turns"]):
            report = summarize(value, index, args.reference_text)
            report["diagnosis"] = diagnose(value, child_trace, index)
            with wave.open(str(private / row.get("microphone_file", "microphone.wav")), "rb") as wav:
                captured = wav.readframes(wav.getnframes())
            report["signal_alignment"] = match_reference(captured, reference)
            end = report["signal_alignment"]["matched_reference_end_sample"]
            frame, offset = divmod(end, 320)
            signal_end = row["microphone_frames"][frame] - 20_000_000 + round(offset / 16000 * 1e9)
            transitions = value["state_changes"]
            receiving = max(e["monotonic_ns"] for e in transitions if e["state"] == "PERCEPTION"
                            and e["monotonic_ns"] <= row["nodes"]["first_frame"])
            thinking = next(e["monotonic_ns"] for e in transitions if e["state"] == "THINK"
                            and e["monotonic_ns"] >= row["nodes"]["asr_final"])
            action = next(e["monotonic_ns"] for e in transitions if e["state"] == "ACTION"
                          and e["monotonic_ns"] >= thinking)
            native_begin = next(e["monotonic_ns"] for e in child_trace["events"]
                                if e["stage"] == "native_command_begin" and e["request_id"] == row["asr_wire"][0]["request_id"])
            writes = [f["audio_first_write"] for f in row["fragments"] if "audio_first_write" in f]
            report["timeline"] = {
                "receiving_to_native_command_s": (native_begin - receiving) / 1e9,
                "native_command_to_think_s": (thinking - native_begin) / 1e9,
                "receiving_to_think_s": (thinking - receiving) / 1e9,
                "matched_signal_end_to_think_s": (thinking - signal_end) / 1e9,
                "matched_signal_end_to_action_s": (action - signal_end) / 1e9,
                "matched_signal_end_to_response_first_write_s": (min(writes) - signal_end) / 1e9,
                "think_to_action_s": (action - thinking) / 1e9}
            reports.append(report)
        report = reports[0] if args.turns == 1 else {
            "mode": "APP_ACOUSTIC_PAIRED_DIAGNOSTIC", "disposition": "VALID_OBSERVATION",
            "same_session": True, "backends_reused": True, "turns": reports,
            "turn2_minus_turn1_s": {key: reports[1]["timeline"][key] - reports[0]["timeline"][key]
                                     for key in reports[0]["timeline"]}}
    except (OSError, ValueError) as exc:
        report = {"mode": "APP_ACOUSTIC_DIAGNOSTIC", "disposition": "INVALID",
                  "reason_code": "CHILD_DIAGNOSTIC_UNAVAILABLE"}
    except InvalidObservation as exc:
        report = {"mode": "APP_ACOUSTIC_DIAGNOSTIC", "disposition": "INVALID",
                  "reason_code": exc.code}
    if args.reference_wav:
        report["mode"] = "APP_RECORDING_ACOUSTIC_DIAGNOSTIC"
        report["custom_recording"] = True
    private_json(output / "result.json", report)
    print(json.dumps(report, indent=2))
    return 0 if report["disposition"] == "VALID_OBSERVATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
