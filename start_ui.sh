#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env.device"
LOG_FILE="$APP_DIR/ui-autostart.log"

cd "$APP_DIR"

if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

: "${SIA_SERVER_URL:?Set SIA_SERVER_URL in .env.device}"
: "${SIA_UPLOAD_ENDPOINT:=/stimmungsbarometer/device_ingest.php}"
: "${SIA_HEALTH_ENDPOINT:=/stimmungsbarometer/device_ingest.php}"
: "${SIA_DEVICE_TOKEN:=}"
: "${SIA_DEVICE_ID:=pi-room-01}"

export SIA_SERVER_URL
export SIA_UPLOAD_ENDPOINT
export SIA_HEALTH_ENDPOINT
export SIA_DEVICE_TOKEN
export SIA_DEVICE_ID

if [ ! -f "$VENV/bin/activate" ]; then
    echo "Missing virtual environment activation script: $VENV/bin/activate" >&2
    exit 1
fi

# Guard against double instances: if device.main is already running (e.g.
# started by systemd or a previous autostart), skip startup and exit cleanly.
# This prevents two processes from uploading the same mood events when both
# the systemd service and the desktop autostart entry are active.
if pgrep -f "python -m device.main" >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] device.main is already running; skipping duplicate startup" >&2
    exit 0
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

exec python -m device.main >> "$LOG_FILE" 2>&1
