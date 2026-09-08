"""Run the bounded, non-formal prompt candidate screen on the selected Pi runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from poc_llm.efficiency.backend import EfficiencyLiteRtBackend
from poc_llm.efficiency.prompt import compose_system_prompt
from poc_llm.harness.mva_contract import SESSION_FACTS
from poc_llm.harness.mva_identity import load_config
from poc_llm.harness.mva_litert_backend import MvaBackendError
from poc_llm.harness.mva_product_layout import cache_object_path, runtime_model_path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "poc_llm/contracts/mva"
CANDIDATES = {
    "V1": ROOT / "poc_llm/contracts/mva/system-prompt-v1.txt",
    "V2A": ROOT / "poc_llm/contracts/efficiency/system-prompt-v2a-core.txt",
    "V2B": ROOT / "poc_llm/contracts/efficiency/system-prompt-v2b-core.txt",
    "V2C": ROOT / "poc_llm/contracts/efficiency/system-prompt-v2c-core.txt",
}
SETTINGS = "溫暖自然，稍帶幽默。"
NEGATIVE_MARKERS = ("不能", "無法", "看不到", "沒有")
SCREEN_CASES = (
    ("identity", "你是誰？", "identity"),
    ("basic", "天空為什麼是藍色的？", "answer"),
    ("cannot_see", "你看得到我嗎？", "negative"),
    ("cannot_tool", "你可以使用工具嗎？", "negative"),
    ("explicit_end", "不用了，結束對話。", "end"),
    ("negative_end", "不要結束，再說簡單一點。", "answer"),
)
TIMING_PAIR = ("你好？", "請用一句話說明天空為什麼看起來是藍色的？")


def _turn(text: str) -> dict[str, object]:
    return {"perceptions": [{"kind": "listen", "status": "ok", "text": text}]}


def _passes(expectation: str, semantic: dict[str, object]) -> bool:
    text = semantic["text"]
    end = semantic["end"]
    if expectation == "end":
        return end is True and text == ""
    if end is not False or not isinstance(text, str) or not text.strip():
        return False
    if expectation == "identity":
        return "雪板" in text
    if expectation == "negative":
        return any(marker in text for marker in NEGATIVE_MARKERS)
    return True


def _metrics(
    generation, *, case_id: str, passed: bool, include_public_answer: bool,
) -> dict[str, object]:
    semantic = generation.generation.semantic
    values = generation.generation.metrics
    result = {
        "case_id": case_id,
        "pass": passed,
        "end": semantic["end"],
        "answer_codepoints": len(semantic["text"]),
        "new_user_tokens": values["new_user_tokens"],
        "rendered_tokens": values["rendered_tokens"],
        "runtime_prefill_tokens": values["incremental_tokens"],
        "output_tokens": values["output_tokens"],
        "kv_tokens": values["kv_tokens"],
        "first_decodable_text_ms": values["first_decodable_text_ms"],
        "first_safe_chunk_ms": values["first_chunk_ms"],
        "terminal_ms": values["ttc_ms"],
    }
    if include_public_answer:
        result["public_answer"] = semantic["text"]
    return result


def _one(
    backend, session: str, text: str, expectation: str, *, include_public_answer: bool,
) -> dict[str, object]:
    backend.open_session(session, SESSION_FACTS)
    provisional: list[str] = []
    try:
        try:
            result = backend.generate_turn(
                session,
                1,
                SESSION_FACTS,
                _turn(text),
                on_provisional_text=provisional.append,
            )
        except MvaBackendError as error:
            failed = {
                "case_id": session,
                "pass": False,
                "terminal": error.code,
                "detail_code": getattr(error, "detail_code", None),
                **getattr(error, "diagnostic_metrics", {}),
            }
            if include_public_answer:
                failed["provisional_public_answer"] = "".join(provisional)
            return failed
        action_ok = (
            result.action["action_kind"] == ("rest" if expectation == "end" else "speak")
        )
        return _metrics(
            result,
            case_id=session,
            passed=_passes(expectation, result.generation.semantic) and action_ok,
            include_public_answer=include_public_answer,
        )
    finally:
        if backend.session_id is not None:
            backend.close_session(session)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--candidate", choices=tuple(CANDIDATES), required=True)
    parser.add_argument("--review-public-answers", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config, checkout_root=ROOT)
    core = CANDIDATES[args.candidate].read_text(encoding="utf-8")
    prompt = (compose_system_prompt(core, SETTINGS) if args.candidate != "V1" else None)
    system_message = prompt.system_message if prompt is not None else core

    import litert_lm
    with tempfile.TemporaryDirectory(prefix="prompt-engineering-") as directory:
        inference = {
            "temperature": 0.0,
            "top_p": 1.0,
            "maximum_output_tokens": 128,
            "user_new_token_admission": 32,
            "engine_kv_tokens": 1024,
            "threads": 4,
            "model_path": str(runtime_model_path(config, directory)),
            "cache_dir": str(cache_object_path(config)),
        }
        engine = litert_lm.Engine(
            inference["model_path"],
            backend=litert_lm.Backend.CPU(thread_count=4),
            cache_dir=inference["cache_dir"],
            enable_benchmark=True,
            max_num_tokens=1024,
        )
        backend = EfficiencyLiteRtBackend(
            inference,
            encoding="J",
            system_message=system_message,
            user_template=(CONTRACT / "user-turn-template-v1.txt").read_text(encoding="utf-8"),
            semantic_schema=json.loads(
                (CONTRACT / "semantic-output-v1.schema.json").read_text(encoding="utf-8")),
            profile_digest=hashlib.sha256(system_message.encode()).hexdigest(),
            child_generation=1,
            litert_lm_module=litert_lm,
            engine=engine,
        )
        try:
            screen = [
                _one(
                    backend,
                    f"screen-{case_id}",
                    text,
                    expectation,
                    include_public_answer=args.review_public_answers,
                )
                for case_id, text, expectation in SCREEN_CASES
            ]
            confirmation = []
            if all(item["pass"] for item in screen):
                for repetition in range(1, 4):
                    session = f"timing-{repetition}"
                    backend.open_session(session, SESSION_FACTS)
                    try:
                        for turn_id, text in enumerate(TIMING_PAIR, 1):
                            try:
                                result = backend.generate_turn(
                                    session, turn_id, SESSION_FACTS, _turn(text))
                            except MvaBackendError as error:
                                confirmation.append({
                                    "case_id": f"timing-{repetition}-{turn_id}",
                                    "pass": False,
                                    "terminal": error.code,
                                })
                                break
                            confirmation.append(_metrics(
                                result,
                                case_id=f"timing-{repetition}-{turn_id}",
                                passed=_passes("answer", result.generation.semantic),
                                include_public_answer=args.review_public_answers,
                            ))
                    finally:
                        if backend.session_id is not None:
                            backend.close_session(session)
            output = {
                "status": "ENGINEERING_NON_FORMAL_USER_REVIEW_REQUIRED",
                "candidate": args.candidate,
                "core_tokens": len(engine.tokenize(prompt.core if prompt is not None else system_message)),
                "settings_tokens": len(engine.tokenize(prompt.trusted_settings)) if prompt is not None else 0,
                "system_tokens": len(engine.tokenize(system_message)),
                "screen": screen,
                "screen_pass": all(item["pass"] for item in screen),
                "confirmation": confirmation,
                "confirmation_pass": bool(confirmation) and all(
                    item["pass"] for item in confirmation),
            }
            print(json.dumps(output, ensure_ascii=False, sort_keys=True, allow_nan=False))
            return 0 if output["screen_pass"] and output["confirmation_pass"] else 1
        finally:
            backend.close()


if __name__ == "__main__":
    raise SystemExit(main())
