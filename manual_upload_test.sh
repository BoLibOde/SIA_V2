#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$APP_DIR/.env.device"
NOW="$(date -Iseconds)"

if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

: "${SIA_SERVER_URL:=http://100.74.7.35}"
: "${SIA_UPLOAD_ENDPOINT:=/device_ingest.php}"
: "${SIA_DEVICE_TOKEN:?Set SIA_DEVICE_TOKEN in .env.device}"
: "${SIA_DEVICE_ID:=pi-room-01}"

REQUEST_BODY=$(cat <<JSON
{
  "device_id": "${SIA_DEVICE_ID}",
  "mood": "neutral",
  "co2": 650,
  "humidity": 42.5,
  "temperature": 22.1,
  "created_at": "${NOW}"
}
JSON
)

curl -i -X POST "${SIA_SERVER_URL}${SIA_UPLOAD_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: ${SIA_DEVICE_TOKEN}" \
  --data "$REQUEST_BODY"
