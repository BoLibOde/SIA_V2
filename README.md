# SIA_V2

## Produktionsrealität (aktiver Pfad)

Dieses Repository enthält mehrere Implementierungen.  
**Der aktuell produktive Stack ist:**

- PHP-Anwendung (`/server/WEBSITE`)
- nginx
- php-fpm
- MariaDB (`stimmungsbarometer`)

Für eine vollständige Ubuntu-Server-Einrichtung siehe auch
[`docs/ubuntu-server-setup.md`](docs/ubuntu-server-setup.md). Dort ist auch klar dokumentiert,
dass produktiv **nginx + php-fpm + MariaDB** benötigt werden und **Apache nicht erforderlich** ist.

Das Produktions-Webroot auf dem Server ist typischerweise:

- `/var/www/html/stimmungsbarometer`

Die PHP-App liest/schreibt MariaDB-Tabellen, darunter:

- `users`
- `locations`
- `measurements`
- `sensor_hourly_aggregates`
- `device_location_history`

## Deploy-Verhalten in Produktion (Datenbanksicherheit)

Normale GitHub-Actions-Deploys aktualisieren nur die Website-Dateien und **setzen die produktive MariaDB-Datenbank nicht zurück und bauen sie nicht neu auf**.

- Live-Daten in Tabellen wie `locations`, `users`, `measurements`,
  `sensor_hourly_aggregates` und `device_location_history` müssen bei
  Standard-Deploys unverändert bleiben.
- `scripts/refresh_database.sh` ist ein destruktiver Reset-Helfer und darf nur
  manuell für explizite Bootstrap-/Recovery-Szenarien ausgeführt werden.

---

## Device-Ingest-Endpunkt für Raspberry Pi (Produktion)

In der PHP-App gibt es jetzt einen dedizierten Maschinenendpunkt:

- `server/WEBSITE/device_ingest.php`
- Beispiel für den deployten Pfad: `http://<host>/device_ingest.php`

### Verhalten

- `GET` liefert JSON-Health-Informationen (`200`).
- `POST` erwartet einen JSON-Payload.
- Es ist kein Browser-Session-Login erforderlich.
- Speichert **Live-Stimmungsereignisse** in `measurements`.
- Speichert **15-Minuten-Sensordurchschnitte** in `sensor_hourly_aggregates`.
- Nutzt `location_id` aus dem Payload, wenn vorhanden.
- Andernfalls wird `location_id` anhand des Payload-Zeitstempels über `device_location_history` aufgelöst (`created_at` für Live-Events, `period_end` für Sensor-Aggregat-Uploads).
- Gibt JSON und korrekte HTTP-Statuscodes zurück.

### Optionales Shared Secret (empfohlen)

Setze `device_ingest_token` in `server/WEBSITE/db.local.php` (siehe `db.local.example.php`) und sende es als:

- HTTP-Header: `X-Device-Token: <token>`
- (Fallback) JSON-Feld: `token`

Wenn konfiguriert und fehlend/ungültig, gibt der Endpunkt `401` zurück.

### Read-only-Endpunkt für heutige Zählerstände

Der Pi kann außerdem die maßgeblichen Stimmungszähler des aktuellen Tages lesen über:

- `server/WEBSITE/device_today_counts.php`
- Beispiel für den deployten Pfad: `http://<host>/device_today_counts.php?device_id=pi-room-01`

Verhalten:

- nur `GET`; keine Datenbankschreibvorgänge und keine Retry-Nebeneffekte
- liest ausschließlich aus `measurements`
- liefert die heutigen Zähler für `good` / `neutral` / `bad` für den aufgelösten Standort zurück
- akzeptiert `location_id` direkt oder löst den aktuellen Standort über `device_location_history` auf
- verwendet dasselbe optionale `X-Device-Token`-Modell wie `device_ingest.php`

### Unterstützte POST-JSON-Formate

1) Direktes Messformat:

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

2) Raspberry-Pi-Live-Stimmungsereignis-Format:

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

3) Raspberry-Pi-Payload-Format für 15-Minuten-Sensoraggregate (aus `device/upload_service.py`):

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

Sensor-Aggregat-Payloads erzeugen keine Stimmungsvotes. Das Intervall `period_end – period_start` beträgt
15 Minuten (Fenster: `HH:00–HH:15`, `HH:15–HH:30`, `HH:30–HH:45`, `HH:45–HH+1:00`).
Jedes abgeschlossene Fenster erzeugt höchstens eine gespeicherte Zeile (der Server erzwingt Eindeutigkeit über
`UNIQUE KEY (location_id, period_start, period_end)`; doppelte Übermittlungen erhalten `409`).
Für Multi-Device-Setups `location_id` explizit in den Payloads angeben.

---

## PHP-Datenbankkonfiguration (Produktion)

Hauptkonfigurationsdatei:

- `server/WEBSITE/db.php`

Lokale Override-Datei — **nur serverlokal, nie committen**:

- `server/WEBSITE/db.local.php`

Diese Datei ist in `.gitignore` aufgeführt und von allen Deploys ausgeschlossen.
Kopiere das Beispiel, um sie auf einem neuen Server anzulegen:

```bash
cp server/WEBSITE/db.local.example.php /var/www/html/stimmungsbarometer/db.local.php
# anschließend mit echten Zugangsdaten und Token bearbeiten
```

Beispiel (`db.local.example.php`):

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

## Raspberry-Pi-Runtime-/Deploy-Hygiene

Für Desktop-Autostart auf dem Raspberry Pi und lokales Secret-Handling siehe [`PI_SETUP.md`](PI_SETUP.md).

Schnellstart:

```bash
cp .env.device.example .env.device
./manual_upload_test.sh
./start_ui.sh
```

---

## Startup-Menü – Modus + Sensor-Fallback

Beim Programmstart erscheinen vor der Haupt-App **zwei sequenzielle Menüs**:

1. **Betriebsmodus wählen**: Online / Offline
2. **Sensor-Strategie wählen**:
   - **Echte Sensoren** (Standard, kein Fallback)
   - **Mit Simulation** (Fallback nur wenn Hardware ausfällt)

### 3 Betriebszustände

| Zustand | Anzeige | Server |
|---|---|---|
| **Online mit Server** | `Modus: Online \| Server: verbunden` | ✅ Verbunden |
| **Online ohne Server** | `Modus: Online \| Server: offline (lokal gepuffert)` | Retry-Buffer aktiv |
| **Offline-Modus** | `Modus: Offline (Lokal)` | ⛔ Kein Server |

### Button-Belegung im Startup-Menü

#### Menü 1: Betriebsmodus

| Taste / Button | Aktion |
|---|---|
| **GUT-Button** | Online-Modus wählen |
| **NEUTRAL-Button** | Offline-Modus wählen |
| **SCHLECHT-Button** | Offline-Modus wählen |
| Tastatur **O** oder **Enter** | Online-Modus wählen |
| Tastatur **F** | Offline-Modus wählen |
| Tastatur **ESC** | Im Menü bleiben (wiederholen) |

#### Menü 2: Simulation/Fallback

| Taste / Button | Aktion |
|---|---|
| **GUT-Button** | Echte Sensoren (kein Fallback) |
| **NEUTRAL-Button** | Mit Simulation (Fallback bei Sensor-Ausfall) |
| **SCHLECHT-Button** | Mit Simulation (Fallback bei Sensor-Ausfall) |
| Tastatur **E** oder **Enter** | Echte Sensoren |
| Tastatur **M** oder **S** | Mit Simulation |
| Tastatur **ESC** | Zurück zu Menü 1 |

### Offline-Betrieb (z. B. Messe)

Im Offline-Modus werden Stimmungszähler des aktuellen Tages lokal in `device/tagesgesamt.json` gespeichert.
Bei Mitternacht werden die Zähler automatisch zurückgesetzt. Sensor-Werte werden nur live angezeigt.

Vollständige Dokumentation: [`OFFLINE_MODE.md`](OFFLINE_MODE.md)

### Modus per Umgebungsvariable erzwingen (headless)

```bash
export SIA_OPERATING_MODE=offline   # Offline-Modus, kein Startup-Menü
export SIA_OPERATING_MODE=online    # Online-Modus, kein Startup-Menü (Standard)
export SIA_ENABLE_SIMULATION_FALLBACK=false  # Standard: echte Sensoren bevorzugen
```

### Sensorstatus in der UI

Die Statusleiste unterscheidet jetzt klar zwischen:

- `Sensoren: OK | CO2: ... ppm` (Sensordaten vorhanden)
- `Sensoren: ⚠ Fehler` (keine Sensordaten verfügbar)

**Wichtig:** Simulation wird absichtlich **nicht** als eigener UI-Status angezeigt.
Bei aktivem Fallback laufen nur zusätzliche Logs (z. B. I2C-Bus-Erkennung, Recovery).

### Aktuell empfohlenes Runtime-Modell

Die Raspberry-Pi-UI sollte als **Desktop-Anwendung** laufen, die über den Desktop-Autostart gestartet wird.
`device.main` darf **nicht** gleichzeitig ein zweites Mal über `systemd` laufen.

- Es darf genau **ein** laufender Prozess `python -m device.main` existieren.
- Für den Start `./start_ui.sh`, für Neustarts `./restart_ui.sh` und für Deploy/Update `./update_pi.sh` verwenden.
- Desktop-Autostart ist der bevorzugte Weg, wenn die UI auf dem Pi-Display sichtbar sein muss.
- Ein paralleler `systemd`-Service für `device.main` kann doppelte Uploads und aufgeblähte Dashboard-Zähler verursachen.
- `start_ui.sh` hat einen Schutz vor Doppelstarts und kann statt eines zweiten Starts einen Skip protokollieren.

### Sauberer Neustart auf dem Pi

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

### Wenn veraltete Pending-Uploads bewusst verworfen werden sollen

```bash
printf '[]\n' > ~/Desktop/SIA_V2/device/pending_uploads.json
```

Das nur tun, wenn alte gepufferte Uploads ausdrücklich verworfen statt erneut versucht werden sollen.

---

## Raspberry-Pi-Upload-Konfiguration

Die Device-Defaults in `device/config.py` zeigen jetzt auf den PHP-Ingest-Pfad:

- `SIA_SERVER_URL` Standard: `http://100.74.7.35`
- `SIA_UPLOAD_ENDPOINT` Standard: `/device_ingest.php`
- `SIA_HEALTH_ENDPOINT` Standard: `/device_ingest.php`
- `SIA_TODAY_COUNTS_ENDPOINT` Standard: `/device_today_counts.php`
- `SIA_DEVICE_TOKEN` optional (wird als `X-Device-Token` gesendet)

Beispiel für Overrides:

```bash
export SIA_SERVER_URL="http://YOUR_HOST"
export SIA_UPLOAD_ENDPOINT="/device_ingest.php"
export SIA_HEALTH_ENDPOINT="/device_ingest.php"
export SIA_TODAY_COUNTS_ENDPOINT="/device_today_counts.php"
export SIA_DEVICE_TOKEN="CHANGE_ME_DEVICE_TOKEN"
python -m device.main
```

Die Pi-UI nutzt die Server-Zähler als Basiswert und wendet im Speicher optimistische
Pending-Deltas für lokale Tastendrücke an. Ein Wert wie `12*` bedeutet, dass die UI
lokal eine ausstehende Erhöhung anzeigt, die noch nicht mit dem maßgeblichen
Server-Zähler abgeglichen wurde.

---

## Admin-Funktionen (produktive PHP-App)

Alle Admin-Seiten sind über den **Admin-Bereich** zugänglich (`/admin.php` oder die entsprechend
deployte URL, z. B. `http://<host>/stimmungsbarometer/admin.php`).  
Ein Admin-Login ist erforderlich; Nicht-Admin-Benutzer werden zum Dashboard weitergeleitet.

| Seite | Pfad | Beschreibung |
|---|---|---|
| Admin-Übersicht | `admin.php` | Navigationszentrale für alle Admin-Funktionen |
| Standorte verwalten | `admin_locations.php` | Standorte ansehen, bearbeiten, löschen |
| Standort hinzufügen | `add_location.php` | Einen neuen Standort anlegen |
| Messung hinzufügen | `add_measurement.php` | Manuell eine Messzeile hinzufügen |
| Gerätestandort | `device_location.php` | Festhalten, wann das Gerät an einen neuen Standort verschoben wurde |
| Benutzerverwaltung | `admin_users.php` | Benutzer und Rollen anlegen/aktualisieren |
| Messungen löschen | `delete_measurements.php` | Messzeilen filtern und löschen (nur Admin, nur POST, Vorschau vor dem Löschen erforderlich) |

### Messungen löschen — Sicherheitsablauf

`delete_measurements.php` erzwingt einen obligatorischen Zwei-Schritt-Ablauf:

1. **Filter setzen** (Standort, Datumsbereich, Stimmung) — mindestens ein Filter ist erforderlich.
2. **Vorschau**: zeigt die Anzahl passender Zeilen; ein serverseitiges Session-Token wird ausgestellt.
3. **Bestätigen**: Checkbox aktivieren und das Löschformular absenden — das Session-Token muss übereinstimmen
   (verhindert das Umgehen der Vorschau per direktem POST).
4. **Ergebnis**: Die Seite zeigt die Anzahl der tatsächlich gelöschten Zeilen.

Löschen ist weder per GET noch ohne abgeschlossenen Vorschau-Schritt möglich.

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
7. Deaktivieren bekannter Test-Standorte
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

## Betriebliche Checkliste (Produktion)

### Services

- [ ] MariaDB läuft
- [ ] nginx läuft
- [ ] php-fpm läuft

### Erreichbarkeit der Web-App

- [ ] `http://127.0.0.1/login.php` liefert eine Seite (oder das erwartete Redirect-/Auth-Verhalten)
- [ ] `http://127.0.0.1/dashboard.php` ist nach dem Login erreichbar

### MariaDB-Prüfungen

- [ ] Datenbank `stimmungsbarometer` existiert
- [ ] Tabellen `users`, `locations`, `measurements`, `sensor_hourly_aggregates`, `device_location_history` existieren
- [ ] DB-Zugangsdaten in `db.local.php` sind gültig

### Prüfungen für Device-Ingest

- [ ] `GET /device_ingest.php` liefert JSON-Health zurück
- [ ] `POST /device_ingest.php` mit einem Live-Payload speichert eine Zeile in `measurements`
- [ ] `POST /device_ingest.php` mit einem stündlichen Sensor-Payload speichert eine Zeile in `sensor_hourly_aggregates`
- [ ] Dashboard-Stimmungszähler ändern sich nur nach einem Live-Payload
- [ ] Dashboard-Sensorwerte/-Charts ändern sich nach einem stündlichen Sensor-Payload

Beispiel-Test-POST:

```bash
curl -i -X POST "http://127.0.0.1/device_ingest.php"   -H "Content-Type: application/json"   -H "X-Device-Token: CHANGE_ME_DEVICE_TOKEN"   -d '{
    "mood":"neutral",
    "co2":620,
    "humidity":41.7,
    "temperature":21.8,
    "created_at":"2026-06-16T19:00:00+02:00"
  }'
```

### Raspberry-Pi-Prüfungen

- [ ] Genau **ein** `device.main`-Prozess läuft (Doppelinstanzen verursachen doppelte Zähler):

  ```bash
  pgrep -af "python -m device.main"
  # muss genau eine Zeile zeigen
  ```

- [ ] Die Pi-UI wird über Desktop-Autostart gestartet, nicht über einen zweiten parallelen `systemd`-`device.main`-Service.

- [ ] Upload-Endpunkt ist vom Pi erreichbar (verwendet Einstellungen aus `.env.device`):

  ```bash
  cd ~/Desktop/SIA_V2
  ./manual_upload_test.sh
  # erwartet HTTP 201 und {"status":"stored",...}
  ```

- [ ] Read-only-Endpunkt für heutige Zähler ist vom Pi erreichbar:

  ```bash
  curl -i     -H "X-Device-Token: CHANGE_ME_DEVICE_TOKEN"     "http://YOUR_HOST/device_today_counts.php?device_id=pi-room-01"
  # erwartet HTTP 200 und JSON mit status/date/timezone/location_id/device_id/counts/total
  ```

- [ ] Keine festhängenden Pending-Uploads:

  ```bash
  cat ~/Desktop/SIA_V2/device/pending_uploads.json
  # normal: leeres Array [] oder kleine Anzahl von Einträgen, die beim nächsten Retry verschwinden
  ```

- [ ] Log zeigt keinen auffälligen Retry-Spam:

  ```bash
  tail -n 40 ~/Desktop/SIA_V2/ui-autostart.log
  ```

Für vollständige Pi-Setup-Anweisungen siehe [`PI_SETUP.md`](PI_SETUP.md).

---

## Troubleshooting (Pi-Betrieb)

### Auf doppelte Prozesse prüfen (häufigste Ursache für doppelte Uploads / aufgeblähte Zähler)

```bash
pgrep -af "python -m device.main"
```

**Es darf genau eine Zeile erscheinen.** Wenn zwei oder mehr erscheinen, einen Neustart per Hilfsskript ausführen:

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

### Live-Logs prüfen

```bash
tail -n 100 ~/Desktop/SIA_V2/ui-autostart.log
tail -f ~/Desktop/SIA_V2/ui-autostart.log
```

Normale Ausgabe: Sensorwerte, erfolgreiche Upload-Meldungen.  
Warnsignal: `Retry: 0 gesendet, N offen` wiederholt sich ohne Unterbrechung → Netzwerk- oder Endpunktproblem.

### Retry-Puffer prüfen

```bash
cat ~/Desktop/SIA_V2/device/pending_uploads.json
```

Eine große oder wachsende Datei bedeutet, dass Uploads fehlschlagen.  
Prüfe, ob `.env.device` korrekt ist und der Server erreichbar ist.
Wenn du veraltete gepufferte Uploads bewusst verwerfen willst, zuerst die App stoppen und dann die Datei zurücksetzen:

```bash
pkill -f "python -m device.main"
printf '[]\n' > ~/Desktop/SIA_V2/device/pending_uploads.json
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

### Prüfen, ob `.env.device` vollständig ist

```bash
cat ~/Desktop/SIA_V2/.env.device
```

Erforderliche Schlüssel: `SIA_SERVER_URL`, `SIA_UPLOAD_ENDPOINT`, `SIA_HEALTH_ENDPOINT`, `SIA_DEVICE_TOKEN`, `SIA_DEVICE_ID`.  
`SIA_SIMULATION` muss fehlen oder `false` sein, wenn echte Hardware angeschlossen ist.

Korrekte Endpunkt-Pfade:

```
SIA_UPLOAD_ENDPOINT=/device_ingest.php
SIA_HEALTH_ENDPOINT=/device_ingest.php
```

### Manueller Upload-Test

```bash
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

Erwartet: HTTP `201 Created` mit `{"status":"stored",...}`.

### GPIO-/Button-Prüfung

```bash
raspi-gpio get 17   # bad button
raspi-gpio get 22   # neutral button
raspi-gpio get 27   # good button
```

Ein stabiles `level=1` im Ruhezustand (Pull-up aktiv) ist korrekt.  
Instabil oder dauerhaft `level=0` ohne Tastendruck → Verkabelung, Pull-up-Widerstand und gemeinsame Masse prüfen.

### I2C-/CO₂-Sensor-Prüfung

```bash
i2cdetect -y 0      # Raspberry Pi je nach Modell/Config: Bus 0 oder 1 prüfen
i2cdetect -y 1      # sollte Gerät bei 0x62 (SCD41) zeigen
dmesg | grep -i i2c
```

Die Device-App erkennt den SCD41-I2C-Bus automatisch (Bus 0/1) und loggt bei Fehlern
den probierten Bus inkl. Hinweis zur Verkabelung.

---

## Python/FastAPI-Code in diesem Repository (alternativer/nicht-produktiver Pfad)

Das Repository enthält weiterhin:

- Python-Device-Anwendung (`/device`)
- FastAPI-Backend (`/server/main.py`, `/server/routes`, SQLAlchemy-Modelle)

Das ist nützlich für Entwicklung/Experimente und bleibt im Repository, ist aber **nicht der aktuell aktive Produktions-Deploy-Pfad**, der oben beschrieben ist.

---

## Tests

```bash
pip install -r requirements-server.txt
pytest
```
