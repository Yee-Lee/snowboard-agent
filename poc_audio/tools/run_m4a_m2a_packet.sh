#!/usr/bin/env bash
# Validate ACK-003 M2A identities or create a controlled pre-output fixture selection.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHONPATH="$repo_root/poc_audio/src" python3 -m audio_poc.m4a_m2a_packet "$@"
