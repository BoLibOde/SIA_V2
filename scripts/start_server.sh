#!/bin/bash
# start_server.sh -- start the SIA V2 FastAPI server on Ubuntu.
# Uses /opt/SIA_V2 as the app directory.
#
# DATABASE_URL is read from the environment (set via systemd EnvironmentFile or exported
# before calling this script).  The fallback below is used only when nothing else sets it.

set -euo pipefail

APP_DIR="/opt/SIA_V2"
VENV="$APP_DIR/.venv"
DATABASE_URL_DEFAULT="******localhost:5432/sia_v2"

cd "$APP_DIR"

if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet --upgrade -r "$APP_DIR/requirements-server.txt"

export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

exec "$VENV/bin/uvicorn" server.main:app --host 0.0.0.0 --port 8000
