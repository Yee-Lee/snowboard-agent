"""Materialize an M5.tool release profile from accepted memory limits and Pi token count."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sbd.cognition.litert_lm.m5_profile import load_m5_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m4-release-profile", type=Path, required=True)
    parser.add_argument("--prompt-tokens", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        parser.error("output must be new in an existing directory")
    source = json.loads(args.m4_release_profile.read_text())
    if source.get("profile_id") != "core-m4b-cognition-001" or source.get("profile_stage") != "release":
        parser.error("accepted M4 release profile required")
    profile = load_m5_profile(ROOT / "requirements/m5tool/product-profile.json",
                              allow_template=True)
    profile.update(profile_stage="release", prompt_tokens=args.prompt_tokens,
        min_mem_available_generate_bytes=source.get("min_mem_available_generate_bytes"),
        min_mem_available_speak_bytes=source.get("min_mem_available_speak_bytes"))
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, (json.dumps(profile, ensure_ascii=False, indent=2) + "\n").encode())
    finally:
        os.close(descriptor)
    load_m5_profile(args.output)
    print("M5.tool release profile prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
