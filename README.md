# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Repository file structure

```text
SIA_V2/
├── README.md
├── setup.sh
├── requirements-device.txt
├── requirements-server.txt
├── device/
│   ├── __init__.py
│   ├── aggregation_service.py
│   ├── config.py
│   ├── gpio_handler.py
│   ├── main.py
│   ├── models.py
│   ├── sensor_service.py
│   ├── ui.py
│   ├── upload_service.py
│   └── assets/
│       ├── bad.png
│       ├── bad.svg
│       ├── empty.txt
│       ├── good.png
│       ├── good.svg
│       ├── meh.png
│       └── meh.svg
└── server/
    ├── __init__.py
    ├── db.py
    ├── main.py
    ├── models.py
    ├── schemas.py
    └── routes/
        ├── __init__.py
        ├── ingest.py
        ├── live.py
        ├── locations.py
        └── summary.py
```

## Quick setup (Raspberry Pi / target machine)

Run `setup.sh` once to clone the repo into `~/Desktop/SIA_V2` and install everything.  
Run it again at any time to update only changed files.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Or, if you already have the file locally:

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
1. Install required system packages (`git`, `python3`, `pygame`, etc.)
2. Clone `BoLibOde/SIA_V2` into `~/Desktop/SIA_V2` (or pull the latest changes if already cloned)
3. Install all Python dependencies from `requirements-device.txt` and `requirements-server.txt`
4. Verify the repo state and report success or any missing files

After setup, start the device app with:

```bash
~/Desktop/SIA_V2/.venv/bin/python -m device.main
```

## Server run

1. Create a virtual environment
2. Install dependencies from `requirements-server.txt`
3. Set `DATABASE_URL`
4. Run:

```bash
uvicorn server.main:app --reload
```

## Backend data model (prototype)

- `hourly_uploads`: historical base data (hourly rollups)
- `device_live_states`: latest live values + today counters for dashboard
- `device_locations`: location history with `valid_from` / `valid_to`

Location history keeps old data correct when a device moves between rooms.

## API overview

### Ingest

- `POST /api/v1/ingest/hourly`
- `POST /api/v1/ingest/live`

Live payload example:

```json
{
  "device_id": "device-01",
  "timestamp": "2026-06-11T16:30:00",
  "latest_mood": "good",
  "today_counts": { "good": 12, "neutral": 5, "bad": 2 },
  "sensor_current": { "temperature_c": 22.1, "humidity_pct": 47.3, "co2_ppm": 560 }
}
```

### Live dashboard

- `GET /api/v1/live`
- `GET /api/v1/devices/{device_id}/live`
- `GET /api/v1/devices/{device_id}/today`

### Location history

- `POST /api/v1/devices/{device_id}/location`
- `GET /api/v1/devices/{device_id}/locations`

Assign location example:

```json
{
  "location": "Raum A",
  "valid_from": "2026-06-06T00:00:00"
}
```

### Historical summary (flexible for website)

- `GET /api/v1/summary?from=...&to=...&device_id=...&location=...&group_by=hour|day|week|month|year`

Response includes totals, percentages, score, smiley, sensor averages, and chart `series`.

Example request:

```text
/api/v1/summary?from=2026-06-01T00:00:00&to=2026-06-30T23:59:59&group_by=day&device_id=device-01&location=Raum%20A
```

Example response:

```json
{
  "from_dt": "2026-06-01T00:00:00",
  "to_dt": "2026-06-30T23:59:59",
  "group_by": "day",
  "device_filter": "device-01",
  "location_filter": "Raum A",
  "counts": { "good": 180, "neutral": 50, "bad": 20 },
  "percentages": { "good": 72, "neutral": 20, "bad": 8 },
  "sensor_avg": { "temperature_c": 22.4, "humidity_pct": 45.8, "co2_ppm": 590 },
  "score": 0.64,
  "smiley": "good",
  "series": [
    {
      "bucket_start": "2026-06-01T00:00:00",
      "device_id": "device-01",
      "location": "Raum A",
      "counts": { "good": 6, "neutral": 2, "bad": 1 },
      "sensor_avg": { "temperature_c": 22.0, "humidity_pct": 46.2, "co2_ppm": 570 },
      "score": 0.556,
      "smiley": "good"
    }
  ]
}
```

### Day / Week / Month / Year JSON usage

Use the same endpoint and only change `group_by` + date range:

- Day: `group_by=hour`, range = one day
- Week: `group_by=day`, range = one week
- Month: `group_by=day` or `group_by=week`, range = one month
- Year: `group_by=month`, range = one year

Legacy endpoint still exists:

- `GET /api/v1/devices/{device_id}/summary?range=day|week|month|year`
