# API-Referenz

## Produktionsendpunkt (PHP)

Der aktive produktive Ingest-Endpunkt ist Teil der PHP-App, die vom Server per nginx ausgeliefert wird.

### Health Check

**`GET /device_ingest.php`**

Liefert `200` mit JSON, wenn die PHP-App erreichbar ist.

```json
{ "status": "ok", "service": "php-device-ingest" }
```

---

### Ingest (Device → Server)

**`POST /device_ingest.php`**

Der Raspberry Pi sendet hierhin Daten nach jedem Tastendruck (Live-Event) und einmal pro
15-Minuten-Sensorfenster (Aggregat).

**Authentifizierung (optional, empfohlen)**

Das Shared Secret als HTTP-Header `X-Device-Token` senden.  
Das Token in `server/WEBSITE/db.local.php` als `device_ingest_token` konfigurieren.

**Unterstützte Request-Body-Formate**

1. Direkte Messung (einzelne Zeile):

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

2. Raspberry-Pi-15-Minuten-Sensoraggregat (aus `device/upload_service.py`):

```json
{
  "upload_type": "sensor_hourly",
  "device_id": "pi-room-01",
  "period_start": "2026-06-16T18:45:00+02:00",
  "period_end":   "2026-06-16T19:00:00+02:00",
  "sensor_avg": {
    "temperature_c": 21.6,
    "humidity_pct": 41.9,
    "co2_ppm": 618
  },
  "sample_count": 12
}
```

`location_id` wird aus `device_location_history` aufgelöst, wenn sie nicht mitgegeben wird.
Sensor-Aggregat-Uploads erzeugen keine Stimmungszeilen in `measurements`.

**Antwort 201** – Zeile gespeichert:

```json
{
  "status": "stored",
  "measurement_id": 42,
  "location_id": 1,
  "created_at": "2026-06-16 19:00:00"
}
```

**Antwort 400** – fehlende oder ungültige Felder.  
**Antwort 401** – fehlendes/ungültiges Token (nur wenn ein Token konfiguriert ist).  
**Antwort 422** – kein Gerätestandort für den angegebenen Zeitstempel konfiguriert.  
**Antwort 500** – Datenbankfehler.

---

### Heutige Stimmungszähler (Server → Device, Read-only)

**`GET /device_today_counts.php?device_id=pi-room-01`**

Liefert die maßgeblichen heutigen Stimmungszähler für den aktuellen Standort zurück.

- liest ausschließlich aus `measurements`
- schreibt nie in die Datenbank
- akzeptiert optional `location_id`
- löst andernfalls den Standort über `device_location_history` auf
- verwendet denselben optionalen `X-Device-Token`-Header wie `device_ingest.php`

**Antwort 200**

```json
{
  "status": "ok",
  "date": "2026-06-18",
  "timezone": "+02:00",
  "location_id": 1,
  "device_id": "pi-room-01",
  "counts": {
    "good": 12,
    "neutral": 4,
    "bad": 3
  },
  "total": 19
}
```

Tage mit Nullwerten liefern weiterhin `200` mit Nullwerten.

**Terminal-Prüfung auf dem Pi**

```bash
curl -i   -H "X-Device-Token: CHANGE_ME_DEVICE_TOKEN"   "http://YOUR_HOST/device_today_counts.php?device_id=pi-room-01"
```

---

### Dashboard-Daten

Das PHP-Dashboard liest direkt aus der MariaDB-Tabelle `measurements` über
`dashboard_data_service.php`. Es gibt keine separate JSON-API für das Dashboard;
es ist serverseitig gerendertes PHP.

Verfügbare Bereiche (Query-Parameter `range`): `tag`, `woche`, `monat`, `jahr`, `gesamt`.

---

## Alternativer / Entwicklungs-Endpunkt (FastAPI – nicht in Produktion)

Das Repository enthält ein FastAPI-Backend (`server/main.py`, `server/routes/`), das
ursprünglich der Prototyp war. Es ist in der aktuellen Produktionsumgebung **nicht deployt**.

Base-URL beim lokalen Betrieb: `http://localhost:8000`  
Interaktive Doku: `http://localhost:8000/docs`

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /api/v1/health` | Health Check |
| `POST /api/v1/ingest/hourly` | Hourly-Aggregat-Ingest |
| `GET /api/v1/devices/{id}/summary` | Stimmungs- + Sensorzusammenfassung |
| `GET /api/v1/summary/global` | Globale Zusammenfassung über alle Devices |
| `GET /api/v1/devices/{id}/history` | Time-Series-Historie |

Siehe die eingebettete Swagger-Doku (`/docs`) für vollständige Request-/Response-Schemas im lokalen Betrieb.
