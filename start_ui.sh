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
: "${SIA_UPLOAD_ENDPOINT:=/device_ingest.php}"
: "${SIA_HEALTH_ENDPOINT:=/device_ingest.php}"
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

# shellcheck disable=SC1091
source "$VENV/bin/activate"

exec python -m device.main >> "$LOG_FILE" 2>&1
