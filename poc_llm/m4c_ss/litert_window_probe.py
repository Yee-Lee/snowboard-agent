"""Sanitized one-shot probe for the real LiteRT pre-terminal S2 window."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

from poc_llm.efficiency.raw_stream import send_message_raw
from poc_llm.harness.mva_contract import render_user_turn, validate_semantic as validate_mva
from poc_llm.harness.mva_product_layout import cache_object_path, runtime_model_path
from poc_llm.m4c_ss.incremental_s2 import IncrementalS2
from poc_llm.m4c_ss.s2 import S2Error, validate_semantic


ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "poc_llm/contracts/mva/mva-profile-001.json").read_text())
CONTRACT = ROOT / "poc_llm/contracts/mva"
RELEASE_BOUNDARIES = (8, 12, 16, 24)
RUN_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")


class PrivateChunkJournal:
    def __init__(self, path: Path) -> None:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.path = path
        self.output = os.fdopen(descriptor, "w", encoding="utf-8")
        self.bytes = 0
        self.sha256 = ""

    def append(self, *, offset_ns: int, text: str, is_final: bool) -> None:
        self.output.write(json.dumps({
            "offset_ns": offset_ns,
            "text": text,
            "is_final": is_final,
        }, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.output.flush()

    def close(self) -> None:
        if self.output.closed:
            return
        self.output.flush()
        os.fsync(self.output.fileno())
        self.output.close()
        payload = self.path.read_bytes()
        self.bytes = len(payload)
        self.sha256 = hashlib.sha256(payload).hexdigest()



def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_probe(
    *, config_path: Path, private_root: Path, public_text: str, run_id: str,
) -> dict[str, object]:
    import litert_lm

    config = json.loads(config_path.read_text(encoding="utf-8"))
    runtime_root = Path(config["runtime_root"]).resolve()
    if not Path(litert_lm.__file__).resolve().is_relative_to(runtime_root):
        raise RuntimeError("RUNTIME_IMPORT_DRIFT")
    mem_kib = next(
        int(line.split()[1])
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    if mem_kib < 512 * 1024:
        raise RuntimeError("RESOURCE_STOP")

    inference = PROFILE["inference"]
    sampler = litert_lm.SamplerConfig(
        temperature=inference["temperature"], top_p=inference["top_p"]
    )
    system_message = (CONTRACT / "system-prompt-v1.txt").read_text(encoding="utf-8")
    user_template = (CONTRACT / "user-turn-template-v1.txt").read_text(encoding="utf-8")
    schema = json.loads((CONTRACT / "semantic-output-v1.schema.json").read_text())
    private_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if RUN_ID.fullmatch(run_id) is None:
        raise ValueError("RUN_ID_INVALID")
    run_root = private_root / run_id
    run_root.mkdir(mode=0o700, exist_ok=False)
    journal = PrivateChunkJournal(run_root / "raw-stream.jsonl")

    engine = None
    conversation = None
    with tempfile.TemporaryDirectory(prefix="litert-window-", dir=private_root) as directory:
        try:
            engine_started = time.monotonic_ns()
            engine = litert_lm.Engine(
                str(runtime_model_path(config, directory)),
                backend=litert_lm.Backend.CPU(thread_count=4),
                cache_dir=str(cache_object_path(config)),
                enable_benchmark=True,
                max_num_tokens=inference["engine_kv_tokens"],
            )
            engine_ready = time.monotonic_ns()
            conversation = engine.create_conversation(
                system_message=system_message,
                sampler_config=sampler,
                max_output_tokens=inference["maximum_output_tokens"],
                automatic_tool_calling=False,
                constrained_decoding_config=litert_lm.ConstrainedDecodingConfig(
                    enable=True,
                    provider=litert_lm.LiteRtLmConstraintProviderType.LL_GUIDANCE,
                ),
            )
            prompt = render_user_turn(user_template, public_text)
            response_format = litert_lm.ResponseFormat.json(schema)
            sent = time.monotonic_ns()
            incrementals = {
                boundary: IncrementalS2(max_codepoints=boundary)
                for boundary in RELEASE_BOUNDARIES
            }
            fragment_events: dict[int, list[dict[str, object]]] = {
                boundary: [] for boundary in RELEASE_BOUNDARIES
            }
            wire = ""
            chunk_count = 0
            nonempty_count = 0
            first_chunk_ns = None
            valid_ns = None
            valid_terminal = None
            final_ns = None
            for chunk in send_message_raw(conversation, prompt, response_format=response_format):
                now = time.monotonic_ns()
                journal.append(
                    offset_ns=now - sent, text=chunk.text, is_final=chunk.is_final,
                )
                chunk_count += 1
                if chunk.is_final:
                    final_ns = now
                    continue
                if chunk.text:
                    nonempty_count += 1
                    first_chunk_ns = first_chunk_ns or now
                    wire += chunk.text
                for boundary, incremental in incrementals.items():
                    for fragment in incremental.feed(wire):
                        fragment_events[boundary].append({
                            "offset_ms": (now - sent) / 1_000_000,
                            "codepoints": len(fragment),
                            "sha256": _sha256(fragment),
                        })
                if valid_ns is None:
                    try:
                        candidate = validate_semantic(wire)
                        validate_mva(json.loads(wire))
                    except (S2Error, json.JSONDecodeError, ValueError, TypeError):
                        continue
                    valid_ns = now
                    valid_terminal = candidate
                    for boundary, incremental in incrementals.items():
                        for fragment in incremental.flush(candidate.text):
                            fragment_events[boundary].append({
                                "offset_ms": (now - sent) / 1_000_000,
                                "codepoints": len(fragment),
                                "sha256": _sha256(fragment),
                            })
            journal.close()
            if final_ns is None:
                raise RuntimeError("MISSING_NATIVE_FINAL")
            terminal = validate_semantic(wire)
            validate_mva(json.loads(wire))
            if (
                valid_terminal != terminal
                or any(
                    incremental.released != terminal.text
                    for incremental in incrementals.values()
                )
            ):
                raise RuntimeError("TERMINAL_REVISION")
            release_results: dict[str, object] = {}
            for boundary in RELEASE_BOUNDARIES:
                events = fragment_events[boundary]
                first_ms = events[0]["offset_ms"] if events else None
                release_results[str(boundary)] = {
                    "first_safe_text_ms": first_ms,
                    "lead_to_native_final_ms": (
                        None if first_ms is None
                        else (final_ns - sent) / 1_000_000 - float(first_ms)
                    ),
                    "fragment_count": len(events),
                    "fragments": events,
                }
            baseline = release_results["24"]
            benchmark = conversation.get_benchmark_info()
            return {
                "status": "ENGINEERING_OBSERVATION_NOT_FORMAL",
                "public_input_sha256": _sha256(public_text),
                "engine_ready_ms": (engine_ready - engine_started) / 1_000_000,
                "first_chunk_ms": None if first_chunk_ns is None else (first_chunk_ns - sent) / 1_000_000,
                "first_valid_s2_ms": None if valid_ns is None else (valid_ns - sent) / 1_000_000,
                "native_final_ms": (final_ns - sent) / 1_000_000,
                "usable_preterminal_window_ms": None if valid_ns is None else (final_ns - valid_ns) / 1_000_000,
                "native_ttft_ms": benchmark.time_to_first_token_in_second * 1000,
                "chunk_count": chunk_count,
                "nonempty_chunk_count": nonempty_count,
                "safe_fragment_count": baseline["fragment_count"],
                "safe_fragments": baseline["fragments"],
                "release_boundaries": release_results,
                "terminal_text_sha256": terminal.text_sha256,
                "terminal_codepoints": terminal.normalized_codepoints,
                "terminal_end": terminal.end,
                "wire_sha256": _sha256(wire),
                "raw_text_retained": True,
                "private_bundle": {
                    "run_id": run_id,
                    "bytes": journal.bytes,
                    "sha256": journal.sha256,
                },
            }
        finally:
            journal.close()
            if conversation is not None:
                conversation.close()
            if engine is not None:
                engine.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--public-text", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = run_probe(
            config_path=args.config,
            private_root=args.private_root,
            public_text=args.public_text,
            run_id=args.run_id,
        )
    except BaseException as error:
        print(json.dumps({"status": "ENGINEERING_ERROR_NOT_FORMAL", "code": type(error).__name__}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
