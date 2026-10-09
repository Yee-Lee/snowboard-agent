#!/bin/sh
# Foreground product launcher. Ctrl+C requests the App's normal shutdown.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
APP_PYTHON="$REPO_ROOT/.venv/bin/python"
APP_CONFIG="$REPO_ROOT/config.local.yaml"

usage() {
    printf '%s\n' \
        'Usage: run-app.sh [--config FILE] [--python EXECUTABLE]' \
        'Defaults: repository config.local.yaml and .venv/bin/python.' \
        'Runs the real App in the foreground with microphone and hardware input.' \
        'Short press: start/end a conversation. Long press or Ctrl+C: stop App.' \
        'Stopping App does not power off the Pi. Closing the terminal may stop App.'
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --config|--python)
            if [ "$#" -lt 2 ] || [ -z "$2" ]; then
                printf '%s\n' 'ERROR: option requires a value.' >&2
                exit 2
            fi
            case "$1" in
                --config) APP_CONFIG=$2 ;;
                --python) APP_PYTHON=$2 ;;
            esac
            shift 2 ;;
        *) printf '%s\n' 'ERROR: unknown argument; use --help.' >&2; exit 2 ;;
    esac
done

# Resolve operator-relative paths before changing to the repository directory.
case "$APP_CONFIG" in
    /*) ;;
    *) APP_CONFIG="$PWD/$APP_CONFIG" ;;
esac
if [ ! -f "$APP_CONFIG" ]; then
    printf '%s\n' 'ERROR: config file is missing; provide --config FILE.' >&2
    exit 2
fi
APP_PYTHON=$(command -v "$APP_PYTHON") || {
    printf '%s\n' 'ERROR: Python is unavailable; provide --python EXECUTABLE.' >&2
    exit 2
}
case "$APP_PYTHON" in
    /*) ;;
    *) APP_PYTHON="$PWD/$APP_PYTHON" ;;
esac

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$APP_PYTHON" -u -c '
import asyncio
import sys
from sbd.main import bootstrap_logging, run_app
bootstrap_logging()
raise SystemExit(asyncio.run(run_app(sys.argv[1])))
' "$APP_CONFIG"
