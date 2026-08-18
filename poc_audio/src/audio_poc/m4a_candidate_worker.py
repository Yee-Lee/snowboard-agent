"""One-shot real-candidate worker used only by the M2 isolated smoke packet."""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import time
import unicodedata
import wave
from pathlib import Path


def normalize_asr(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        char
        for char in normalized
        if char.isdecimal() or "a" <= char <= "z" or "\u3400" <= char <= "\u9fff"
    )


def edit_distance(reference: str, hypothesis: str) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def run_asr(args: argparse.Namespace) -> dict[str, object]:
    import sherpa_onnx

    started = time.monotonic()
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(args.model_dir / "model.int8.onnx"),
        tokens=str(args.model_dir / "tokens.txt"),
        num_threads=2,
        language="zh",
        use_itn=True,
        provider="cpu",
    )
    load_ms = (time.monotonic() - started) * 1000
    with wave.open(str(args.wav), "rb") as source:
        metadata = (source.getframerate(), source.getnchannels(), source.getsampwidth())
        frames = source.readframes(source.getnframes())
    if metadata != (16000, 1, 2):
        raise ValueError(f"unexpected ASR fixture PCM: {metadata}")
    pcm = array.array("h")
    pcm.frombytes(frames)
    samples = [value / 32768.0 for value in pcm]
    inference_started = time.monotonic()
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, samples)
    recognizer.decode_stream(stream)
    inference_ms = (time.monotonic() - inference_started) * 1000
    result = stream.result
    hypothesis = str(result.text if hasattr(result, "text") else result)
    reference = normalize_asr(args.reference)
    normalized_hypothesis = normalize_asr(hypothesis)
    edits = edit_distance(reference, normalized_hypothesis)
    return {
        "candidate_id": "asr-sherpa-sensevoice-int8-2025-09-09",
        "fixture_id": args.fixture_id,
        "load_ms": round(load_ms, 3),
        "inference_ms": round(inference_ms, 3),
        "audio_duration_seconds": len(samples) / 16000,
        "rtf": round(inference_ms / 1000 / (len(samples) / 16000), 6),
        "reference_length": len(reference),
        "hypothesis_length": len(normalized_hypothesis),
        "edit_distance": edits,
        "cer": round(edits / len(reference), 6),
        "sentence_correct": reference == normalized_hypothesis,
        "hypothesis_sha256": hashlib.sha256(hypothesis.encode("utf-8")).hexdigest(),
        "raw_transcript_emitted": False,
    }


def run_tts(args: argparse.Namespace) -> dict[str, object]:
    import sherpa_onnx

    rule_fsts = ",".join(
        str(args.model_dir / name)
        for name in ("phone-zh.fst", "date-zh.fst", "number-zh.fst")
    )
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=str(args.model_dir / "model-steps-3.onnx"),
                vocoder=str(args.vocos),
                lexicon=str(args.model_dir / "lexicon.txt"),
                tokens=str(args.model_dir / "tokens.txt"),
                data_dir=str(args.model_dir / "espeak-ng-data"),
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
    tts = sherpa_onnx.OfflineTts(config)
    load_ms = (time.monotonic() - started) * 1000
    inference_started = time.monotonic()
    audio = tts.generate(args.text, sid=0, speed=1.0)
    inference_ms = (time.monotonic() - inference_started) * 1000
    sample_count = len(audio.samples)
    if audio.sample_rate != 16000 or sample_count == 0:
        raise ValueError("Matcha returned invalid native PCM metadata")
    duration = sample_count / audio.sample_rate
    return {
        "candidate_id": "tts-sherpa-matcha-zh-en-1.13.5",
        "fixture_id": args.fixture_id,
        "load_ms": round(load_ms, 3),
        "inference_ms": round(inference_ms, 3),
        "sample_rate_hz": audio.sample_rate,
        "sample_count": sample_count,
        "channels": 1,
        "native_sample_representation": "float32_api_buffer",
        "audio_duration_seconds": round(duration, 6),
        "rtf": round(inference_ms / 1000 / duration, 6),
        "first_chunk_ms": None,
        "first_chunk_status": "PENDING_AUTHORIZED_CALLBACK_DEPENDENCY_REVIEW",
        "pcm_emitted": False,
        "audio_device_opened": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=("asr", "tts"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--vocos", type=Path)
    parser.add_argument("--wav", type=Path)
    parser.add_argument("--reference", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--fixture-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_asr(args) if args.domain == "asr" else run_tts(args)
    print("M4A_CANDIDATE_RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
