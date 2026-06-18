# Ubuntu-Server-Einrichtung

## Zielbild

Für den **produktiven** Server dieses Projekts werden benötigt:

- `git`
- `nginx`
- `php`
- `php-fpm`
- `php-mysql`
- `mariadb-server`
- `tailscale`

**Nicht erforderlich für Produktion:**

- `apache2` – dieses Projekt nutzt produktiv **nginx + php-fpm**, nicht Apache
- Python/FastAPI als Serverprozess – der Python-Stack im Repository ist nur für Entwicklung/Tests gedacht

**Optional, aber sinnvoll für Wartung/Entwicklung auf dem Server:**

- `python3`
- `python3-pip`
- `python3-venv`

Wenn Apache bereits installiert ist, sollte er nicht parallel Port 80 belegen:

```bash
sudo systemctl disable --now apache2
```

---

## 1. System aktualisieren

```bash
sudo apt update
sudo apt upgrade -y
```

---

## 2. Benötigte Pakete installieren

### Produktionspakete

```bash
sudo apt install -y \
  git \
  nginx \
  php \
  php-fpm \
  php-mysql \
  mariadb-server \
  tailscale
```

### Optionale Python-Pakete für lokale Tests / Wartung

```bash
sudo apt install -y python3 python3-pip python3-venv
```

---

## 3. Basis-Services aktivieren

PHP-FPM läuft versionsabhängig meist als `php8.x-fpm`. Verfügbare FPM-Dienste anzeigen mit:

```bash
systemctl list-unit-files | grep php | grep fpm
```

Dann den passenden Dienst aktivieren, z. B.:

```bash
sudo systemctl enable --now nginx
sudo systemctl enable --now php8.3-fpm
sudo systemctl enable --now mariadb
```

Prüfen:

```bash
systemctl status nginx --no-pager
systemctl status mariadb --no-pager
systemctl status php8.3-fpm --no-pager
```

> Den `php8.3-fpm`-Namen bei Bedarf durch die auf deinem Server installierte PHP-FPM-Version ersetzen.

---

## 4. Repository an den Zielort legen

Die Produktionsdoku in diesem Repository geht typischerweise von diesem Pfad aus:

- `/var/www/html/stimmungsbarometer`

Einrichtung:

```bash
cd /var/www/html
sudo git clone https://github.com/BoLibOde/SIA_V2.git stimmungsbarometer
sudo chown -R www-data:www-data /var/www/html/stimmungsbarometer
```

---

## 5. MariaDB absichern und Datenbank anlegen

Zuerst Grundabsicherung:

```bash
sudo mysql_secure_installation
```

Dann Datenbank und Benutzer anlegen:

```bash
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

---

## 6. Lokale PHP-Konfiguration anlegen

Die produktive PHP-App liest die DB-Zugangsdaten aus `server/WEBSITE/db.local.php`.

```bash
cd /var/www/html/stimmungsbarometer/server/WEBSITE
cp db.local.example.php db.local.php
sudo chown www-data:www-data db.local.php
sudo chmod 640 db.local.php
```

Danach `db.local.php` mit echten Werten befüllen:

- `host`
- `dbname`
- `user`
- `pass`
- `timezone`
- `device_ingest_token`

Wichtig:

- `db.local.php` ist **serverlokal**
- die Datei ist in `.gitignore`
- sie darf **niemals** committet werden

---

## 7. nginx für die PHP-App konfigurieren

Empfohlene Struktur:

- Webroot: `/var/www/html/stimmungsbarometer/server/WEBSITE`
- PHP-Ausführung über `php-fpm`

Beispielkonfiguration:

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/html/stimmungsbarometer/server/WEBSITE;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

Falls deine Distribution keinen generischen Socket `php-fpm.sock` bereitstellt, den versionsspezifischen Socket verwenden, z. B.:

```nginx
fastcgi_pass unix:/run/php/php8.3-fpm.sock;
```

Aktivieren und neu laden:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. Tailscale aktivieren

```bash
sudo tailscale up
tailscale ip -4
```

Der Raspberry Pi verwendet diese Adresse später als `SIA_SERVER_URL`.

---

## 9. Optional: Firewall öffnen

Wenn `ufw` verwendet wird:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 10. Funktion prüfen

### PHP-Endpunkt

```bash
curl -i http://127.0.0.1/device_ingest.php
```

Erwartet:

```json
{"status":"ok","service":"php-device-ingest"}
```

### MariaDB

```bash
mysql -u sia_web -p -D stimmungsbarometer -e "SHOW TABLES;"
```

### nginx / php-fpm / MariaDB

```bash
systemctl is-active nginx
systemctl is-active mariadb
systemctl is-active php8.3-fpm
```

---

## 11. Optional: Python-Umgebung für Entwicklung auf dem Server

Nur nötig, wenn du auf dem Ubuntu-Server auch den alternativen FastAPI-/Testpfad nutzen willst.

```bash
cd /var/www/html/stimmungsbarometer
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-server.txt
pytest
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Dieser Python-Server ist **nicht** der produktive Stack.

---

## Kurzantwort zu Apache / Python / MariaDB / nginx / PHP

- **MariaDB:** benötigt
- **nginx:** benötigt
- **PHP + php-fpm + php-mysql:** benötigt
- **Python:** nur optional für Entwicklung/Tests auf dem Server
- **Apache:** nicht benötigt; bei installierter Standardkonfiguration besser deaktivieren
