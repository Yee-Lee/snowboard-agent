#!/usr/bin/env bash
# Assemble reviewed sanitized M2A rows; never accepts controlled transcripts.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$repo_root/poc_audio/src"
python3 -m audio_poc.m2a_scorecard "$@"
