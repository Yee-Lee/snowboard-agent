#!/usr/bin/env bash
# Derive the reviewed C PCM locks without candidate execution.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m2b_c_fixture_lock "$@"
