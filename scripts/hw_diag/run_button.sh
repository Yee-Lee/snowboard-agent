#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
PYTHON="$REPO_ROOT/.venv/bin/python"
DEFAULT_CONFIG="$REPO_ROOT/config.m3.local.yaml"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: project Python is unavailable: $PYTHON" >&2
    exit 2
fi

has_config=0
for arg do
    case "$arg" in
        --config|--config=*) has_config=1 ;;
    esac
done
if [ "$has_config" -eq 0 ]; then
    set -- --config "$DEFAULT_CONFIG" "$@"
fi

cd "$REPO_ROOT"
exec "$PYTHON" "$SCRIPT_DIR/run_button.py" "$@"
