#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <full-source-sha> <sanitized-output-json>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.run_m4a_fake_conformance \
  --source-sha "$1" \
  --output "$2"
