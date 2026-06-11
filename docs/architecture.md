# Architecture Overview

## Components

```
Raspberry Pi (device/)          Server (server/)          Website (teammate)
┌──────────────────┐            ┌─────────────────┐       ┌──────────────┐
│  GPIO buttons    │            │  FastAPI app    │       │  Frontend    │
│  SCD41 sensor    │──HTTP──▶  │  PostgreSQL DB  │◀─API─│  (any stack) │
│  Pygame UI       │            │  services/      │       └──────────────┘
└──────────────────┘            └─────────────────┘
        │
   Tailscale VPN
        │
   ─────▶ server
```

## Data flow

1. Buttons on the device increment local mood counters.
2. The SCD41 sensor is read every few seconds and buffered.
3. The device uploads raw hourly measurements and live-feed data to the server.
4. The server stores those uploads in PostgreSQL, which is the central source of truth.
5. Aggregation, filtering, history queries, and summaries are calculated server-side via SQL.
6. JSON files are optional only as a local retry/offline buffer on the device (for example `pending_uploads.json`).
7. The website polls the server endpoints to display charts, live status, and historical views.

## Architecture decision: SQL over JSON filters

- PostgreSQL / SQL is the primary business data system for SIA V2.
- Devices are intentionally kept simple: they collect button/sensor inputs and send raw data plus live-feed updates.
- The server is responsible for persistence, filtering, aggregation, and historical evaluation.
- JSON must not be treated as the main analytical data store; it is only acceptable as a temporary local retry buffer when the device is offline or an upload fails.

## Directory layout

```
SIA_V2/
├── device/               # Runs on Raspberry Pi
│   ├── config.py         # All config – can be overridden via env vars
│   ├── main.py           # Entry point, main loop
│   ├── gpio_handler.py   # Button input + debounce
│   ├── sensor_service.py # SCD41 sensor (or simulation)
│   ├── aggregation_service.py  # Builds hourly payload
│   ├── upload_service.py # HTTP upload + retry
│   ├── ui.py             # Pygame display
│   └── models.py         # Dataclasses shared inside device/
│
├── server/               # Runs on any machine reachable via Tailscale
│   ├── main.py           # FastAPI app, CORS, startup
│   ├── db.py             # SQLAlchemy engine / session
│   ├── models.py         # DB table definitions
│   ├── schemas.py        # Pydantic request/response models
│   ├── services/
│   │   └── summary_service.py  # Calculation logic
│   └── routes/
│       ├── health.py     # GET /api/v1/health
│       ├── ingest.py     # POST /api/v1/ingest/hourly
│       └── summary.py    # GET summary + history endpoints
│
└── docs/
    ├── architecture.md   # This file
    ├── api.md            # API reference for the website teammate
    └── tailscale-setup.md
```

## Technology choices

| Layer   | Technology          | Why                              |
|---------|---------------------|----------------------------------|
| Device  | Python + Pygame     | Runs on Pi, UI without a browser |
| Server  | FastAPI + SQLAlchemy| Fast to build, auto docs at /docs|
| DB      | PostgreSQL          | Simple, reliable                 |
| Network | Tailscale           | Zero-config VPN for prototype    |
