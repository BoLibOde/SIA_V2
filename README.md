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
├── server/
│   ├── main.py             # FastAPI app (CORS enabled)
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   └── summary_service.py   # Calculation logic
│   └── routes/
│       ├── health.py       # GET /api/v1/health
│       ├── ingest.py       # POST /api/v1/ingest/hourly
│       └── summary.py      # Summary + history endpoints
└── docs/
    ├── architecture.md
    ├── api.md              # API reference for website teammate
    └── tailscale-setup.md
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

## Key API endpoints

| Method | Path                                    | Description                        |
|--------|-----------------------------------------|------------------------------------|
| GET    | `/api/v1/health`                        | Server health check                |
| POST   | `/api/v1/ingest/hourly`                 | Device uploads hourly aggregate    |
| GET    | `/api/v1/devices/{id}/summary?range=day`| Mood summary for one device        |
| GET    | `/api/v1/summary/global?range=day`      | Summary across all devices         |
| GET    | `/api/v1/devices/{id}/history?hours=24` | Hourly history for charting        |

See [`docs/api.md`](docs/api.md) for full request/response details.

## Tailscale

The device connects to the server over Tailscale. See [`docs/tailscale-setup.md`](docs/tailscale-setup.md).

## Docs

- [`docs/architecture.md`](docs/architecture.md) – component overview and data flow
- [`docs/api.md`](docs/api.md) – API reference for the website teammate
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md) – Tailscale and prototype setup

