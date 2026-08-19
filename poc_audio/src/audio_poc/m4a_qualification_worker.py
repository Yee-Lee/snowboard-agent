"""Run one loaded authorized candidate over frozen M2 fixtures without playback."""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import resource
import time
import wave
from pathlib import Path
from typing import Any, Callable

from .m4a_candidate_worker import edit_distance, normalize_asr


def _rss_mib() -> float:
    status = Path("/proc/self/status")
    if status.is_file():
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 3)
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_asr(model_dir: Path) -> tuple[Any, float]:
    import sherpa_onnx

    started = time.monotonic()
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(model_dir / "model.int8.onnx"),
        tokens=str(model_dir / "tokens.txt"),
        num_threads=2,
        language="zh",
        use_itn=True,
        provider="cpu",
    )
    return recognizer, (time.monotonic() - started) * 1000


def _load_tts(model_dir: Path, vocos: Path) -> tuple[Any, float]:
    import sherpa_onnx

    rule_fsts = ",".join(
        str(model_dir / name)
        for name in ("phone-zh.fst", "date-zh.fst", "number-zh.fst")
    )
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=str(model_dir / "model-steps-3.onnx"),
                vocoder=str(vocos),
                lexicon=str(model_dir / "lexicon.txt"),
                tokens=str(model_dir / "tokens.txt"),
                data_dir=str(model_dir / "espeak-ng-data"),
            ),
            provider="cpu",
            num_threads=2,
        ),
        rule_fsts=rule_fsts,
        max_num_sentences=1,
    )
    if not config.validate():
        raise ValueError("Matcha configuration validation failed")
    started = time.monotonic()
    engine = sherpa_onnx.OfflineTts(config)
    return engine, (time.monotonic() - started) * 1000


def _asr_once(recognizer: Any, item: dict[str, Any], fixture_dir: Path) -> dict[str, Any]:
    fixture = fixture_dir / f"{item['fixture_id']}.wav"
    with wave.open(str(fixture), "rb") as source:
        metadata = (source.getframerate(), source.getnchannels(), source.getsampwidth())
        frames = source.readframes(source.getnframes())
    if metadata != (16000, 1, 2):
        raise ValueError(f"unexpected ASR fixture PCM: {item['fixture_id']}: {metadata}")
    pcm = array.array("h")
    pcm.frombytes(frames)
    samples = [value / 32768.0 for value in pcm]
    started = time.monotonic()
    cpu_started = time.process_time()
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, samples)
    recognizer.decode_stream(stream)
    cpu_ms = (time.process_time() - cpu_started) * 1000
    inference_ms = (time.monotonic() - started) * 1000
    result = stream.result
    hypothesis = str(result.text if hasattr(result, "text") else result)
    reference = normalize_asr(str(item["reference_text"]))
    normalized_hypothesis = normalize_asr(hypothesis)
    edits = edit_distance(reference, normalized_hypothesis)
    duration = len(samples) / 16000
    return {
        "fixture_id": item["fixture_id"],
        "category": item["category"],
        "latency_ms": round(inference_ms, 3),
        "cpu_ms": round(cpu_ms, 3),
        "audio_duration_seconds": round(duration, 6),
        "rtf": round(inference_ms / 1000 / duration, 6),
        "reference_length": len(reference),
        "hypothesis_length": len(normalized_hypothesis),
        "edit_distance": edits,
        "sentence_correct": reference == normalized_hypothesis,
        "hypothesis_sha256": _sha256_text(hypothesis),
        "raw_transcript_emitted": False,
    }


def _tts_once(tts: Any, item: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    cpu_started = time.process_time()
    audio = tts.generate(str(item["text"]), sid=0, speed=1.0)
    cpu_ms = (time.process_time() - cpu_started) * 1000
    inference_ms = (time.monotonic() - started) * 1000
    sample_count = len(audio.samples)
    if audio.sample_rate != 16000 or sample_count <= 0:
        raise ValueError(f"invalid Matcha output: {item['fixture_id']}")
    duration = sample_count / audio.sample_rate
    return {
        "fixture_id": item["fixture_id"],
        "category": item["category"],
        "latency_ms": round(inference_ms, 3),
        "first_chunk_ms": round(inference_ms, 3),
        "first_chunk_boundary": "synchronous_generate_returned_first_nonempty_buffer",
        "cpu_ms": round(cpu_ms, 3),
        "sample_rate_hz": audio.sample_rate,
        "sample_count": sample_count,
        "channels": 1,
        "native_sample_representation": "float32_api_buffer",
        "audio_duration_seconds": round(duration, 6),
        "rtf": round(inference_ms / 1000 / duration, 6),
        "pcm_emitted": False,
        "audio_device_opened": False,
    }


def run_suite(
    items: list[dict[str, Any]],
    infer: Callable[[dict[str, Any]], dict[str, Any]],
    cycles: int,
) -> tuple[list[dict[str, Any]], list[float]]:
    results: list[dict[str, Any]] = []
    rss_after_cycle: list[float] = []
    for cycle in range(1, cycles + 1):
        for item in items:
            result = infer(item)
            result["cycle"] = cycle
            results.append(result)
        rss_after_cycle.append(_rss_mib())
    return results, rss_after_cycle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=("asr", "tts"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--vocos", type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cycles", type=int, required=True)
    parser.add_argument("--warmups", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cycles <= 0 or args.warmups < 0:
        raise ValueError("cycles must be positive and warmups non-negative")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if args.domain == "asr":
        items = list(plan["utterances"])
        if len(items) != 50 or args.fixture_dir is None:
            raise ValueError("ASR qualification requires the frozen 50-item set")
        engine, load_ms = _load_asr(args.model_dir)
        infer = lambda item: _asr_once(engine, item, args.fixture_dir)
        candidate_id = "asr-sherpa-sensevoice-int8-2025-09-09"
    else:
        items = list(plan["prompts"])
        if len(items) != 20 or args.vocos is None:
            raise ValueError("TTS qualification requires the frozen 20-prompt set")
        engine, load_ms = _load_tts(args.model_dir, args.vocos)
        infer = lambda item: _tts_once(engine, item)
        candidate_id = "tts-sherpa-matcha-zh-en-1.13.5"

    for warmup in range(args.warmups):
        infer(items[warmup % len(items)])
    started = time.monotonic()
    cpu_started = time.process_time()
    results, rss_after_cycle = run_suite(items, infer, args.cycles)
    report = {
        "candidate_id": candidate_id,
        "domain": args.domain,
        "load_ms": round(load_ms, 3),
        "warmups": args.warmups,
        "cycles": args.cycles,
        "fixture_count": len(items),
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "cpu_ms": round((time.process_time() - cpu_started) * 1000, 3),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3),
        "rss_after_cycle_mib": rss_after_cycle,
        "results": results,
        "raw_transcript_emitted": False,
        "pcm_emitted": False,
        "audio_device_opened": False,
    }
    print("M4A_QUALIFICATION_RESULT=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
