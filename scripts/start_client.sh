#!/bin/bash
# start_client.sh -- start the SIA V2 device client on Raspberry Pi.
# Uses /home/pi/Desktop/SIA_V2 as the app directory.

set -euo pipefail

APP_DIR="/home/pi/Desktop/SIA_V2"
VENV="$APP_DIR/.venv"

cd "$APP_DIR"

if [ ! -d "$VENV" ]; then
    # inherit system-site-packages so pygame (installed via apt) is available
    python3 -m venv --system-site-packages "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet --upgrade -r "$APP_DIR/requirements-device.txt"

exec "$VENV/bin/python" -m device.main
