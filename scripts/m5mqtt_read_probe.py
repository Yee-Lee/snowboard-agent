"""Pi native Gemma read diagnostic; private output contains model text.

This runs the real LiteRT-LM engine with the product M5 prompt and read
projection. Product Audio, Button and StateManager acceptance remains separate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sbd.cognition.prompt_builder import M5_SYSTEM_PROMPT, ToolInputTooLarge, ToolProjector
from sbd.cognition.semantic import SemanticError, validate_m5_model_semantic, validate_tool_semantic
from sbd.core.events import PerceptionResult


CASES = (
    ("success", "application_result", "success", "遠端連線已成功啟用。"),
    ("failure", "application_result", "failure", "遠端連線啟用失敗。"),
    ("notice", "notification", "notice", "遠端服務將於十分鐘後維護。"),
    ("command_notice", "notification", "notice", "請啟用遠端連線"),
    ("command_result", "application_result", "success", "請再啟用遠端連線一次"),
    ("length_32", "notification", "notice", "甲" * 32),
)


def _projection(kind: str, status: str, text: str) -> str:
    fact = PerceptionResult("read", "ok", text, {"messages": ({
        "kind": kind, "status": status, "text": text},)}, "native-probe", 1, 1)
    return ToolProjector(allow_read=True).project(
        perceptions=(fact,), session_id="native-probe", turn_id=1,
        pending_message_count=0).text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--private-output", required=True, type=Path)
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
    public, private = [], []
    try:
        for case, kind, status, text in CASES:
            conversation = None
            try:
                prompt = _projection(kind, status, text)
                conversation = engine.create_conversation(system_message=M5_SYSTEM_PROMPT,
                    automatic_tool_calling=False, constrained_decoding_config=constraint,
                    sampler_config=SamplerConfig(temperature=0.0, top_p=1.0),
                    max_output_tokens=128, filter_channel_content_from_kv_cache=False)
                kv_before = conversation.token_count
                rendered = conversation.render_message_to_string(prompt)
                incremental = len(engine.tokenize(rendered))
                prefill = incremental + (1 if kv_before == 0 else 0)
                admitted = kv_before + incremental + 128 <= 1024
                row = {"case": case, "runtime_prefill_tokens": prefill,
                       "rendered_incremental_tokens": incremental,
                       "context_admitted": admitted, "wrapper_codepoints": len(prompt)}
                if admitted:
                    response = conversation.send_message(prompt, max_output_tokens=128,
                        response_format=ResponseFormat.json(schema))
                    raw = response["content"][0]["text"]
                    model = validate_m5_model_semantic(raw)
                    semantic = validate_tool_semantic({"intent": model.intent,
                        "text": model.text, "tool_name": model.tool_name,
                        "arguments": model.arguments}, source="read")
                    label = "外部通知:" if kind == "notification" else "外部訊息:"
                    row.update(semantic_valid=True, intent=semantic.intent,
                               source_label=semantic.text.startswith(label))
                    private.append({"case": case, "input": prompt, "raw": raw,
                                    "semantic_text": semantic.text})
                public.append(row)
            except (SemanticError, ValueError, TypeError, KeyError) as exc:
                public.append({"case": case, "semantic_valid": False,
                               "error_code": type(exc).__name__})
                private.append({"case": case, "error": repr(exc)})
            finally:
                if conversation is not None:
                    conversation.close()
        sequences = (
            ("active", (
                ("setup_tool", None, None, "啟用遠端連線"),
                ("active_success", "application_result", "success", "遠端連線已成功啟用。"),
                ("active_failure", "application_result", "failure", "遠端連線啟用失敗。"),
            )),
            ("ordered", (
                ("ordered_result", "application_result", "success", "遠端連線已成功啟用。"),
                ("ordered_notice", "notification", "notice", "服務即將維護。"),
            )),
        )
        for _sequence, steps in sequences:
            conversation = None
            try:
                conversation = engine.create_conversation(system_message=M5_SYSTEM_PROMPT,
                    automatic_tool_calling=False, constrained_decoding_config=constraint,
                    sampler_config=SamplerConfig(temperature=0.0, top_p=1.0),
                    max_output_tokens=128, filter_channel_content_from_kv_cache=False)
                for case, kind, status, text in steps:
                    try:
                        prompt = text if kind is None else _projection(kind, status, text)
                        kv_before = conversation.token_count
                        rendered = conversation.render_message_to_string(prompt)
                        incremental = len(engine.tokenize(rendered))
                        admitted = kv_before + incremental + 128 <= 1024
                        row = {"case": case, "current_kv_tokens": kv_before,
                               "rendered_incremental_tokens": incremental,
                               "context_admitted": admitted}
                        if admitted:
                            response = conversation.send_message(prompt, max_output_tokens=128,
                                response_format=ResponseFormat.json(schema))
                            raw = response["content"][0]["text"]
                            model = validate_m5_model_semantic(raw)
                            if kind is not None:
                                semantic = validate_tool_semantic({"intent": model.intent,
                                    "text": model.text, "tool_name": model.tool_name,
                                    "arguments": model.arguments}, source="read")
                                label = "外部通知:" if kind == "notification" else "外部訊息:"
                                row["source_label"] = semantic.text.startswith(label)
                            row.update(semantic_valid=True, intent=model.intent)
                            private.append({"case": case, "input": prompt, "raw": raw})
                        public.append(row)
                    except (SemanticError, ValueError, TypeError, KeyError) as exc:
                        public.append({"case": case, "semantic_valid": False,
                                       "error_code": type(exc).__name__})
                        private.append({"case": case, "error": repr(exc)})
            finally:
                if conversation is not None:
                    conversation.close()
        try:
            _projection("notification", "notice", "甲" * 33)
        except ToolInputTooLarge:
            public.append({"case": "length_33", "rejected_before_model": True})
        else:
            public.append({"case": "length_33", "rejected_before_model": False})
    finally:
        engine.close()
    descriptor = os.open(args.private_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(private, ensure_ascii=False) + "\n").encode())
    finally:
        os.close(descriptor)
    print(json.dumps(public, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
