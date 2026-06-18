# Tailscale- / Netzwerk-Setup

Dieses Projekt nutzt [Tailscale](https://tailscale.com/), damit der Raspberry Pi den Server
ohne Port-Forwarding oder öffentliche IP erreichen kann.

## 1. Tailscale auf jeder Maschine installieren

**Linux (Pi + Server):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Windows / Mac:** Installer von https://tailscale.com/download herunterladen

Alle Maschinen müssen im **gleichen Tailscale-Account / Tailnet** angemeldet sein.

## 2. Tailscale-IP des Servers finden

```bash
tailscale ip -4          # gibt etwas wie 100.x.y.z aus
# oder MagicDNS-Name verwenden:
tailscale status         # zeigt den Hostnamen, z. B. "myserver"
```

## 3. Device so konfigurieren, dass es den Server erreicht

`.env.device` auf dem Pi bearbeiten (aus `.env.device.example` kopieren, falls noch nicht vorhanden):

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
# danach SIA_SERVER_URL mit der echten Server-Adresse bearbeiten
```

Wichtige Variablen:

| Variable | Beispielwert | Beschreibung |
|----------|--------------|--------------|
| `SIA_SERVER_URL` | `http://100.74.7.35` | Basis-URL des Servers (ohne Slash am Ende) |
| `SIA_UPLOAD_ENDPOINT`| `/device_ingest.php` | Ingest-Pfad auf dem Server |
| `SIA_HEALTH_ENDPOINT`| `/device_ingest.php` | Pfad für den Health Check (derselbe Endpunkt) |
| `SIA_DEVICE_TOKEN` | *(dein Shared Secret)* | Muss `device_ingest_token` in `db.local.php` entsprechen |
| `SIA_DEVICE_ID` | `pi-room-01` | Eindeutiger Name für diesen Pi |
| `SIA_SIMULATION` | `false` | Für Entwicklung ohne Hardware auf `true` setzen |
| `SIA_FULLSCREEN` | `true` | Für Fenstermodus auf `false` setzen |
| `SIA_UPLOAD_TIMEOUT` | `10` | HTTP-Timeout in Sekunden |

## 4. Produktions-Server-Stack

Der Server läuft mit **PHP + nginx + php-fpm + MariaDB**. Es gibt in Produktion keinen separaten
Python-/FastAPI-Serverprozess. Der Ingest-Endpunkt ist:

```
http://<server-ip>/device_ingest.php
```

## 5. Verbindung prüfen

Vom Pi aus:
```bash
# Tailscale-Erreichbarkeit
ping 100.74.7.35

# PHP-Ingest-Health-Check
curl -i http://100.74.7.35/device_ingest.php
# Erwartet: {"status":"ok","service":"php-device-ingest"}

# Vollständiger Upload-Test (setzt konfigurierte .env.device voraus)
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

## Troubleshooting

- **Server nicht erreichbar:** `tailscale ping <server-ip>` ausführen – wenn das fehlschlägt, prüfen, ob beide Maschinen im selben Tailnet sind.
- **404 auf Ingest:** prüfen, ob `SIA_UPLOAD_ENDPOINT` auf `/device_ingest.php` steht und `SIA_SERVER_URL` auf den richtigen Host zeigt (das nginx-Root ist bereits das App-Verzeichnis).
- **401 Unauthorized:** `SIA_DEVICE_TOKEN` in `.env.device` stimmt nicht mit `device_ingest_token` in `db.local.php` auf dem Server überein.
- **422 Unprocessable:** Für den aktuellen Zeitstempel ist kein Gerätestandort konfiguriert – über Admin → Gerätestandort setzen.
- **UI friert beim Start ein:** pygame benötigt ein Display – `SIA_FULLSCREEN=false` setzen und sicherstellen, dass auf dem Pi `DISPLAY=:0` gilt.
