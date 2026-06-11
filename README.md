# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Architektur in Kürze

- PostgreSQL / SQL ist die zentrale Source of Truth.
- Devices senden Rohdaten und Live-Feed an den Server.
- Speicherung, Filterung, Historie, Aggregation und Auswertung passieren serverseitig über SQL.
- JSON ist höchstens noch ein lokaler Retry-/Offline-Puffer auf dem Device, nicht das fachliche Hauptsystem.

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
└── server/
    ├── __init__.py
    ├── db.py
    ├── main.py
    ├── models.py
    ├── schemas.py
    ├── services/
    └── routes/
```

## Voraussetzungen

### Python
- Python 3.11 empfohlen für Server und CI
- Python 3.x auf dem Raspberry Pi / Device
- optional: virtuelles Environment (`.venv`)

### Datenbank
- PostgreSQL als zentrale relationale Datenbank
- `DATABASE_URL` muss auf die Server-Datenbank zeigen

Beispiel:

```bash
export DATABASE_URL="postgresql://<db-user>:<db-password>@localhost:5432/sia_v2"
```

## Server-Setup

```bash
cd /home/runner/work/SIA_V2/SIA_V2/BoLibOde/SIA_V2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
export DATABASE_URL="postgresql://<db-user>:<db-password>@localhost:5432/sia_v2"
```

## Server starten

### Entwicklung

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Ohne Reload

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Danach sind die wichtigsten Endpunkte erreichbar:

- Root: `http://localhost:8000/`
- Health: `http://localhost:8000/api/v1/health`
- API-Doku: `http://localhost:8000/docs`

## Raspberry-Pi- / Device-Setup

### Automatisch mit Setup-Skript

```bash
chmod +x setup.sh
./setup.sh
```

### Alternativ per Remote-Setup

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Vor dem Start mindestens die Server-URL setzen:

```bash
export SIA_SERVER_URL="http://localhost:8000"
```

Bei Nutzung über Tailnet stattdessen z. B.:

```bash
export SIA_SERVER_URL="http://100.74.7.35:8000"
```

## Hauptprogramm auf dem Raspberry Pi starten

```bash
python -m device.main
```

Das Device sendet nur Rohdaten und Live-Feed an den Server. Speicherung und Auswertung erfolgen serverseitig in PostgreSQL/SQL.

## Hauptprogramm lokal ohne Hardware / im Simulationsmodus starten

```bash
export SIA_SERVER_URL="http://localhost:8000"
export SIA_SIMULATION=true
export SIA_FULLSCREEN=false
python -m device.main
```

## Datenfluss

- Device sammelt Button- und Sensorwerte.
- Device lädt Rohdaten und Live-Feed zum Server hoch.
- Server speichert die Daten in PostgreSQL.
- Historie, Filterung und Aggregation laufen serverseitig per SQL.
- JSON-Dateien sind nur optional für lokale Retry-/Offline-Fälle gedacht.

## Tests ausführen

```bash
pytest
pytest -v
pytest tests/test_health.py
```

## Manuell prüfen

- Server startet mit gesetzter `DATABASE_URL` ohne Fehler.
- `GET /` liefert `status=ok` und `service=sia-v2-api`.
- `GET /api/v1/health` liefert `status=ok` und einen Timestamp.
- `http://localhost:8000/docs` ist erreichbar.
- Device kann mit gesetzter `SIA_SERVER_URL` starten.
- Simulationsmodus funktioniert mit `SIA_SIMULATION=true`.

## Weiterführende Dokumentation

- [`docs/api.md`](docs/api.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/tailscale-setup.md`](docs/tailscale-setup.md)
- [`docs/deployment_tailscale.md`](docs/deployment_tailscale.md)
