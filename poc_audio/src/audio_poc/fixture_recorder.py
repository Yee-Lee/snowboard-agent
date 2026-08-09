"""Controlled local recorder for the M1 authorized VAD/ASR fixture set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MANIFEST_NAME = "fixture_manifest.json"
SUMMARY_NAME = "fixture_summary.json"


@dataclass(frozen=True)
class CaptureItem:
    fixture_id: str
    vad_class: str
    category: str
    duration_seconds: int
    display_text: str | None = None
    reference_text: str | None = None


def load_plan(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    required = {"plan_id", "native_capture", "sets", "utterances"}
    missing = required - set(document)
    if missing:
        raise ValueError(f"recording plan missing keys: {', '.join(sorted(missing))}")
    if document.get("audio_git_tracked") is not False:
        raise ValueError("recording plan must keep raw audio outside Git")
    native = document["native_capture"]
    if native != {
        "sample_rate_hz": 48000,
        "channels": 2,
        "sample_format": "S32_LE",
        "access": "direct_hw",
    }:
        raise ValueError("recording plan does not use the reviewed native PCM format")
    return document


def build_capture_items(plan: dict[str, Any]) -> list[CaptureItem]:
    duration_by_class = {
        item["class"]: int(item["duration_seconds_each"]) for item in plan["sets"]
    }
    expected = {"clear_speech", "pause", "silence", "noise"}
    if set(duration_by_class) != expected:
        raise ValueError("recording plan must define all four VAD classes")

    items: list[CaptureItem] = []
    for utterance in plan["utterances"]:
        vad_class = str(utterance["vad_class"])
        if vad_class not in {"clear_speech", "pause"}:
            raise ValueError(f"invalid speech VAD class: {vad_class}")
        items.append(
            CaptureItem(
                fixture_id=str(utterance["fixture_id"]),
                vad_class=vad_class,
                category=str(utterance["category"]),
                duration_seconds=duration_by_class[vad_class],
                display_text=str(utterance["display_text"]),
                reference_text=str(utterance["reference_text"]),
            )
        )

    for vad_class in ("silence", "noise"):
        count = next(item["count"] for item in plan["sets"] if item["class"] == vad_class)
        for number in range(1, int(count) + 1):
            items.append(
                CaptureItem(
                    fixture_id=f"vad-{vad_class}-{number:03d}",
                    vad_class=vad_class,
                    category=vad_class,
                    duration_seconds=duration_by_class[vad_class],
                )
            )

    ids = [item.fixture_id for item in items]
    if len(items) != 100 or len(set(ids)) != len(ids):
        raise ValueError("recording plan must produce 100 uniquely identified fixtures")
    return items


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_metadata(path: Path) -> dict[str, int | float]:
    with wave.open(str(path), "rb") as source:
        frames = source.getnframes()
        rate = source.getframerate()
        return {
            "channels": source.getnchannels(),
            "sample_width_bytes": source.getsampwidth(),
            "sample_rate_hz": rate,
            "frames": frames,
            "duration_seconds": round(frames / rate, 3),
        }


def validate_wav(
    path: Path,
    native_capture: dict[str, Any],
    expected_duration_seconds: int | None = None,
) -> dict[str, int | float]:
    metadata = wav_metadata(path)
    expected = {
        "channels": native_capture["channels"],
        "sample_width_bytes": 4,
        "sample_rate_hz": native_capture["sample_rate_hz"],
    }
    for name, value in expected.items():
        if metadata[name] != value:
            raise ValueError(f"{path.name} has unexpected {name}: {metadata[name]}")
    if metadata["frames"] <= 0:
        raise ValueError(f"{path.name} contains no frames")
    if expected_duration_seconds is not None and abs(
        float(metadata["duration_seconds"]) - expected_duration_seconds
    ) > 0.1:
        raise ValueError(
            f"{path.name} has unexpected duration: {metadata['duration_seconds']}"
        )
    return metadata


def discover_voicehat_device(command: str) -> str:
    result = subprocess.run(
        [command, "-l"], check=True, text=True, capture_output=True
    )
    match = re.search(r"^card (\d+): .*googlevoicehat", result.stdout, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("no Google VoiceHAT ALSA card was found; pass --device explicitly")
    return f"hw:{match.group(1)},0"


def read_manifest(path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "1.0",
            "plan_id": plan["plan_id"],
            "plan_sha256": sha256_file(Path(plan["_path"])),
            "authorization_confirmed": True,
            "native_capture": plan["native_capture"],
            "records": {},
        }
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("plan_id") != plan["plan_id"]:
        raise ValueError("existing manifest belongs to another recording plan")
    if manifest.get("native_capture") != plan["native_capture"]:
        raise ValueError("existing manifest has a different native PCM format")
    return manifest


def write_json_atomically(path: Path, document: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def record_item(item: CaptureItem, output_dir: Path, device: str, native_capture: dict[str, Any]) -> dict[str, Any]:
    output_path = output_dir / f"{item.fixture_id}.wav"
    temporary = output_path.with_suffix(".wav.partial")
    if temporary.exists():
        temporary.unlink()
    command = [
        "arecord",
        "--device",
        device,
        "--file-type",
        "wav",
        "--rate",
        str(native_capture["sample_rate_hz"]),
        "--channels",
        str(native_capture["channels"]),
        "--format",
        str(native_capture["sample_format"]),
        "--duration",
        str(item.duration_seconds),
        str(temporary),
    ]
    try:
        subprocess.run(command, check=True)
        metadata = validate_wav(temporary, native_capture, item.duration_seconds)
        temporary.replace(output_path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return {
        "fixture_id": item.fixture_id,
        "vad_class": item.vad_class,
        "category": item.category,
        "file": output_path.name,
        "sha256": sha256_file(output_path),
        "metadata": metadata,
        "captured_at_utc": datetime.now(UTC).isoformat(),
    }


def verify_records(plan: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    manifest = read_manifest(manifest_path, plan)
    expected = {item.fixture_id: item for item in build_capture_items(plan)}
    records = manifest.get("records", {})
    valid = 0
    issues: list[str] = []
    counts = {name: 0 for name in ("clear_speech", "pause", "silence", "noise")}
    non_speech_seconds = 0
    for fixture_id, item in expected.items():
        record = records.get(fixture_id)
        if record is None:
            issues.append(f"missing:{fixture_id}")
            continue
        path = output_dir / str(record.get("file", ""))
        try:
            metadata = validate_wav(
                path, plan["native_capture"], item.duration_seconds
            )
            if record.get("sha256") != sha256_file(path):
                raise ValueError("checksum mismatch")
            if record.get("metadata") != metadata:
                raise ValueError("metadata mismatch")
            if record.get("vad_class") != item.vad_class:
                raise ValueError("VAD class mismatch")
        except (OSError, ValueError, wave.Error) as error:
            issues.append(f"invalid:{fixture_id}:{error}")
            continue
        valid += 1
        counts[item.vad_class] += 1
        if item.vad_class in {"silence", "noise"}:
            non_speech_seconds += item.duration_seconds

    summary = {
        "schema_version": "1.0",
        "plan_id": plan["plan_id"],
        "expected_files": len(expected),
        "valid_files": valid,
        "counts_by_vad_class": counts,
        "non_speech_seconds": non_speech_seconds,
        "result": "PASS" if not issues else "INCOMPLETE",
        "issue_count": len(issues),
    }
    write_json_atomically(output_dir / SUMMARY_NAME, summary)
    return {"summary": summary, "issues": issues}


def source_sha(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def prompt_for_item(item: CaptureItem) -> str:
    if item.vad_class == "clear_speech":
        return f"Read naturally: {item.display_text}"
    if item.vad_class == "pause":
        return f"Pause naturally at ｜: {item.display_text}"
    if item.vad_class == "silence":
        return "Remain silent; avoid speech, music, and private audio."
    return "Create stable ambient noise only; avoid speech, music, and private audio."


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("poc_audio/fixtures/authorized/recording_plan_v1.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1"))
    parser.add_argument("--device", help="direct ALSA capture device; defaults to detected VoiceHAT card")
    parser.add_argument("--list", action="store_true", help="list planned fixture IDs without recording")
    parser.add_argument("--verify", action="store_true", help="validate local WAV files and write a local summary")
    parser.add_argument("--record", metavar="FIXTURE_ID", help="record one fixture")
    parser.add_argument("--record-all", action="store_true", help="interactively record remaining fixtures")
    parser.add_argument("--replace", action="store_true", help="allow a completed fixture to be recorded again")
    parser.add_argument("--confirm-authorization", action="store_true", help="confirm the plan's internal-only recording authorization")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    actions = sum(bool(value) for value in (arguments.list, arguments.verify, arguments.record, arguments.record_all))
    if actions != 1:
        raise SystemExit("choose exactly one of --list, --verify, --record, or --record-all")
    plan_path = arguments.plan.resolve()
    plan = load_plan(plan_path)
    plan["_path"] = str(plan_path)
    items = build_capture_items(plan)
    items_by_id = {item.fixture_id: item for item in items}

    if arguments.list:
        for item in items:
            print(f"{item.fixture_id}\t{item.vad_class}\t{item.duration_seconds}s\t{item.category}")
        return 0
    if arguments.verify:
        outcome = verify_records(plan, arguments.output_dir)
        print(json.dumps(outcome["summary"], ensure_ascii=False, sort_keys=True))
        return 0 if not outcome["issues"] else 1

    if not arguments.confirm_authorization:
        raise SystemExit("recording requires --confirm-authorization; see fixtures/authorized/README.md")
    if shutil.which("arecord") is None:
        raise SystemExit("arecord is unavailable")
    device = arguments.device or discover_voicehat_device("arecord")
    output_dir = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    manifest = read_manifest(manifest_path, plan)
    manifest["source_sha"] = source_sha(plan_path.parents[3])
    manifest["capture_device"] = device
    records = manifest.setdefault("records", {})

    if arguments.record and arguments.record not in items_by_id:
        raise SystemExit(f"unknown fixture ID: {arguments.record}")
    requested = [items_by_id[arguments.record]] if arguments.record else items

    for item in requested:
        if item.fixture_id in records and not arguments.replace:
            print(f"skip completed: {item.fixture_id}")
            continue
        print(f"\n[{item.fixture_id}] {prompt_for_item(item)}")
        answer = input("Enter=record, s=skip, q=quit: ").strip().lower()
        if answer == "q":
            break
        if answer == "s":
            continue
        try:
            records[item.fixture_id] = record_item(item, output_dir, device, plan["native_capture"])
            write_json_atomically(manifest_path, manifest)
            print(f"recorded: {item.fixture_id}")
        except (OSError, subprocess.CalledProcessError, ValueError, wave.Error) as error:
            print(f"recording failed for {item.fixture_id}: {error}", file=sys.stderr)
            return 1

    outcome = verify_records(plan, output_dir)
    print(json.dumps(outcome["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
