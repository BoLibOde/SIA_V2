# API Reference

## Production endpoint (PHP)

The active production ingest endpoint is part of the PHP app served by nginx on the server.

### Health check

**`GET /stimmungsbarometer/device_ingest.php`**

Returns `200` with JSON when the PHP app is reachable.

```json
{ "status": "ok", "service": "php-device-ingest" }
```

---

### Ingest (device → server)

**`POST /stimmungsbarometer/device_ingest.php`**

The Raspberry Pi sends data here after each button press (live event) and once per
15-minute sensor window (aggregate).

**Authentication (optional, recommended)**

Send the shared secret as the `X-Device-Token` HTTP header.  
Configure the token in `server/WEBSITE/db.local.php` as `device_ingest_token`.

**Supported request body formats**

1. Direct measurement (single row):

```json
{
  "location_id": 1,
  "mood": "neutral",
  "co2": 640,
  "humidity": 42.5,
  "temperature": 21.4,
  "created_at": "2026-06-16T19:00:00+02:00"
}
```

2. Raspberry Pi 15-minute sensor aggregate (from `device/upload_service.py`):

```json
{
  "upload_type": "sensor_hourly",
  "device_id": "pi-room-01",
  "period_start": "2026-06-16T18:45:00+02:00",
  "period_end":   "2026-06-16T19:00:00+02:00",
  "sensor_avg": {
    "temperature_c": 21.6,
    "humidity_pct": 41.9,
    "co2_ppm": 618
  },
  "sample_count": 12
}
```

`location_id` is resolved from `device_location_history` if not supplied.
Sensor aggregate uploads do not create mood rows in `measurements`.

**Response 201** – row stored:

```json
{
  "status": "stored",
  "measurement_id": 42,
  "location_id": 1,
  "created_at": "2026-06-16 19:00:00"
}
```

**Response 400** – missing or invalid fields.  
**Response 401** – missing/invalid token (only when token is configured).  
**Response 422** – no device location configured for the given timestamp.  
**Response 500** – database error.

---

### Today mood counts (server → device, read-only)

**`GET /stimmungsbarometer/device_today_counts.php?device_id=pi-room-01`**

Returns today's authoritative mood counts for the current location.

- reads only from `measurements`
- never writes to the database
- accepts optional `location_id`
- otherwise resolves the location via `device_location_history`
- uses the same optional `X-Device-Token` header as `device_ingest.php`

**Response 200**

```json
{
  "status": "ok",
  "date": "2026-06-18",
  "timezone": "+02:00",
  "location_id": 1,
  "device_id": "pi-room-01",
  "counts": {
    "good": 12,
    "neutral": 4,
    "bad": 3
  },
  "total": 19
}
```

Zero-count days still return `200` with zero values.

---

### Dashboard data

The PHP dashboard reads directly from the `measurements` MariaDB table via
`dashboard_data_service.php`.  There is no separate JSON API for the dashboard;
it is server-rendered PHP.

Available ranges (query parameter `range`): `tag`, `woche`, `monat`, `jahr`, `gesamt`.

---

## Alternate / development endpoint (FastAPI – not in production)

The repository contains a FastAPI backend (`server/main.py`, `server/routes/`) that was
the original prototype.  It is **not deployed** in the current production environment.

Base URL when running locally: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `POST /api/v1/ingest/hourly` | Hourly aggregate ingest |
| `GET /api/v1/devices/{id}/summary` | Mood + sensor summary |
| `GET /api/v1/summary/global` | Global summary across all devices |
| `GET /api/v1/devices/{id}/history` | Time-series history |

See the inline Swagger docs (`/docs`) for full request/response schemas when running locally.
