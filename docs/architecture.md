# Architecture Overview

## Production stack (active)

```
Raspberry Pi (device/)          Server (server/WEBSITE/)     Browser
┌──────────────────┐            ┌──────────────────────┐    ┌──────────────┐
│  GPIO buttons    │            │  PHP app (nginx +    │    │  dashboard   │
│  SCD41 sensor    │──HTTP──▶  │  php-fpm)            │◀──│  admin       │
│  Pygame UI       │            │  MariaDB             │    │  login       │
└──────────────────┘            └──────────────────────┘    └──────────────┘
        │
   Tailscale VPN
        │
   ─────▶ server (100.74.7.35)
```

## Data flow (production)

1. GPIO buttons on the device increment local mood counters; SCD41 sensor is read periodically.
2. Once per hour the device sends an aggregated payload (`mood_counts`, `sensor_avg`) to `device_ingest.php`.
   Each button press also triggers an immediate live-event upload via the same endpoint.
3. `device_ingest.php` writes one row per upload into `measurements` (MariaDB).
4. The dashboard reads directly from `measurements` via `dashboard_data_service.php`.
5. Failed uploads are buffered locally in `device/pending_uploads.json` and retried automatically.

> **Note on double-counting:** The device sends both live-events (one per button press) and hourly
> aggregates.  Both write to the same `measurements` table without de-duplication, which causes the
> dashboard to count each press twice.  Keep this in mind when interpreting counts.

## Architecture decision: SQL over JSON

- MariaDB / SQL is the authoritative data store for SIA V2.
- JSON (`pending_uploads.json`) is only a local retry buffer for offline/failed uploads.
- Aggregation, filtering and historical views are handled server-side by PHP/SQL.

## Directory layout

```
SIA_V2/
├── device/                   # Runs on Raspberry Pi
│   ├── config.py             # All config – overrideable via env vars
│   ├── main.py               # Entry point, main loop
│   ├── gpio_handler.py       # Button input + debounce
│   ├── sensor_service.py     # SCD41 sensor (or simulation)
│   ├── aggregation_service.py# Builds hourly payload
│   ├── upload_service.py     # HTTP upload + retry buffer
│   ├── ui.py                 # Pygame display
│   └── models.py             # Dataclasses shared inside device/
│
├── server/
│   ├── WEBSITE/              # ★ PRODUCTION – PHP app served by nginx + php-fpm
│   │   ├── device_ingest.php # POST endpoint for the Pi (writes measurements)
│   │   ├── dashboard.php     # Dashboard UI
│   │   ├── dashboard_data.php / dashboard_data_service.php
│   │   ├── admin*.php        # Admin pages (locations, users, manual measurements)
│   │   ├── db.php            # DB config loader
│   │   └── db.local.php      # Server-local credentials (never committed)
│   │
│   ├── main.py               # FastAPI app (alternate/dev – see below)
│   ├── routes/               # FastAPI routes (alternate/dev)
│   └── stimmungsbarometer.sql# MariaDB schema + sample data
│
└── docs/
    ├── architecture.md       # This file
    ├── api.md                # Endpoint reference (PHP production + FastAPI alternate)
    ├── deployment_tailscale.md
    └── tailscale-setup.md
```

## Technology choices

| Layer   | Technology              | Role                                        |
|---------|-------------------------|---------------------------------------------|
| Device  | Python + Pygame         | Runs on Pi, UI without a browser            |
| Server  | PHP + nginx + php-fpm   | **Production** web app and ingest endpoint  |
| DB      | MariaDB (`stimmungsbarometer`) | **Production** data store             |
| Network | Tailscale               | VPN so Pi can reach the server              |
| Server (alt) | FastAPI + SQLAlchemy | Alternate/development path (not deployed) |
| DB (alt)| PostgreSQL              | Used only with the FastAPI alternate path   |

## Alternate / development path (non-production)

The repository also contains a Python/FastAPI backend (`server/main.py`, `server/routes/`) and
corresponding tests (`tests/`).  This code was the original prototype and is retained for
development and experimentation.  It is **not** deployed in production.

To run the FastAPI server locally:

```bash
pip install -r requirements-server.txt
uvicorn server.main:app --host 0.0.0.0 --port 8000
pytest
```
