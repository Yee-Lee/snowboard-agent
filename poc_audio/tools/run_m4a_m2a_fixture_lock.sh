#!/usr/bin/env bash
# Derive the exact ACK-003 M2A 8+12 PCM fixture lock without candidate execution.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_m2a_fixture_lock "$@"
