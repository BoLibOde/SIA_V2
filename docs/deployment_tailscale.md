# SIA V2 – Deployment-Anleitung

## Überblick

| Gerät | Tailscale-IP | Rolle |
|-------|--------------|-------|
| Ubuntu-Server | `100.74.7.35` | PHP-App (nginx + php-fpm) + MariaDB |
| Raspberry Pi | `100.66.41.59` | Device-Client (Pygame-UI + Upload) |

---

## 1. Ubuntu-Server-Setup (PHP + MariaDB)

Für eine **vollständige** Ubuntu-Server-Basisinstallation inklusive benötigter Pakete,
Apache-Hinweis, optionalem Python-Setup, Firewall und Verifikation siehe
[`ubuntu-server-setup.md`](ubuntu-server-setup.md).

### Voraussetzungen

```bash
sudo apt update
sudo apt install -y git nginx php-fpm php-mysql mariadb-server tailscale
```

### Repository klonen

```bash
cd /var/www/html
sudo git clone https://github.com/BoLibOde/SIA_V2.git stimmungsbarometer
sudo chown -R www-data:www-data stimmungsbarometer
```

### MariaDB-Setup

```bash
sudo mysql_secure_installation
sudo mysql -u root -p
```

Im MariaDB-Prompt:

```sql
CREATE DATABASE stimmungsbarometer CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'sia_web'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON stimmungsbarometer.* TO 'sia_web'@'localhost';
FLUSH PRIVILEGES;
\q
```

Schema importieren:

```bash
sudo mysql -u root -p stimmungsbarometer < /var/www/html/stimmungsbarometer/server/stimmungsbarometer.sql
```

### Lokale PHP-Konfiguration (Zugangsdaten + Device-Token)

```bash
cd /var/www/html/stimmungsbarometer/server/WEBSITE
cp db.local.example.php db.local.php
# db.local.php bearbeiten: host, dbname, user, pass, timezone, device_ingest_token setzen
sudo chown www-data:www-data db.local.php
sudo chmod 640 db.local.php
```

`db.local.php` steht in `.gitignore` und darf niemals committet werden.

### nginx-Konfiguration

nginx auf `server/WEBSITE/` als Document Root zeigen lassen. Minimales Beispiel:

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/html/stimmungsbarometer/server/WEBSITE;
    index index.php;

    location /stimmungsbarometer/ {
        alias /var/www/html/stimmungsbarometer/server/WEBSITE/;
        index index.php;
        location ~ \.php$ {
            fastcgi_pass unix:/run/php/php-fpm.sock;
            include fastcgi_params;
            fastcgi_param SCRIPT_FILENAME $request_filename;
        }
    }
}
```

Danach neu laden:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Verifizieren

```bash
curl -i http://127.0.0.1/stimmungsbarometer/device_ingest.php
# Erwartet: {"status":"ok","service":"php-device-ingest"}
```

---

## 2. Raspberry-Pi-Setup

### Initiales Setup

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Das klont das Repository nach `~/Desktop/SIA_V2`, erstellt `.venv` und installiert Python-Abhängigkeiten.

### Device-Umgebung konfigurieren

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
# .env.device bearbeiten: SIA_SERVER_URL, SIA_DEVICE_TOKEN setzen (muss zu server db.local.php passen)
```

### Desktop-Autostart

Die Pi-UI läuft als **Desktop-Anwendung**, die per Autostart gestartet wird (nicht per systemd).  
Das ist erforderlich, damit pygame auf die Display-Sitzung zugreifen kann.

`~/.config/autostart/sia.desktop` anlegen:

```ini
[Desktop Entry]
Type=Application
Name=SIA UI
Exec=/home/ebm/Desktop/SIA_V2/start_ui.sh
Path=/home/ebm/Desktop/SIA_V2
```

`start_ui.sh` aktiviert `.venv`, lädt `.env.device` und startet `python -m device.main`.
Logs werden im Repository-Root in `ui-autostart.log` geschrieben.

### Verifizieren

```bash
# Prüfen, dass nur ein Prozess läuft
pgrep -af "python -m device.main"

# Live-Logs
tail -f ~/Desktop/SIA_V2/ui-autostart.log

# Manueller Upload-Test
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

> **Wichtig:** Es darf genau **ein** `python -m device.main`-Prozess laufen.  
> Mehrere Instanzen verursachen doppelte Uploads (Dashboard zeigt +2 pro Tastendruck).  
> Wenn du zwei Prozesse siehst: `pkill -f "python -m device.main"`, dann mit `./start_ui.sh` neu starten.

---

## 3. Update-Ablauf auf dem Pi

```bash
cd ~/Desktop/SIA_V2
./update_pi.sh
```

`update_pi.sh` holt `origin/main`, führt einen Fast-Forward aus, aktualisiert Python-Abhängigkeiten und startet die UI neu.

Nur manueller Neustart (kein Update):

```bash
./restart_ui.sh
pgrep -af "python -m device.main"
```

---

## 4. Logs ansehen

### Server (nginx + PHP)

```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Raspberry Pi

```bash
tail -f ~/Desktop/SIA_V2/ui-autostart.log
```

---

## 5. Troubleshooting

| Symptom | Prüfung |
|---------|---------|
| Pi erreicht Server nicht | `tailscale ping 100.74.7.35` – beide Geräte müssen im selben Tailnet sein |
| 404 auf Ingest | Prüfen, ob `SIA_UPLOAD_ENDPOINT=/stimmungsbarometer/device_ingest.php` in `.env.device` gesetzt ist |
| 401 Unauthorized | `SIA_DEVICE_TOKEN` in `.env.device` muss `device_ingest_token` in `db.local.php` entsprechen |
| 422 Unprocessable | Kein Gerätestandort für diesen Zeitstempel gesetzt – über Admin → Gerätestandort konfigurieren |
| Dashboard zeigt +2 pro Tastendruck | Zwei `device.main`-Prozesse laufen – Duplikate beenden und neu starten |
| Log füllt sich mit "Retry: 0 gesendet, N offen" | Netzwerkproblem oder falscher Endpunkt – `.env.device` und Server-Erreichbarkeit prüfen |
| UI friert beim Pi-Start ein | Pygame benötigt ein Display – prüfen, ob die Desktop-Sitzung läuft |

---

## 6. FastAPI-Alternativpfad (nicht in Produktion)

Das Repository enthält einen Python/FastAPI-Server (`server/main.py`, `server/routes/`), der
für lokale Entwicklung und Tests verwendet wird. Starten mit:

```bash
pip install -r requirements-server.txt
uvicorn server.main:app --host 0.0.0.0 --port 8000
pytest
```

Dieser Pfad ist auf dem Produktionsserver **nicht** deployt. Siehe `docs/api.md` für Endpunktdetails.
