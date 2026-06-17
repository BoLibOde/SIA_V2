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
- `sensor_hourly_aggregates`
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
- Stores **live mood events** in `measurements`.
- Stores **hourly sensor averages** in `sensor_hourly_aggregates`.
- Uses `location_id` from payload when provided.
- Otherwise resolves `location_id` from `device_location_history` by the payload timestamp (`created_at` for live events, `period_end` for hourly sensor uploads).
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
  "location_id": 1,
  "mood": "neutral",
  "co2": 640,
  "humidity": 42.5,
  "temperature": 21.4,
  "created_at": "2026-06-16T19:00:00+02:00"
}
```

2) Raspberry Pi live mood event format:

```json
{
  "upload_type": "mood_live",
  "mood": "positiv",
  "co2": 618,
  "humidity": 41.9,
  "temperature": 21.6,
  "created_at": "2026-06-16T19:03:10+02:00"
}
```

3) Raspberry Pi hourly sensor payload format (from `device/upload_service.py`):

```json
{
  "upload_type": "sensor_hourly",
  "device_id": "pi-room-01",
  "period_start": "2026-06-16T18:00:00+02:00",
  "period_end": "2026-06-16T19:00:00+02:00",
  "sensor_avg": {
    "temperature_c": 21.6,
    "humidity_pct": 41.9,
    "co2_ppm": 618
  },
  "sample_count": 12
}
```

Hourly sensor payloads no longer create mood votes. Legacy hourly payloads that still contain
`mood_counts` are accepted for compatibility, but the counts are ignored and only the sensor
hour is stored. For multi-device setups, include `location_id` explicitly in payloads.

---

## PHP database configuration (production)

Main config file:

- `server/WEBSITE/db.php`

Local override file — **server-local only, never committed**:

- `server/WEBSITE/db.local.php`

This file is listed in `.gitignore` and excluded from all deploys.
Copy the example to create it on a new server:

```bash
cp server/WEBSITE/db.local.example.php /var/www/html/stimmungsbarometer/db.local.php
# then edit with real credentials and token
```

Example (`db.local.example.php`):

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

## Raspberry Pi runtime/deploy hygiene

For Raspberry Pi desktop autostart + local secret handling, use [`PI_SETUP.md`](PI_SETUP.md).

Quick start:

```bash
cp .env.device.example .env.device
./manual_upload_test.sh
./start_ui.sh
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

## Admin functions (production PHP app)

All admin pages are accessible from the **Admin-Bereich** (`/admin.php` or the equivalent
deployed URL, e.g. `http://<host>/stimmungsbarometer/admin.php`).  
Login as admin is required; non-admin users are redirected to the dashboard.

| Page | Path | Description |
|---|---|---|
| Admin overview | `admin.php` | Navigation hub for all admin functions |
| Manage locations | `admin_locations.php` | View, edit, delete locations |
| Add location | `add_location.php` | Create a new location |
| Add measurement | `add_measurement.php` | Manually add a measurement row |
| Device location | `device_location.php` | Record when the device moved to a new location |
| User management | `admin_users.php` | Create/update users and roles |
| Delete measurements | `delete_measurements.php` | Filter and delete measurement rows (admin-only, POST-only, preview required before delete) |

### Delete measurements — safety flow

`delete_measurements.php` enforces a mandatory two-step flow:

1. **Set filters** (location, date range, mood) — at least one filter is required.
2. **Preview**: shows the count of matching rows; a server-side session token is issued.
3. **Confirm**: tick the checkbox and submit the delete form — the session token must match
   (prevents bypassing the preview via direct POST).
4. **Result**: the page shows the number of actually deleted rows.

No deletion is possible via GET requests or without completing the preview step.

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
- [ ] Tables `users`, `locations`, `measurements`, `sensor_hourly_aggregates`, `device_location_history` exist
- [ ] DB credentials in `db.local.php` are valid

### Device ingest checks

- [ ] `GET /stimmungsbarometer/device_ingest.php` returns JSON health
- [ ] `POST /stimmungsbarometer/device_ingest.php` with a live payload stores one row in `measurements`
- [ ] `POST /stimmungsbarometer/device_ingest.php` with an hourly sensor payload stores one row in `sensor_hourly_aggregates`
- [ ] Dashboard mood counts change only after a live payload
- [ ] Dashboard sensor values/charts change after an hourly sensor payload

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

### Raspberry Pi checks

- [ ] Exactly **one** `device.main` process is running (double instances cause duplicate counts):

  ```bash
  pgrep -af "python -m device.main"
  # must show exactly one line
  ```

  If two lines appear, kill all instances and restart cleanly:

  ```bash
  pkill -f "python -m device.main"
  sleep 2
  cd ~/Desktop/SIA_V2
  ./start_ui.sh
  pgrep -af "python -m device.main"   # expect exactly 1
  ```

- [ ] Upload endpoint reachable from Pi (uses `.env.device` settings):

  ```bash
  cd ~/Desktop/SIA_V2
  ./manual_upload_test.sh
  # expect HTTP 201 and {"status":"stored",...}
  ```

- [ ] No stuck pending uploads:

  ```bash
  cat ~/Desktop/SIA_V2/device/pending_uploads.json
  # normal: empty array [] or small number of entries that clear on next retry
  ```

- [ ] Log shows no abnormal retry spam:

  ```bash
  tail -n 40 ~/Desktop/SIA_V2/ui-autostart.log
  ```

For full Pi setup instructions see [`PI_SETUP.md`](PI_SETUP.md).

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
