"""Run the v0.3 SSD1351 evidence contract on a Raspberry Pi fixture."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from sbd.core.display.hal.factory import create_device


WIDTH = 128
HEIGHT = 128
FRAME_BYTES = WIDTH * HEIGHT * 2
REPO_ROOT = Path(__file__).resolve().parents[2]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.stdout.strip() or "UNKNOWN"


def git_is_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return bool(result.stdout.strip())


def solid(pixel: bytes) -> bytes:
    return pixel * (WIDTH * HEIGHT)


def gradient() -> bytes:
    frame = bytearray(FRAME_BYTES)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            red = x * 31 // (WIDTH - 1)
            green = y * 63 // (HEIGHT - 1)
            blue = (x + y) * 31 // (WIDTH + HEIGHT - 2)
            pixel = (red << 11) | (green << 5) | blue
            offset = (y * WIDTH + x) * 2
            frame[offset] = pixel >> 8
            frame[offset + 1] = pixel & 0xFF
    return bytes(frame)


async def missing_device_is_rejected(args: argparse.Namespace) -> bool:
    data = json.loads(Path(args.config).read_text(encoding="utf-8"))
    data["spi"]["device"] = "/dev/spidev99.0"
    data["spi"]["bus"] = 99
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="poc-display-invalid-",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as temporary:
            json.dump(data, temporary)
            temporary_path = Path(temporary.name)
        device = create_device(
            "waveshare_oled_1in5_rgb",
            so_path=args.so,
            config_path=temporary_path,
        )
        try:
            await device.start()
        except (OSError, RuntimeError, ValueError):
            await device.stop()
            return True
        await device.stop()
        return False
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


async def exercise(args: argparse.Namespace) -> dict[str, object]:
    device = create_device(
        "waveshare_oled_1in5_rgb",
        so_path=args.so,
        config_path=args.config,
    )
    await device.start()
    try:
        wrong_length_rejected = False
        try:
            device.write_pixels(bytes(FRAME_BYTES - 2))
        except ValueError:
            wrong_length_rejected = True
        if not wrong_length_rejected:
            raise RuntimeError("wrong-length frame was not rejected")

        patterns = {
            "black": solid(b"\x00\x00"),
            "white": solid(b"\xff\xff"),
            "red": solid(b"\xf8\x00"),
            "green": solid(b"\x07\xe0"),
            "blue": solid(b"\x00\x1f"),
            "gradient": gradient(),
        }
        pattern_results = []
        for name, frame in patterns.items():
            device.write_pixels(frame)
            device.show()
            pattern_results.append({"name": name, "status": "presented"})
            time.sleep(args.observe_seconds)

        device.clear()
        device.show()

        measure_frame = patterns["gradient"]
        device.write_pixels(measure_frame)
        for _ in range(args.warmup):
            device.show()

        samples_ms = []
        for _ in range(args.samples):
            started = time.perf_counter_ns()
            device.show()
            samples_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    finally:
        await device.stop()
        await device.stop()

    reopen_passes = 0
    for _ in range(3):
        await device.start()
        await device.stop()
        reopen_passes += 1

    missing_device_rejected = await missing_device_is_rejected(args)
    if not missing_device_rejected:
        raise RuntimeError("missing SPI device config was not rejected")

    return {
        "sample_count": len(samples_ms),
        "warmup_count": args.warmup,
        "measurement_boundary": "immediately before adapter show() to native present return",
        "resolution": [WIDTH, HEIGHT],
        "pixel_format": "RGB565_MSB_FIRST",
        "requested_speed_hz": json.loads(Path(args.config).read_text())["spi"]["requested_speed_hz"],
        "effective_speed_hz": None,
        "p50_ms": statistics.median(samples_ms),
        "p95_ms": percentile(samples_ms, 0.95),
        "max_ms": max(samples_ms),
        "patterns": pattern_results,
        "wrong_length_rejected": True,
        "repeated_stop_passed": True,
        "reopen_passes": f"{reopen_passes}/3",
        "missing_device_rejected": missing_device_rejected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--so", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--observe-seconds", type=float, default=1.0)
    args = parser.parse_args()
    if args.warmup < 0 or args.samples < 1:
        parser.error("warmup must be >= 0 and samples must be >= 1")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    config_bytes = Path(args.config).read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    shutil.copyfile(args.config, output / "config.json")
    (output / "config.sha256").write_text(f"{config_hash}  config.json\n")

    results = asyncio.run(exercise(args))
    results["config_sha256"] = config_hash
    results["source_sha"] = git_value("rev-parse", "HEAD")
    results["source_dirty"] = git_is_dirty()
    (output / "latency.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    environment = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "kernel": platform.release(),
        "source_sha": results["source_sha"],
        "source_dirty": results["source_dirty"],
    }
    (output / "environment.txt").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"evidence written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
