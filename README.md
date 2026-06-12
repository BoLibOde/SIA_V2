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
│   ├── gpio_handler.py     # Button input + debounce (polling-based)
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
├── scripts/
│   ├── start_client.sh     # Auto-install deps and start device
│   ├── start_server.sh     # Start server
│   └── run_device.sh       # Stop service, then run device manually (Pi)
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
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/sia_v2"
```

### Raspberry Pi / Device
- Raspberry Pi OS / Linux mit Python 3
- optional Sensor-/GPIO-Hardware
- für die Verbindung zum Server typischerweise Tailscale

## Server-Setup

```bash
cd ~/SIA_web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/sia_v2"
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
- Root: `http://100.74.7.35:8000/`
- Health: `http://100.74.7.35:8000/api/v1/health`
- API-Doku: `http://100.74.7.35:8000/docs`

## Raspberry-Pi-/Device-Setup

Mit dem vorhandenen Setup-Skript:

```bash
chmod +x setup.sh
./setup.sh
```

Oder manuell:

```bash
cd /home/ebm/Desktop/SIA_V2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-device.txt
```

## Device auf dem Raspberry Pi starten (manuell / für Tests)

> **Hinweis:** Falls das Device als systemd-Dienst läuft, diesen zuerst stoppen:
>
> ```bash
> sudo systemctl stop sia-device
> ```

Dann manuell starten:

```bash
cd /home/ebm/Desktop/SIA_V2
source .venv/bin/activate
export SIA_SERVER_URL="http://100.74.7.35:8000"
python -m device.main
```

Oder per Hilfsskript (stoppt den Dienst automatisch):

```bash
bash /home/ebm/Desktop/SIA_V2/scripts/run_device.sh
```

## Button-Belegung (BCM-Nummern)

| Funktion | BCM-Pin | Physischer Pin |
|----------|---------|----------------|
| Gut      | 27      | 13             |
| Neutral  | 22      | 15             |
| Schlecht | 17      | 11             |

Alle drei Pins sind als Eingänge mit internem Pull-up konfiguriert.
Ein Knopfdruck schließt den Pin auf GND (LOW-Signal).

Überschreiben via Umgebungsvariablen:

```bash
export SIA_GOOD_PIN=27
export SIA_NEUTRAL_PIN=22
export SIA_BAD_PIN=17
```

## Simulationsmodus (lokal, ohne Hardware)

```bash
cd /path/to/SIA_V2
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
- `http://100.74.7.35:8000/docs` ist erreichbar
- Device erreicht den Server mit gesetzter `SIA_SERVER_URL`
- Simulationsmodus startet lokal ohne Hardware mit `SIA_SIMULATION=true`

## Troubleshooting

### `RuntimeError: Failed to add edge detection` / GPIO add_event_detect schlägt fehl

Auf manchen Raspberry Pi 3 Model B Geräten schlägt `RPi.GPIO.add_event_detect()`
auf allen Pins fehl. Das Device verwendet daher **Polling** statt Interrupts:
In jedem Loop-Durchgang wird `gpio_handler.update()` aufgerufen, das HIGH→LOW-
Übergänge an den Button-Pins erkennt und Entprellung (`debounce`) intern umsetzt.
Der `bouncetime`-Parameter aus der alten Interrupt-Variante entfällt dadurch.

### Dienst läuft bereits / Fehlermeldung beim manuellen Start

Wenn das Device als systemd-Dienst (`sia-device`) konfiguriert ist, muss dieser
vor einem manuellen `python -m device.main` gestoppt werden:

```bash
sudo systemctl stop sia-device
```

## Weitere Dokumentation

- [`docs/api.md`](docs/api.md) – API-Referenz
- [`docs/architecture.md`](docs/architecture.md) – Architekturüberblick
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md) – Tailscale-Einrichtung
- [`docs/deployment_tailscale.md`](docs/deployment_tailscale.md) – Deployment mit systemd/Tailscale
