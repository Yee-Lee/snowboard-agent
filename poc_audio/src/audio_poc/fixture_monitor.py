"""Create a local dual-mono monitoring copy without modifying fixture audio."""

from __future__ import annotations

import argparse
import array
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from .fixture_recorder import discover_voicehat_device, sha256_file, validate_wav


def duplicate_channel_to_stereo(
    source: Path, destination: Path, channel: int, gain_db: float = 0.0
) -> dict[str, int | float]:
    """Write a clipped-safe dual-mono copy of one S32_LE source channel."""
    if not -24.0 <= gain_db <= 24.0:
        raise ValueError("gain_db must be between -24 and 24")
    with wave.open(str(source), "rb") as input_wav:
        channels = input_wav.getnchannels()
        width = input_wav.getsampwidth()
        rate = input_wav.getframerate()
        frames = input_wav.getnframes()
        if channels != 2 or width != 4 or rate != 48000:
            raise ValueError("source must be native 48 kHz stereo S32_LE WAV")
        if channel < 0 or channel >= channels:
            raise ValueError("requested source channel is unavailable")
        payload = input_wav.readframes(frames)

    values = array.array("i")
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    dual_mono = array.array("i")
    gain = 10 ** (gain_db / 20)
    clipped_source_samples = 0
    for offset in range(channel, len(values), channels):
        sample = round(values[offset] * gain)
        if sample > 2147483647:
            sample = 2147483647
            clipped_source_samples += 1
        elif sample < -2147483648:
            sample = -2147483648
            clipped_source_samples += 1
        dual_mono.extend((sample, sample))
    if sys.byteorder != "little":
        dual_mono.byteswap()

    temporary = destination.with_suffix(destination.suffix + ".partial")
    if temporary.exists():
        temporary.unlink()
    try:
        with wave.open(str(temporary), "wb") as output_wav:
            output_wav.setnchannels(2)
            output_wav.setsampwidth(4)
            output_wav.setframerate(48000)
            output_wav.writeframes(dual_mono.tobytes())
        temporary.replace(destination)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    metadata = validate_wav(
        destination,
        {"sample_rate_hz": 48000, "channels": 2, "sample_format": "S32_LE", "access": "direct_hw"},
    )
    metadata["gain_db"] = gain_db
    metadata["clipped_source_samples"] = clipped_source_samples
    return metadata


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_id", help="authorized fixture ID to monitor")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1"),
    )
    parser.add_argument("--source-channel", type=int, default=0)
    parser.add_argument("--gain-db", type=float, default=0.0, help="temporary monitoring gain, limited to -24 through +24 dB")
    parser.add_argument("--replace", action="store_true", help="replace an existing derived monitor WAV")
    parser.add_argument("--play", action="store_true", help="play the derived monitor WAV through the detected VoiceHAT output")
    parser.add_argument("--playback-device", help="direct ALSA output device; defaults to detected VoiceHAT card")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    if not arguments.fixture_id.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("fixture_id contains unsupported characters")
    source = arguments.artifact_dir / f"{arguments.fixture_id}.wav"
    if not source.is_file():
        raise SystemExit("authorized source WAV is unavailable")
    monitor_dir = arguments.artifact_dir / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    gain_suffix = "" if arguments.gain_db == 0 else f"-gain{arguments.gain_db:+g}dB"
    destination = monitor_dir / f"{arguments.fixture_id}-ch{arguments.source_channel}-dual{gain_suffix}.wav"
    if destination.exists() and not arguments.replace:
        raise SystemExit("derived monitor WAV already exists; pass --replace to recreate it")

    metadata = duplicate_channel_to_stereo(
        source, destination, arguments.source_channel, arguments.gain_db
    )
    summary = {
        "fixture_id": arguments.fixture_id,
        "source_channel": arguments.source_channel,
        "transform": "dual_mono_with_saturating_gain",
        "gain_db": arguments.gain_db,
        "clipped_source_samples": metadata["clipped_source_samples"],
        "derived_sha256": sha256_file(destination),
        "metadata": metadata,
        "played": arguments.play,
    }
    print(json.dumps(summary, sort_keys=True))

    if arguments.play:
        if shutil.which("aplay") is None:
            raise SystemExit("aplay is unavailable")
        device = arguments.playback_device or discover_voicehat_device("aplay")
        subprocess.run(["aplay", "--device", device, str(destination)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
