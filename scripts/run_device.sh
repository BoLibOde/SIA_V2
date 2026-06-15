#!/bin/bash
# run_device.sh -- stop the sia-device service (if running) and start the device manually.
# Intended for testing on the Raspberry Pi as user ebm.

set -euo pipefail

APP_DIR="/home/ebm/Desktop/SIA_V2"
VENV="$APP_DIR/.venv"

# Stop the background service so it doesn't conflict
if systemctl is-active --quiet sia-device 2>/dev/null; then
    echo "Stopping sia-device service..."
    sudo systemctl stop sia-device
fi

cd "$APP_DIR"
export SIA_SERVER_URL="${SIA_SERVER_URL:-http://100.74.7.35:8000}"

exec "$VENV/bin/python" -m device.main
