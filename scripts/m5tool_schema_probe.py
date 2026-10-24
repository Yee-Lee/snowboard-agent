"""One-shot Pi diagnostic for M5.tool schema and first-turn prompt feasibility.

Run with the installed LiteRT-LM Python. This probe does not create product
evidence or replace the M5T-FLOW scenarios. Raw model output is private.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sbd.cognition.semantic import SemanticError, validate_m5_model_semantic
from sbd.cognition.prompt_builder import M5_SYSTEM_PROMPT


CASES = (
    ("answer", "你好，今天想聊什麼？"),
    ("end", "現在請結束對話。"),
    ("tool", "啟用遠端連線"),
    ("look", "幫我看一下前面有什麼東西？"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    args = parser.parse_args()
    if not args.private_output.parent.is_dir() or args.private_output.exists():
        parser.error("private output parent must exist and output must be new")
    sys.path.insert(0, str(args.runtime_root))
    from litert_lm import Backend, ConstrainedDecodingConfig, Engine, ResponseFormat, SamplerConfig
    from litert_lm._ffi import LiteRtLmConstraintProviderType

    schema = json.loads((ROOT / "requirements/m5tool/semantic-output-v1.schema.json").read_text())
    engine = Engine(str(args.model), backend=Backend.CPU(thread_count=4),
                    max_num_tokens=1024, enable_benchmark=True)
    constraint = ConstrainedDecodingConfig(enable=True,
        provider=LiteRtLmConstraintProviderType.LL_GUIDANCE)
    rows = []
    private_rows = []
    for case, utterance in CASES:
        conversation = None
        try:
            conversation = engine.create_conversation(system_message=M5_SYSTEM_PROMPT,
                automatic_tool_calling=False, constrained_decoding_config=constraint,
                sampler_config=SamplerConfig(temperature=0.0, top_p=1.0),
                max_output_tokens=128, filter_channel_content_from_kv_cache=False)
            rendered = conversation.render_message_to_string(utterance)
            prefill = len(engine.tokenize(rendered)) + (1 if conversation.token_count == 0 else 0)
            response = conversation.send_message(utterance, max_output_tokens=128,
                response_format=ResponseFormat.json(schema))
            raw = response["content"][0]["text"]
            try:
                semantic = validate_m5_model_semantic(raw)
                intent, valid = semantic.intent, True
            except SemanticError:
                intent, valid = "INVALID_SEMANTIC", False
            rows.append({"case": case, "runtime_prefill_tokens": prefill,
                         "first_turn_prefill_ok": prefill <= 128,
                         "semantic_valid": valid, "intent": intent})
            private_rows.append({"case": case, "utterance": utterance, "raw": raw,
                                 "rendered": rendered})
        except Exception as exc:
            rows.append({"case": case, "native_error": type(exc).__name__})
            private_rows.append({"case": case, "utterance": utterance,
                                 "native_error": repr(exc)})
        finally:
            if conversation is not None:
                conversation.close()
    engine.close()
    descriptor = os.open(args.private_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(private_rows, ensure_ascii=False) + "\n").encode())
    finally:
        os.close(descriptor)
    print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
