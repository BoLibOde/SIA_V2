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
    pkill -f "python -m device.main"
    attempts=0
    for ((i = 1; i <= MAX_STOP_CHECKS; i++)); do
        attempts="$i"
        if ! pgrep -f "python -m device.main" >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

if pgrep -f "python -m device.main" >/dev/null 2>&1; then
    echo "Could not stop existing device.main process cleanly after $attempts checks." >&2
    exit 1
fi

nohup "$START_SCRIPT" >/dev/null 2>&1 &

echo "UI restart triggered."
