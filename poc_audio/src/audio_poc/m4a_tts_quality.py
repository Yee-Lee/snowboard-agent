"""Generate the ten User-authorized high-risk Matcha review WAVs."""

from __future__ import annotations

import argparse
import array
import json
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .m4a_authorized_preflight import repo_root, verify_candidate_inputs
from .m4a_candidate_smoke import safe_extract
from .m4a_qualification_worker import _load_tts
from .m4a_runtime_preflight import assert_target, target_platform
from .m4a_tts_lifecycle import PROMPTS_SHA256, TTS_ID, sha256_file
from .validation import GIT_SHA_RE


QUALITY_IDS = (
    "tts-005", "tts-006", "tts-008", "tts-009", "tts-011",
    "tts-012", "tts-013", "tts-014", "tts-017", "tts-018",
)


def float_samples_to_s16le(samples: Iterable[float]) -> bytes:
    if sys.byteorder != "little":
        raise RuntimeError("quality WAV generator requires a little-endian target")
    pcm = array.array("h")
    for sample in samples:
        value = float(sample)
        if value <= -1.0:
            pcm.append(-32768)
        elif value >= 1.0:
            pcm.append(32767)
        else:
            pcm.append(round(value * 32767))
    return pcm.tobytes()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not GIT_SHA_RE.fullmatch(args.source_sha):
        raise ValueError("source SHA must be a full Git SHA")
    if args.work_dir.exists() or args.output_dir.exists():
        raise ValueError("work and output directories must be new paths")
    platform = target_platform()
    assert_target(platform)
    manifest = json.loads((repo_root() / "poc_audio/manifests/m4a_gate1b_candidates.json").read_text())
    verify_candidate_inputs(manifest, TTS_ID, args.artifact_dir)
    prompts_path = repo_root() / "poc_audio/fixtures/fake/tts_prompts.json"
    if sha256_file(prompts_path) != PROMPTS_SHA256:
        raise ValueError("tracked TTS prompt checksum mismatch")
    prompts = {
        item["fixture_id"]: item
        for item in json.loads(prompts_path.read_text(encoding="utf-8"))["prompts"]
    }
    if tuple(item for item in QUALITY_IDS if item not in prompts):
        raise ValueError("authorized quality prompt is absent")

    args.work_dir.mkdir(parents=True)
    args.output_dir.mkdir(parents=True)
    model = safe_extract(
        args.artifact_dir / "models/matcha-icefall-zh-en.tar.bz2",
        args.work_dir,
        "matcha-icefall-zh-en",
    )
    tts, load_ms = _load_tts(model, args.artifact_dir / "models/vocos-16khz-univ.onnx")
    records = []
    for index, fixture_id in enumerate(QUALITY_IDS, 1):
        prompt = prompts[fixture_id]
        audio = tts.generate(str(prompt["text"]), sid=0, speed=1.0)
        if audio.sample_rate != 16000 or not len(audio.samples):
            raise ValueError(f"invalid Matcha output: {fixture_id}")
        filename = f"sample-{index:02d}.wav"
        path = args.output_dir / filename
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(16000)
            target.writeframes(float_samples_to_s16le(audio.samples))
        records.append({
            "review_index": index,
            "fixture_id": fixture_id,
            "category": prompt["category"],
            "text": prompt["text"],
            "file": filename,
            "sha256": sha256_file(path),
            "sample_count": len(audio.samples),
            "duration_seconds": round(len(audio.samples) / 16000, 6),
            "score_1_to_5": None,
            "critical_misread": None,
            "note": "",
        })

    report = {
        "schema_version": "1.0",
        "report_id": "M4A-G1B-WP3-MATCHA-RISK-QUALITY",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "poc_source_sha": args.source_sha,
        "candidate_id": TTS_ID,
        "platform": platform,
        "prompts_sha256": PROMPTS_SHA256,
        "quality_ids": list(QUALITY_IDS),
        "load_ms": round(load_ms, 3),
        "pcm": {"sample_rate_hz": 16000, "channels": 1, "sample_format": "S16_LE"},
        "gate": {"median_score_gte": 4, "unrecorded_critical_misreads": 0},
        "records": records,
        "status": "READY_FOR_USER_REVIEW",
    }
    report_path = args.output_dir / "review.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Matcha quality packet: {report_path} ({report['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
