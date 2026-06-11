# API Reference

Base URL: `http://<server-ip>:8000`

Interactive docs: `http://<server-ip>:8000/docs`

---

## Health

### `GET /api/v1/health`

Quick connection test. Returns 200 when the server is running.

**Response**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```

---

## Ingest (device → server)

### `POST /api/v1/ingest/hourly`

The device POSTs this once per hour.

**Request body**
```json
{
  "device_id": "pi-room-01",
  "period_start": "2024-01-15T09:00:00",
  "period_end":   "2024-01-15T10:00:00",
  "mood_counts": {
    "good": 12,
    "neutral": 5,
    "bad": 3
  },
  "sensor_avg": {
    "temperature_c": 22.4,
    "humidity_pct": 48.1,
    "co2_ppm": 612
  },
  "sample_count": 720
}
```

**Response 200**
```json
{ "status": "ok", "stored": true }
```

**Response 409** – upload already exists for this device + period (idempotent, safe to ignore).

---

## Summary (server → website)

### `GET /api/v1/devices/{device_id}/summary`

Aggregated mood + sensor summary for one device.

**Query params**
| Param  | Values            | Default |
|--------|-------------------|---------|
| range  | day / week / month | day    |

**Response 200**
```json
{
  "device_id": "pi-room-01",
  "range": "day",
  "counts": { "good": 42, "neutral": 18, "bad": 7 },
  "sensor_avg": { "temperature_c": 22.1, "humidity_pct": 47.5, "co2_ppm": 598 },
  "score": 0.519,
  "smiley": "good"
}
```

`score` is `(good - bad) / total` in [-1, 1].
`smiley` is `"good"` (score > 0.25) | `"neutral"` | `"bad"` (score < -0.25).

**Response 404** – device not found.

---

### `GET /api/v1/summary/global`

Same as above but across **all devices combined**.

**Query params** – same as device summary.

**Response 200**
```json
{
  "range": "day",
  "device_count": 3,
  "counts": { "good": 120, "neutral": 55, "bad": 20 },
  "sensor_avg": { "temperature_c": 21.8, "humidity_pct": 46.0, "co2_ppm": 610 },
  "score": 0.513,
  "smiley": "good"
}
```

---

### `GET /api/v1/devices/{device_id}/history`

Hourly data points for charting / time series.

**Query params**
| Param | Range      | Default |
|-------|------------|---------|
| hours | 1 – 720    | 24      |

**Response 200**
```json
{
  "device_id": "pi-room-01",
  "hours": 24,
  "entries": [
    {
      "period_start": "2024-01-15T08:00:00",
      "period_end":   "2024-01-15T09:00:00",
      "counts": { "good": 8, "neutral": 3, "bad": 1 },
      "score": 0.583,
      "smiley": "good",
      "avg_temperature_c": 22.3,
      "avg_co2_ppm": 605
    }
  ]
}
```

**Response 404** – device not found.

---

## Notes for the website teammate

- All timestamps are **UTC ISO 8601**.
- CORS is open (`*`) for the prototype – all origins allowed.
- The server exposes Swagger UI at `/docs` and ReDoc at `/redoc`.
- Use `/api/v1/health` to show a connection indicator.
- For a live dashboard, poll `/api/v1/summary/global?range=day` every 30–60 s.
- For charts, fetch `/api/v1/devices/{id}/history?hours=24` and map `entries` to your charting library.
