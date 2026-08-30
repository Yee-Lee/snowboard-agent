#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
PYTHON="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: project Python is unavailable: $PYTHON" >&2
    exit 2
fi

cd "$REPO_ROOT"
exec "$PYTHON" "$REPO_ROOT/scripts/hw_diag.py" "$@"
