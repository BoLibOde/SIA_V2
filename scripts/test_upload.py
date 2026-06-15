#!/usr/bin/env python3
"""test_upload.py -- send a realistic sample payload to the SIA V2 server.

Run from any machine that can reach the server over Tailscale:

    python3 scripts/test_upload.py

Expected output on success:
    Status: 200
    Body: {"status":"ok","stored":true}
"""

import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

SERVER_URL = "http://100.74.7.35:8000/api/v1/ingest/hourly"

# Sample payload – matches HourlyUploadRequest schema on the server
payload = {
    "device_id": "pi-room-01",
    "period_start": "2026-06-11T10:00:00",
    "period_end": "2026-06-11T11:00:00",
    "mood_counts": {
        "good": 5,
        "neutral": 2,
        "bad": 1,
    },
    "sensor_avg": {
        "temperature_c": 22.5,
        "humidity_pct": 48.0,
        "co2_ppm": 650,
    },
    "sample_count": 12,
}

print(f"POST {SERVER_URL}")
print(f"Payload: {payload}")
print()

try:
    response = requests.post(SERVER_URL, json=payload, timeout=10)
except requests.ConnectionError as exc:
    print(f"Connection error: {exc}", file=sys.stderr)
    print("Check that the server is running and that Tailscale is connected.", file=sys.stderr)
    sys.exit(1)
except requests.Timeout:
    print("Request timed out after 10 s.", file=sys.stderr)
    sys.exit(1)

print(f"Status: {response.status_code}")
print(f"Body:   {response.text}")

if response.status_code in (200, 201):
    print("\n✓ Upload successful")
elif response.status_code == 409:
    print("\n✓ Duplicate (already stored for this period) – server is reachable")
else:
    print(f"\n✗ Unexpected status {response.status_code}", file=sys.stderr)
    sys.exit(1)
