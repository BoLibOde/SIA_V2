# SIA_V2

## Production reality (active path)

This repository contains multiple implementations.  
**The live production stack is currently:**

- PHP application (`/server/WEBSITE`)
- nginx
- php-fpm
- MariaDB (`stimmungsbarometer`)

The production webroot on the server is typically:

- `/var/www/html/stimmungsbarometer`

The PHP app reads/writes MariaDB tables including:

- `users`
- `locations`
- `measurements`
- `device_location_history`

---

## Device ingest endpoint for Raspberry Pi (production)

A dedicated machine endpoint now exists in the PHP app:

- `server/WEBSITE/device_ingest.php`
- deployed path example: `http://<host>/stimmungsbarometer/device_ingest.php`

### Behavior

- `GET` returns JSON health info (`200`).
- `POST` expects JSON payload.
- No browser session login is required.
- Stores one measurement row in `measurements`.
- Resolves `location_id` from `device_location_history` by `valid_from <= created_at` (latest match).
- Returns JSON and proper HTTP status codes.

### Optional shared secret (recommended)

Set `device_ingest_token` in `server/WEBSITE/db.local.php` (see `db.local.example.php`) and send it as:

- HTTP header: `X-Device-Token: <token>`
- (fallback) JSON field: `token`

If configured and missing/invalid, endpoint returns `401`.

### Supported POST JSON formats

1) Direct measurement format:

```json
{
  "mood": "neutral",
  "co2": 640,
  "humidity": 42.5,
  "temperature": 21.4,
  "created_at": "2026-06-16T19:00:00+02:00"
}
```

2) Raspberry Pi hourly payload format (from `device/upload_service.py`):

```json
{
  "device_id": "pi-room-01",
  "period_start": "2026-06-16T18:00:00+02:00",
  "period_end": "2026-06-16T19:00:00+02:00",
  "mood_counts": { "good": 4, "neutral": 2, "bad": 1 },
  "sensor_avg": {
    "temperature_c": 21.6,
    "humidity_pct": 41.9,
    "co2_ppm": 618
  },
  "sample_count": 12
}
```

The endpoint maps hourly payload fields to `measurements` and derives mood from `mood_counts`.

---

## PHP database configuration (production)

Main config file:

- `server/WEBSITE/db.php`

Local override file (not committed):

- `server/WEBSITE/db.local.php`

Example:

```php
<?php
return [
    'host' => 'localhost',
    'dbname' => 'stimmungsbarometer',
    'user' => 'sia_web',
    'pass' => 'CHANGE_ME',
    'timezone' => '+02:00',
    'device_ingest_token' => 'CHANGE_ME_DEVICE_TOKEN',
];
```

---

## Raspberry Pi upload configuration

Device defaults in `device/config.py` now point to the PHP ingest path:

- `SIA_SERVER_URL` default: `http://100.74.7.35`
- `SIA_UPLOAD_ENDPOINT` default: `/stimmungsbarometer/device_ingest.php`
- `SIA_HEALTH_ENDPOINT` default: `/stimmungsbarometer/device_ingest.php`
- `SIA_DEVICE_TOKEN` optional (sent as `X-Device-Token`)

Example override:

```bash
export SIA_SERVER_URL="http://YOUR_HOST"
export SIA_UPLOAD_ENDPOINT="/stimmungsbarometer/device_ingest.php"
export SIA_HEALTH_ENDPOINT="/stimmungsbarometer/device_ingest.php"
export SIA_DEVICE_TOKEN="CHANGE_ME_DEVICE_TOKEN"
python -m device.main
```

---

## Operational checklist (production)

### Services

- [ ] MariaDB running
- [ ] nginx running
- [ ] php-fpm running

### Web app reachability

- [ ] `http://127.0.0.1/login.php` returns page (or expected redirect/auth behavior)
- [ ] `http://127.0.0.1/dashboard.php` reachable after login

### MariaDB checks

- [ ] Database `stimmungsbarometer` exists
- [ ] Tables `users`, `locations`, `measurements`, `device_location_history` exist
- [ ] DB credentials in `db.local.php` are valid

### Device ingest checks

- [ ] `GET /stimmungsbarometer/device_ingest.php` returns JSON health
- [ ] `POST /stimmungsbarometer/device_ingest.php` with valid payload stores a row in `measurements`
- [ ] Dashboard shows the newly stored measurement

Example test POST:

```bash
curl -i -X POST "http://127.0.0.1/stimmungsbarometer/device_ingest.php" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: CHANGE_ME_DEVICE_TOKEN" \
  -d '{
    "mood":"neutral",
    "co2":620,
    "humidity":41.7,
    "temperature":21.8,
    "created_at":"2026-06-16T19:00:00+02:00"
  }'
```

---

## Python/FastAPI code in this repository (alternate/non-production path)

The repository still contains:

- Python device application (`/device`)
- FastAPI backend (`/server/main.py`, `/server/routes`, SQLAlchemy models)

This is useful for development/experimentation and remains in the repo, but it is **not the currently active production deployment path** described above.

---

## Tests

```bash
pip install -r requirements-server.txt
pytest
```
