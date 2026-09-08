"""Collect the one missing non-formal D lifecycle memory observation on Pi."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from poc_llm.efficiency.backend import EfficiencyLiteRtBackend
from poc_llm.harness.mva_contract import SESSION_FACTS
from poc_llm.harness.mva_identity import load_config
from poc_llm.harness.mva_product_layout import cache_object_path, runtime_model_path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "poc_llm/contracts/mva"


def _pss_mib() -> float:
    for line in Path("/proc/self/smaps_rollup").read_text(encoding="utf-8").splitlines():
        if line.startswith("Pss:"):
            return round(int(line.split()[1]) / 1024, 3)
    raise RuntimeError("PSS_UNAVAILABLE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = load_config(args.config, checkout_root=ROOT)

    import litert_lm
    with tempfile.TemporaryDirectory(prefix="d-memory-engineering-") as directory:
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
        prompt = (CONTRACT / "system-prompt-v1.txt").read_text(encoding="utf-8")
        backend = EfficiencyLiteRtBackend(
            inference,
            encoding="J",
            system_message=prompt,
            user_template=(CONTRACT / "user-turn-template-v1.txt").read_text(encoding="utf-8"),
            semantic_schema=json.loads(
                (CONTRACT / "semantic-output-v1.schema.json").read_text(encoding="utf-8")),
            profile_digest=hashlib.sha256(prompt.encode()).hexdigest(),
            child_generation=1,
            litert_lm_module=litert_lm,
            engine=engine,
        )
        closed = False
        try:
            result = {"engine_ready_pss_mib": _pss_mib()}
            opened = backend.open_session("d-memory", SESSION_FACTS, readiness="D")
            result["conversation_open_pss_mib"] = _pss_mib()
            generated = backend.generate_turn(
                "d-memory",
                1,
                SESSION_FACTS,
                {"perceptions": [{
                    "kind": "listen", "status": "ok", "text": "天空為什麼是藍色的？",
                }]},
            )
            result.update({
                "open_ms": opened["open_ms"],
                "post_request_pss_mib": _pss_mib(),
                "reasoner_action": generated.action["action_kind"],
                "rendered_tokens": generated.generation.metrics["rendered_tokens"],
                "runtime_prefill_tokens": generated.generation.metrics["incremental_tokens"],
                "first_safe_chunk_ms": generated.generation.metrics["first_chunk_ms"],
                "terminal_ms": generated.generation.metrics["ttc_ms"],
            })
            backend.close_session("d-memory")
            time.sleep(1)
            result["one_second_after_conversation_close_pss_mib"] = _pss_mib()
            backend.close()
            closed = True
            result["after_engine_close_pss_mib"] = _pss_mib()
            result["status"] = "ENGINEERING_NON_FORMAL_USER_REVIEW_REQUIRED"
            print(json.dumps(result, sort_keys=True, allow_nan=False))
            return 0
        finally:
            if not closed:
                backend.close()


if __name__ == "__main__":
    raise SystemExit(main())
