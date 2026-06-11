# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Repository structure

```text
SIA_V2/
├── README.md
├── setup.sh
├── requirements-device.txt
├── requirements-server.txt
├── .github/workflows/
│   ├── ci.yml
│   └── deploy.yml
├── device/
│   ├── config.py           # All settings, overridable via env vars
│   ├── main.py             # Device entry point
│   ├── gpio_handler.py     # Button input + debounce
│   ├── sensor_service.py   # SCD41 sensor or simulation
│   ├── aggregation_service.py
│   ├── upload_service.py   # HTTP upload + retry
│   ├── ui.py               # Pygame display + status bar
│   ├── models.py
│   └── assets/
├── server/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py             # FastAPI app (CORS enabled)
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   └── routes/
├── docs/
└── tests/
```

## Voraussetzungen

### Python
- Python 3.11 oder neuer empfohlen
- optional ein virtuelles Environment (`python -m venv .venv`)

### Server
- PostgreSQL muss erreichbar sein
- `DATABASE_URL` muss gesetzt sein, z. B.:

```bash
export DATABASE_URL="******localhost:5432/sia_v2"
```

### Raspberry Pi / Device
- Raspberry Pi OS / Linux mit Python 3
- optional Sensor-/GPIO-Hardware
- für die Verbindung zum Server typischerweise Tailscale

## Server-Setup

```bash
cd /home/runner/work/SIA_V2/SIA_V2/BoLibOde/SIA_V2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
export DATABASE_URL="******localhost:5432/sia_v2"
```

Weiterführende Doku:
- [`docs/api.md`](docs/api.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md)
- [`docs/deployment_tailscale.md`](docs/deployment_tailscale.md)

## Server starten

Entwicklungsstart mit Reload:

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Start ohne Reload:

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Danach erreichbar unter:
- Root: `http://localhost:8000/`
- Health: `http://localhost:8000/api/v1/health`
- API-Doku: `http://localhost:8000/docs`

## Raspberry-Pi-/Device-Setup

Mit dem vorhandenen Setup-Skript:

```bash
chmod +x setup.sh
./setup.sh
```

Oder manuell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-device.txt
```

Beispiel für die Server-URL des Devices:

```bash
export SIA_SERVER_URL="http://100.x.y.z:8000"
```

## Hauptprogramm auf dem Raspberry Pi starten

```bash
cd /home/pi/Desktop/SIA_V2
source .venv/bin/activate
export SIA_SERVER_URL="http://100.x.y.z:8000"
python -m device.main
```

## Hauptprogramm lokal ohne Hardware / im Simulationsmodus starten

```bash
cd /home/runner/work/SIA_V2/SIA_V2/BoLibOde/SIA_V2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-device.txt
export SIA_SERVER_URL="http://localhost:8000"
export SIA_SIMULATION=true
export SIA_FULLSCREEN=false
python -m device.main
```

## Tests ausführen

Server-Testabhängigkeiten installieren:

```bash
pip install -r requirements-server.txt
```

Tests starten:

```bash
pytest
pytest -v
pytest tests/test_health.py
```

## Kurzcheck für manuelle Prüfung

- Server startet ohne Fehler mit gesetzter `DATABASE_URL`
- `GET /` liefert Status `ok` und Service `sia-v2-api`
- `GET /api/v1/health` liefert Status `ok` und einen `timestamp`
- `http://localhost:8000/docs` ist erreichbar
- Device erreicht den Server mit gesetzter `SIA_SERVER_URL`
- Simulationsmodus startet lokal ohne Hardware mit `SIA_SIMULATION=true`

## Weitere Dokumentation

- [`docs/api.md`](docs/api.md) – API-Referenz
- [`docs/architecture.md`](docs/architecture.md) – Architekturüberblick
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md) – Tailscale-Einrichtung
- [`docs/deployment_tailscale.md`](docs/deployment_tailscale.md) – Deployment mit systemd/Tailscale
