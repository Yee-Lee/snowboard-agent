"""Exact-identity, no-model-load preflight for AR1M1 development probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixture_preflight import verify_controlled_smoke_fixture
from .m1_baseline import _repo_root, _verify_external
from .m1_lifecycle import _build_backend
from .nemo_adapter import NemoSpeechCBackend


def run_preflight(args: argparse.Namespace) -> dict[str, object]:
    fixture = _verify_external(args.fixture, _repo_root(), "controlled audio")
    identity = verify_controlled_smoke_fixture(_repo_root(), fixture)
    backend = _build_backend(args)
    runtime_identity = "sherpa-onnx 1.13.5"
    if isinstance(backend, NemoSpeechCBackend):
        runtime_identity = backend.verify_runtime_identity()
    return {
        "schema_version": "1.0",
        "formal_result": False,
        "candidate_id": args.candidate_id,
        "fixture_id": identity.fixture_id,
        "preflight_completed": True,
        "status": "NON_FORMAL_EXACT_IDENTITY_PREFLIGHT_COMPLETED",
        "artifact_identity_verified": True,
        "dependency_identity_verified": True,
        "fixture_identity_verified": True,
        "runtime_identity": runtime_identity,
        "model_loaded": False,
        "interpretation": "NON_FORMAL_WORKSTATION_PREFLIGHT",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--artifact-archive", type=Path)
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--runtime-library", type=Path)
    parser.add_argument("--runtime-artifact", action="append", type=Path, default=[])
    parser.add_argument("--num-threads", type=int, default=2)
    return parser


def main() -> int:
    result = run_preflight(_parser().parse_args())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
