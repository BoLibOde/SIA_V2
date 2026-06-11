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
3. Once per hour the device builds an `HourlyUploadPayload` and POSTs it to the server.
4. Failed uploads are saved to `pending_uploads.json` and retried automatically.
5. The server stores each upload in PostgreSQL.
6. The website polls the summary/history endpoints to display charts and current status.

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
