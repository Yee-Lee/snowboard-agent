"""Interactive local review for energy-assisted VAD label proposals."""

from __future__ import annotations

import argparse
import array
import json
import math
import shutil
import subprocess
import sys
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
    for proposal in document["proposals"]:
        fixture_id = proposal["fixture_id"]
        if fixture_id in accepted:
            continue
        source = artifact_dir / f"{fixture_id}.wav"
        print(f"\n{fixture_id} ({proposal['class']}, {proposal['category']})")
        print(f"suggested speech={proposal['speech_intervals_ms']} pause={proposal.get('internal_pause_candidate_ms')}")
        while True:
            for label, start, end in _preview_ranges(proposal):
                preview = preview_dir / f"{fixture_id}-{label}.wav"
                gain_db = _write_preview(source, preview, start, end)
                print(f"playing {label}: {start}..{end} ms (preview gain {gain_db:+.2f} dB)")
                subprocess.run(["aplay", "--device", playback_device, str(preview)], check=True)
            answer = input("Enter=accept, r=replay, q=quit, or override times: ").strip().lower()
            if not answer:
                intervals, pause = proposal["speech_intervals_ms"], proposal.get("internal_pause_candidate_ms")
            elif answer == "r":
                continue
            elif answer == "q":
                output_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return 0
            else:
                try:
                    intervals, pause = _parse_override(answer, proposal)
                except ValueError as error:
                    print(error)
                    continue
            accepted[fixture_id] = {"speech_intervals_ms": intervals, "internal_pause_interval_ms": pause, "review_status": "ACCEPTED_BY_LOCAL_REVIEW"}
            output_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            break
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
