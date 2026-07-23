#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"

# Convert to a path the interpreter understands (Git-Bash on Windows needs win paths).
if command -v cygpath >/dev/null 2>&1; then
    SRC_DIR="$(cygpath -w "$HERE/src")"
else
    SRC_DIR="$HERE/src"
fi
export PYTHONPATH="$SRC_DIR${PYTHONPATH:+;$PYTHONPATH}"

# Prefer python3.11; fall back to `py -3.11` on Windows.
if command -v python3.11 >/dev/null 2>&1; then
    exec python3.11 -m sbd.main "$@"
else
    exec py -3.11 -m sbd.main "$@"
fi
