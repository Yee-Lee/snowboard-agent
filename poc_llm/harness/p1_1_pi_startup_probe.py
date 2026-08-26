#!/usr/bin/env python3
"""Non-scoring wrapper that timestamps Pi child startup and applies a frozen P1.1 profile."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import poc_llm.harness.litert_lm_pi_child_adapter_v2 as target


def mark(stage: str) -> None:
    print(f"P1_1_STAGE {stage} {time.monotonic_ns()}", file=sys.stderr, flush=True)


def pop_probe_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--p1-1-profile",
        choices=("baseline", "bounded_context"),
        required=True,
    )
    parser.add_argument("--p1-1-max-num-tokens", type=int)
    values, remaining = parser.parse_known_args()
    sys.argv[1:] = remaining
    return values


probe_args = pop_probe_args()
OriginalBackend = target.LiteRtBackend


class StartupProbeBackend(OriginalBackend):
    def __init__(self, config: dict[str, Any]):
        mark("backend_start")
        mark("litert_import_start")
        import litert_lm
        mark("litert_import_end")

        original_engine = litert_lm.Engine
        original_sampler = litert_lm.SamplerConfig

        def engine(*args: Any, **kwargs: Any):
            mark("engine_start")
            if probe_args.p1_1_profile == "bounded_context":
                if probe_args.p1_1_max_num_tokens is None:
                    raise ValueError("bounded context profile is missing max_num_tokens")
                kwargs["max_num_tokens"] = probe_args.p1_1_max_num_tokens
            value = original_engine(*args, **kwargs)
            mark("engine_end")
            return value

        def sampler(*args: Any, **kwargs: Any):
            mark("sampler_start")
            value = original_sampler(*args, **kwargs)
            mark("sampler_end")
            return value

        litert_lm.Engine = engine
        litert_lm.SamplerConfig = sampler
        try:
            super().__init__(config)
        finally:
            litert_lm.Engine = original_engine
            litert_lm.SamplerConfig = original_sampler
        mark("backend_end")


original_load = target.load_pi_config_v2


def diagnostic_load(*args: Any, **kwargs: Any):
    mark("config_receipt_start")
    value = original_load(*args, **kwargs)
    mark("config_receipt_end")
    return value


original_protocol = target.protocol_validator


def diagnostic_protocol(*args: Any, **kwargs: Any):
    mark("protocol_validator_start")
    value = original_protocol(*args, **kwargs)
    mark("protocol_validator_end")
    return value


original_ready = target.PiChild.ready


def diagnostic_ready(self: Any):
    mark("ready_emit_start")
    value = original_ready(self)
    mark("ready_emit_end")
    return value


target.LiteRtBackend = StartupProbeBackend
target.load_pi_config_v2 = diagnostic_load
target.protocol_validator = diagnostic_protocol
target.PiChild.ready = diagnostic_ready

mark(f"profile:{probe_args.p1_1_profile}")
mark("adapter_main_start")
raise SystemExit(target.main())
