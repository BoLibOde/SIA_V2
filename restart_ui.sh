#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restarting SIA UI..."

if pgrep -f "python -m device.main" >/dev/null 2>&1; then
    pkill -f "python -m device.main"
    sleep 2
fi

nohup "$APP_DIR/start_ui.sh" >/dev/null 2>&1 &

echo "UI restart triggered."
