# SIA V2 – Deployment Guide

## Overview

| Device         | Tailscale IP    | Role                                         |
|----------------|-----------------|----------------------------------------------|
| Ubuntu server  | `100.74.7.35`   | PHP app (nginx + php-fpm) + MariaDB          |
| Raspberry Pi   | `100.66.41.59`  | Device client (Pygame UI + upload)           |

---

## 1. Ubuntu server setup (PHP + MariaDB)

### Prerequisites

```bash
sudo apt update
sudo apt install -y git nginx php-fpm php-mysql mariadb-server tailscale
```

### Clone the repository

```bash
cd /var/www/html
sudo git clone https://github.com/BoLibOde/SIA_V2.git stimmungsbarometer
sudo chown -R www-data:www-data stimmungsbarometer
```

### MariaDB setup

```bash
sudo mysql_secure_installation
sudo mysql -u root -p
```

In the MariaDB prompt:

```sql
CREATE DATABASE stimmungsbarometer CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'sia_web'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON stimmungsbarometer.* TO 'sia_web'@'localhost';
FLUSH PRIVILEGES;
\q
```

Import the schema:

```bash
sudo mysql -u root -p stimmungsbarometer < /var/www/html/stimmungsbarometer/server/stimmungsbarometer.sql
```

### PHP local config (credentials + device token)

```bash
cd /var/www/html/stimmungsbarometer/server/WEBSITE
cp db.local.example.php db.local.php
# edit db.local.php: set host, dbname, user, pass, timezone, device_ingest_token
sudo chown www-data:www-data db.local.php
sudo chmod 640 db.local.php
```

`db.local.php` is in `.gitignore` and must never be committed.

### nginx configuration

Point nginx to `server/WEBSITE/` as the document root. Example minimal config:

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

Then reload:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Verify

```bash
curl -i http://127.0.0.1/stimmungsbarometer/device_ingest.php
# Expected: {"status":"ok","service":"php-device-ingest"}
```

---

## 2. Raspberry Pi setup

### Initial setup

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

This clones the repo to `~/Desktop/SIA_V2`, creates `.venv`, and installs Python dependencies.

### Configure device environment

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
# edit .env.device: set SIA_SERVER_URL, SIA_DEVICE_TOKEN (must match server db.local.php)
```

### Desktop autostart

The Pi UI runs as a **desktop application** started via autostart (not systemd).  
This is required for pygame to access the display session.

Create `~/.config/autostart/sia.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=SIA UI
Exec=/home/ebm/Desktop/SIA_V2/start_ui.sh
Path=/home/ebm/Desktop/SIA_V2
```

`start_ui.sh` activates `.venv`, loads `.env.device`, and starts `python -m device.main`.
Logs are written to `ui-autostart.log` in the repo root.

### Verify

```bash
# Check only one process is running
pgrep -af "python -m device.main"

# Live logs
tail -f ~/Desktop/SIA_V2/ui-autostart.log

# Manual upload test
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

> **Important:** There must be exactly **one** `python -m device.main` process.  
> Multiple instances cause duplicate uploads (dashboard shows +2 per button press).  
> If you see two processes: `pkill -f "python -m device.main"` then restart with `./start_ui.sh`.

---

## 3. Update flow on the Pi

```bash
cd ~/Desktop/SIA_V2
./update_pi.sh
```

`update_pi.sh` fetches `origin/main`, fast-forwards, refreshes Python deps, and restarts the UI.

Manual restart only (no update):

```bash
./restart_ui.sh
pgrep -af "python -m device.main"
```

---

## 4. Viewing logs

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

| Symptom | Check |
|---------|-------|
| Pi can't reach server | `tailscale ping 100.74.7.35` – both devices must be in the same tailnet |
| 404 on ingest | Verify `SIA_UPLOAD_ENDPOINT=/stimmungsbarometer/device_ingest.php` in `.env.device` |
| 401 Unauthorized | `SIA_DEVICE_TOKEN` in `.env.device` must match `device_ingest_token` in `db.local.php` |
| 422 Unprocessable | No device location set for this timestamp – configure via Admin → Gerätestandort |
| Dashboard shows +2 per press | Two device.main processes running – kill duplicates and restart |
| Log fills with "Retry: 0 gesendet, N offen" | Network issue or wrong endpoint – check `.env.device` and server reachability |
| UI freezes on Pi startup | Pygame needs a display – verify desktop session is running |

---

## 6. FastAPI alternate path (not in production)

The repository contains a Python/FastAPI server (`server/main.py`, `server/routes/`) used
for local development and testing.  Run it with:

```bash
pip install -r requirements-server.txt
uvicorn server.main:app --host 0.0.0.0 --port 8000
pytest
```

This is **not** deployed on the production server.  See `docs/api.md` for endpoint details.
