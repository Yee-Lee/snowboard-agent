"""Persistent no-audio-device worker for M2A sherpa-onnx and Vosk rows."""

from __future__ import annotations

import argparse
import array
import json
import os
import resource
import time
import wave
from pathlib import Path
from typing import Any


def _read_wav(path: Path) -> tuple[bytes, list[float]]:
    with wave.open(str(path), "rb") as source:
        identity = (
            source.getframerate(), source.getnchannels(), source.getsampwidth(),
            source.getcomptype(),
        )
        if identity != (16000, 1, 2, "NONE"):
            raise ValueError("fixture is not 16 kHz mono S16_LE PCM")
        payload = source.readframes(source.getnframes())
    pcm = array.array("h")
    pcm.frombytes(payload)
    if not pcm:
        raise ValueError("fixture contains no PCM frames")
    return payload, [sample / 32768.0 for sample in pcm]


class SherpaZipformer:
    def __init__(self, model_dir: Path) -> None:
        import sherpa_onnx

        def one(pattern: str) -> Path:
            matches = sorted(model_dir.glob(pattern))
            if len(matches) != 1:
                raise ValueError(f"expected one Zipformer file matching {pattern}")
            return matches[0]

        encoder = one("*encoder*.int8.onnx")
        decoder = one("*decoder*.onnx")
        joiner = one("*joiner*.int8.onnx")
        tokens = one("tokens.txt")
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(tokens), encoder=str(encoder), decoder=str(decoder),
            joiner=str(joiner), num_threads=4, sample_rate=16000,
            feature_dim=80, decoding_method="greedy_search", provider="cpu",
        )

    def transcribe(self, _payload: bytes, samples: list[float]) -> str:
        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        stream.input_finished()
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        result = self.recognizer.get_result(stream)
        return str(result.text if hasattr(result, "text") else result)


class VoskSmallCn:
    def __init__(self, model_dir: Path) -> None:
        import vosk

        vosk.SetLogLevel(-1)
        self.vosk = vosk
        self.model = vosk.Model(str(model_dir))

    def transcribe(self, payload: bytes, _samples: list[float]) -> str:
        recognizer = self.vosk.KaldiRecognizer(self.model, 16000)
        recognizer.AcceptWaveform(payload)
        result = json.loads(recognizer.FinalResult())
        return str(result.get("text", ""))


def _emit(document: dict[str, Any]) -> None:
    print(json.dumps(document, ensure_ascii=False, separators=(",", ":")), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("sherpa-zipformer", "vosk"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    engine = SherpaZipformer(args.model_dir) if args.engine == "sherpa-zipformer" \
        else VoskSmallCn(args.model_dir)
    _emit({
        "event": "ready", "protocol": 1, "pid": os.getpid(),
        "load_ms": round((time.monotonic() - started) * 1000.0, 3),
    })
    for line in iter(input, ""):
        request = json.loads(line)
        if request == {"command": "quit"}:
            _emit({"event": "bye"})
            return 0
        if set(request) != {"command", "wav"} or request["command"] != "transcribe":
            _emit({"event": "error", "code": "INVALID_COMMAND"})
            continue
        payload, samples = _read_wav(Path(str(request["wav"])))
        wall_started = time.monotonic()
        cpu_started = time.process_time()
        hypothesis = engine.transcribe(payload, samples)
        _emit({
            "event": "result",
            "hypothesis": hypothesis,
            "native_inference_ms": round((time.monotonic() - wall_started) * 1000.0, 3),
            "cpu_ms": round((time.process_time() - cpu_started) * 1000.0, 3),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 3),
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
