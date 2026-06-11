# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Repository structure

```text
SIA_V2/
├── README.md
├── setup.sh
├── requirements-device.txt
├── requirements-server.txt
├── device/
│   ├── config.py           # All settings, overridable via env vars
│   ├── main.py             # Entry point
│   ├── gpio_handler.py     # Button input + debounce
│   ├── sensor_service.py   # SCD41 sensor or simulation
│   ├── aggregation_service.py
│   ├── upload_service.py   # HTTP upload + retry
│   ├── ui.py               # Pygame display + status bar
│   ├── models.py
│   └── assets/
│       ├── bad.png
│       ├── bad.svg
│       ├── good.png
│       ├── good.svg
│       ├── meh.png
│       └── meh.svg
└── server/
    ├── __init__.py
    ├── db.py
    ├── main.py             # FastAPI app (CORS enabled)
    ├── models.py
    ├── schemas.py
    ├── services/
    │   └── summary_service.py   # Calculation logic
    └── routes/
        ├── __init__.py
        ├── health.py       # GET /api/v1/health
        ├── ingest.py       # POST /api/v1/ingest/hourly + /live
        ├── live.py         # Live dashboard endpoints
        ├── locations.py    # Device location history
        └── summary.py      # Summary + history endpoints
```

## Quick setup (Raspberry Pi)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Or locally:
```bash
chmod +x setup.sh && ./setup.sh
```

Start the device app:
```bash
export SIA_SERVER_URL="http://<server-tailscale-ip>:8000"
~/Desktop/SIA_V2/.venv/bin/python -m device.main
```

For development without hardware (simulated sensor, windowed mode):
```bash
export SIA_SIMULATION=true
export SIA_FULLSCREEN=false
python -m device.main
```

## Server setup

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-server.txt

export DATABASE_URL="******localhost:5432/sia_v2"
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs available at `http://localhost:8000/docs`.

## Backend data model

- `hourly_uploads` – historical base data (hourly rollups)
- `device_live_states` – latest live values + today counters for dashboard
- `device_locations` – location history with `valid_from` / `valid_to`

Location history keeps old data correct when a device moves between rooms.

## Key API endpoints

### Health

| Method | Path               | Description          |
|--------|--------------------|----------------------|
| GET    | `/api/v1/health`   | Server health check  |

### Ingest

| Method | Path                      | Description                      |
|--------|---------------------------|----------------------------------|
| POST   | `/api/v1/ingest/hourly`   | Device uploads hourly aggregate  |
| POST   | `/api/v1/ingest/live`     | Device pushes live state         |

### Live dashboard

| Method | Path                              | Description                  |
|--------|-----------------------------------|------------------------------|
| GET    | `/api/v1/live`                    | All devices live dashboard   |
| GET    | `/api/v1/devices/{id}/live`       | Single device live state     |
| GET    | `/api/v1/devices/{id}/today`      | Today's counts for a device  |

### Location history

| Method | Path                               | Description                         |
|--------|------------------------------------|-------------------------------------|
| POST   | `/api/v1/devices/{id}/location`    | Assign location with valid_from     |
| GET    | `/api/v1/devices/{id}/locations`   | Get location history                |

### Historical summary (for website)

| Method | Path                                    | Description                               |
|--------|-----------------------------------------|-------------------------------------------|
| GET    | `/api/v1/summary`                       | Flexible summary with filter + group_by   |
| GET    | `/api/v1/devices/{id}/summary`          | Per-device summary (legacy)               |
| GET    | `/api/v1/devices/{id}/history?hours=24` | Hourly history for charting               |

See [`docs/api.md`](docs/api.md) for full request/response details.

## Tailscale

The device connects to the server over Tailscale. See [`docs/tailscale-setup.md`](docs/tailscale-setup.md).

## Docs

- [`docs/architecture.md`](docs/architecture.md) – component overview and data flow
- [`docs/api.md`](docs/api.md) – API reference for the website teammate
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md) – Tailscale and prototype setup
