"""Interactive local review for energy-assisted VAD label proposals."""

from __future__ import annotations

import argparse
import array
import json
import math
import signal
import shutil
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Any

from .fixture_recorder import discover_voicehat_device


def _write_preview(source: Path, destination: Path, start_ms: int, end_ms: int) -> float:
    """Write a temporary peak-normalized dual-mono preview; source is immutable."""
    with wave.open(str(source), "rb") as input_wav:
        rate = input_wav.getframerate()
        start = max(0, start_ms * rate // 1000)
        end = min(input_wav.getnframes(), end_ms * rate // 1000)
        input_wav.setpos(start)
        payload = input_wav.readframes(max(0, end - start))
    values = array.array("i")
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    channel = values[0::2]
    peak = max((abs(value) for value in channel), default=0)
    gain = min(10 ** (24 / 20), (2147483647 * 0.7079 / peak) if peak else 1.0)
    dual = array.array("i")
    for value in channel:
        scaled = max(-2147483648, min(2147483647, round(value * gain)))
        dual.extend((scaled, scaled))
    if sys.byteorder != "little":
        dual.byteswap()
    with wave.open(str(destination), "wb") as output_wav:
        output_wav.setnchannels(2)
        output_wav.setsampwidth(4)
        output_wav.setframerate(rate)
        output_wav.writeframes(dual.tobytes())
    return round(20 * math.log10(gain), 2)


def _preview_ranges(proposal: dict[str, Any]) -> list[tuple[str, int, int]]:
    intervals = proposal["speech_intervals_ms"]
    ranges = [("start", max(0, intervals[0][0] - 500), intervals[0][0] + 500)]
    ranges.append(("end", max(0, intervals[-1][1] - 500), intervals[-1][1] + 500))
    pause = proposal.get("internal_pause_candidate_ms")
    if pause:
        ranges.append(("pause", max(0, pause[0] - 500), pause[1] + 500))
    return ranges


def _parse_override(answer: str, proposal: dict[str, Any]) -> tuple[list[list[int]], list[int] | None]:
    values = [int(value.strip()) for value in answer.split(",")]
    if proposal["class"] == "clear_speech" and len(values) == 2 and values[0] < values[1]:
        return [[values[0], values[1]]], None
    if proposal["class"] == "pause" and len(values) == 4 and values[0] < values[1] < values[2] < values[3]:
        return [[values[0], values[1]], [values[2], values[3]]], [values[1], values[2]]
    raise ValueError("clear requires start,end; pause requires start,pause_start,pause_end,end")


def review(proposals_path: Path, artifact_dir: Path, output_path: Path, playback_device: str | None) -> int:
    document = json.loads(proposals_path.read_text(encoding="utf-8"))
    existing = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {"accepted": {}}
    accepted = existing.setdefault("accepted", {})
    preview_dir = output_path.parent / "label-preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    if playback_device is None:
        if shutil.which("aplay") is None:
            raise RuntimeError("aplay is unavailable")
        playback_device = discover_voicehat_device("aplay")
    player: subprocess.Popen[str] | None = None
    paused_at: float | None = None
    elapsed_before_pause = 0.0
    timer_stop = threading.Event()

    def elapsed_ms() -> int:
        if paused_at is not None:
            return round(elapsed_before_pause * 1000)
        return round((elapsed_before_pause + (time.monotonic() - started_at)) * 1000)

    started_at = time.monotonic()

    def timer() -> None:
        while not timer_stop.wait(0.1):
            if player is not None and player.poll() is None:
                print(f"\rplayback={elapsed_ms()} ms", end="", flush=True)

    threading.Thread(target=timer, daemon=True).start()
    for proposal in document["proposals"]:
        fixture_id = proposal["fixture_id"]
        if fixture_id in accepted:
            continue
        source = artifact_dir / f"{fixture_id}.wav"
        print(f"\n{fixture_id} ({proposal['class']}, {proposal['category']})")
        intervals = proposal["speech_intervals_ms"]
        pause = proposal.get("internal_pause_candidate_ms")
        if proposal["class"] == "clear_speech":
            labels = {"s": intervals[0][0], "e": intervals[0][1]}
        else:
            labels = {"s": intervals[0][0], "w": pause[0], "c": pause[1], "e": intervals[-1][1]}
        full_preview = preview_dir / f"{fixture_id}-full.wav"
        duration_ms = max(interval[-1] for interval in intervals)
        gain_db = _write_preview(source, full_preview, 0, duration_ms)
        print(f"suggested={labels}; full preview gain={gain_db:+.2f} dB")
        while True:
            answer = input("p=play, u=pause, r=replay, s/e/w/c=<ms>, Enter=accept, q=quit: ").strip().lower()
            if not answer:
                if proposal["class"] == "clear_speech":
                    intervals, pause = [[labels["s"], labels["e"]]], None
                else:
                    intervals, pause = [[labels["s"], labels["w"]], [labels["c"], labels["e"]]], [labels["w"], labels["c"]]
            elif answer in {"p", "r"}:
                if player is not None and player.poll() is None:
                    if answer == "p" and paused_at is not None:
                        player.send_signal(signal.SIGCONT)
                        elapsed_before_pause += time.monotonic() - paused_at
                        paused_at = None
                        started_at = time.monotonic()
                        continue
                    player.terminate()
                elapsed_before_pause = 0.0
                paused_at = None
                started_at = time.monotonic()
                player = subprocess.Popen(["aplay", "--device", playback_device, str(full_preview)], text=True)
                continue
            elif answer == "u":
                if player is not None and player.poll() is None and paused_at is None:
                    elapsed_before_pause += time.monotonic() - started_at
                    paused_at = time.monotonic()
                    player.send_signal(signal.SIGSTOP)
                continue
            elif answer == "q":
                output_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                timer_stop.set()
                return 0
            else:
                try:
                    key, value = answer.split("=", 1)
                    if key not in labels:
                        raise ValueError("unsupported label key")
                    labels[key] = int(value)
                    print(f"current={labels}")
                except ValueError as error:
                    print(f"invalid command: {error}")
                continue
            accepted[fixture_id] = {"speech_intervals_ms": intervals, "internal_pause_interval_ms": pause, "review_status": "ACCEPTED_BY_LOCAL_REVIEW"}
            output_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            break
    timer_stop.set()
    print(f"accepted={len(accepted)} output={output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--playback-device")
    arguments = parser.parse_args(argv)
    return review(arguments.proposals, arguments.artifact_dir, arguments.output, arguments.playback_device)


if __name__ == "__main__":
    raise SystemExit(main())
