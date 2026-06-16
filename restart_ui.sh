#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SCRIPT="$APP_DIR/start_ui.sh"
MAX_STOP_CHECKS=20

echo "Restarting SIA UI..."

if [ ! -x "$START_SCRIPT" ]; then
    echo "Missing or non-executable start script: $START_SCRIPT" >&2
    exit 1
fi

if pgrep -f "python -m device.main" >/dev/null 2>&1; then
    pkill -TERM -f "python -m device.main"
    checks=0
    while pgrep -f "python -m device.main" >/dev/null 2>&1 && [ "$checks" -lt "$MAX_STOP_CHECKS" ]; do
        checks=$((checks + 1))
        sleep 0.5
    done
fi

if pgrep -f "python -m device.main" >/dev/null 2>&1; then
    echo "Process still running after graceful stop, sending SIGKILL..." >&2
    pkill -KILL -f "python -m device.main" || true
    sleep 1
    if pgrep -f "python -m device.main" >/dev/null 2>&1; then
        echo "Could not stop existing device.main process cleanly." >&2
        exit 1
    fi
fi

nohup "$START_SCRIPT" >/dev/null 2>&1 &

echo "UI restart triggered."
