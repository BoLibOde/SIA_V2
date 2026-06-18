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

## Production deploy behavior (database safety)

Normal GitHub Actions deploys update the website files only and **do not reset or
rebuild** the production MariaDB database.

- Live data in tables such as `locations`, `users`, `measurements`,
  `sensor_hourly_aggregates`, and `device_location_history` must remain untouched
  during standard deploys.
- `scripts/refresh_database.sh` is a destructive reset helper and must only be run
  manually for explicit bootstrap/recovery scenarios.

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
- Stores **15-minute sensor averages** in `sensor_hourly_aggregates`.
- Uses `location_id` from payload when provided.
- Otherwise resolves `location_id` from `device_location_history` by the payload timestamp (`created_at` for live events, `period_end` for sensor aggregate uploads).
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

3) Raspberry Pi 15-minute sensor aggregate payload format (from `device/upload_service.py`):

```json
{
  "upload_type": "sensor_hourly",
  "device_id": "pi-room-01",
  "period_start": "2026-06-16T18:45:00+02:00",
  "period_end": "2026-06-16T19:00:00+02:00",
  "sensor_avg": {
    "temperature_c": 21.6,
    "humidity_pct": 41.9,
    "co2_ppm": 618
  },
  "sample_count": 12
}
```

Sensor aggregate payloads do not create mood votes. The `period_end – period_start` interval is
15 minutes (windows: `HH:00–HH:15`, `HH:15–HH:30`, `HH:30–HH:45`, `HH:45–HH+1:00`).
Each completed window produces at most one stored row (server enforces uniqueness via
`UNIQUE KEY (location_id, period_start, period_end)`; duplicate submissions receive `409`).
For multi-device setups, include `location_id` explicitly in payloads.

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

### Current recommended runtime model

The Raspberry Pi UI should run as a **desktop application** started from desktop autostart.
Do **not** run a second `device.main` instance via `systemd` at the same time.

- Keep exactly **one** running `python -m device.main` process.
- Use `./start_ui.sh` for startup, `./restart_ui.sh` for restart, and `./update_pi.sh` for deploy/update.
- Desktop autostart is the preferred way when the UI must be visible on the Pi display.
- A parallel `systemd` service for `device.main` can cause duplicate uploads and inflated dashboard counts.
- `start_ui.sh` has duplicate-start protection and may log a skip instead of starting a second process.

### Clean restart on the Pi

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

### If stale pending uploads must be discarded intentionally

```bash
printf '[]\n' > ~/Desktop/SIA_V2/device/pending_uploads.json
```

Only do this if you explicitly want to drop old buffered uploads instead of retrying them.

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

## Produktionsdaten-Cleanup

Für bereits verfälschte Produktionsdaten gibt es zwei Hilfsdateien:

- `scripts/cleanup_production_data.sh`
- `scripts/cleanup_production_data.sql`

Der empfohlene Weg ist immer der Shell-Wrapper, weil er **vor dem Cleanup automatisch ein
vollständiges mysqldump-Backup** anlegt und danach das SQL-Skript ausführt.

### Ausführung auf dem Server

```bash
sudo bash scripts/cleanup_production_data.sh
```

### Was das Cleanup macht

1. Vollständiges Datenbank-Backup in `.db-backups/`
2. Zusätzliche Backup-Tabelle `measurements_backup_cleanup` in MariaDB
3. Löschen von physikalisch unmöglichen Sensorwerten
4. Löschen von Messungen mit Zukunfts-Timestamp
5. Löschen offensichtlicher Dummy-/Testwerte
6. Löschen von Messungen vor dem dokumentierten Produktionsstart
7. Deaktivieren bekannter Test-Locations
8. Neuberechnung von `sensor_hourly_aggregates`
9. Abschlusskontrolle per SQL-Selects

### Rollback

Falls das Ergebnis nicht korrekt ist, kann der vorherige Stand aus dem automatisch erzeugten
Dump wiederhergestellt werden:

```bash
sudo mysql stimmungsbarometer < .db-backups/pre_cleanup_YYYYMMDD_HHMMSS.sql
```

> Hinweis: `scripts/cleanup_production_data.sql` ist absichtlich für die produktive Datenbank
> `stimmungsbarometer` geschrieben und sollte nicht ohne vorheriges Backup direkt ausgeführt
> werden.

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

- [ ] The Pi UI is started from desktop autostart, not from a second parallel `systemd` device.main service.

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

## Troubleshooting (Pi operations)

### Check for duplicate processes (most common cause of duplicate uploads / inflated counts)

```bash
pgrep -af "python -m device.main"
```

**Expect exactly one line.** If two or more appear, do a helper-script restart:

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

### Check live logs

```bash
tail -n 100 ~/Desktop/SIA_V2/ui-autostart.log
tail -f ~/Desktop/SIA_V2/ui-autostart.log
```

Normal output: sensor readings, successful upload messages.  
Warning sign: `Retry: 0 gesendet, N offen` repeated without interruption → network or endpoint issue.

### Check the retry buffer

```bash
cat ~/Desktop/SIA_V2/device/pending_uploads.json
```

A large or growing file means uploads are failing.  
Verify `.env.device` is correct and the server is reachable.
If you intentionally want to discard stale buffered uploads, stop the app first and then reset the file:

```bash
pkill -f "python -m device.main"
printf '[]\n' > ~/Desktop/SIA_V2/device/pending_uploads.json
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

### Check `.env.device` is complete

```bash
cat ~/Desktop/SIA_V2/.env.device
```

Required keys: `SIA_SERVER_URL`, `SIA_UPLOAD_ENDPOINT`, `SIA_HEALTH_ENDPOINT`, `SIA_DEVICE_TOKEN`, `SIA_DEVICE_ID`.  
`SIA_SIMULATION` must be absent or `false` when real hardware is connected.

Correct endpoint paths:

```
SIA_UPLOAD_ENDPOINT=/stimmungsbarometer/device_ingest.php
SIA_HEALTH_ENDPOINT=/stimmungsbarometer/device_ingest.php
```

### Manual upload test

```bash
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

Expected: HTTP `201 Created` with `{"status":"stored",...}`.

### GPIO / button check

```bash
raspi-gpio get 17   # bad button
raspi-gpio get 22   # neutral button
raspi-gpio get 27   # good button
```

Stable `level=1` at rest (pull-up active) is correct.  
Unstable or permanently `level=0` without pressing → check wiring, pull-up resistor, common ground.

### I2C / CO₂ sensor check

```bash
i2cdetect -y 1      # should show device at 0x62 (SCD41)
dmesg | grep -i i2c
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
