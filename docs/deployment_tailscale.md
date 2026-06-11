# SIA V2 – Deployment with Tailscale

This guide explains how to deploy the SIA V2 server on Ubuntu and the client on a Raspberry Pi,
connected over [Tailscale](https://tailscale.com/).

## Devices

| Device         | Tailscale IP    | Role                        |
|----------------|-----------------|-----------------------------|
| Ubuntu server  | `100.74.7.35`   | FastAPI + PostgreSQL server |
| Raspberry Pi   | `100.66.41.59`  | Device client (UI + upload) |

---

## 1. Ubuntu server setup

### Prerequisites

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip postgresql tailscale
```

### Clone the repository

```bash
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/BoLibOde/SIA_V2.git
sudo chown -R $USER:$USER /opt/SIA_V2
chmod +x /opt/SIA_V2/scripts/start_server.sh
```

### PostgreSQL setup

```bash
sudo -u postgres psql
```

In the psql prompt:

```sql
CREATE DATABASE sia_v2;
ALTER USER postgres WITH PASSWORD 'postgres';
\q
```

### Install the systemd service

```bash
# Replace 'ubuntu' if your user is different
sudo sed -i "s/^User=ubuntu/User=$(whoami)/" /opt/SIA_V2/deploy/sia-server.service
sudo sed -i "s/^Group=ubuntu/Group=$(whoami)/" /opt/SIA_V2/deploy/sia-server.service

sudo cp /opt/SIA_V2/deploy/sia-server.service /etc/systemd/system/sia-server.service
sudo systemctl daemon-reload
sudo systemctl enable sia-server.service
sudo systemctl start sia-server.service
sudo systemctl status sia-server.service
```

### Allow port 8000 (if ufw is active)

```bash
sudo ufw allow 8000
```

---

## 2. Raspberry Pi setup

### Clone / update the repository

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/BoLibOde/SIA_V2/main/setup.sh)
```

Or locally:

```bash
cd ~/Desktop/SIA_V2
git pull
chmod +x scripts/start_client.sh
```

### Install the systemd service

```bash
sudo cp ~/Desktop/SIA_V2/deploy/sia-client.service /etc/systemd/system/sia-client.service
sudo systemctl daemon-reload
sudo systemctl enable sia-client.service
sudo systemctl start sia-client.service
sudo systemctl status sia-client.service
```

> If your Pi user is **not** `pi`, edit `deploy/sia-client.service` and change `User=`, `Group=`,
> and the paths under `WorkingDirectory` / `ExecStart` before copying.

---

## 3. Tailscale connectivity tests

### From the Raspberry Pi → Ubuntu server

```bash
# 1. Ping test (Tailscale layer)
ping 100.74.7.35

# 2. Health check (FastAPI layer)
curl http://100.74.7.35:8000/api/v1/health
# Expected: {"status":"ok","timestamp":"..."}

# 3. API docs
curl http://100.74.7.35:8000/docs
```

### Test upload (from Pi or any machine with Python + requests)

```bash
cd ~/Desktop/SIA_V2
python3 scripts/test_upload.py
```

Expected output:

```
POST http://100.74.7.35:8000/api/v1/ingest/hourly
...
Status: 200
Body:   {"status":"ok","stored":true}

✓ Upload successful
```

---

## 4. Environment variable reference

All device settings can be overridden via environment variables without editing source files.

| Variable              | Default                      | Description                              |
|-----------------------|------------------------------|------------------------------------------|
| `SIA_SERVER_URL`      | `http://100.74.7.35:8000`    | Server base URL (Tailscale IP/hostname)  |
| `SIA_DEVICE_ID`       | `pi-room-01`                 | Unique name for this Pi                  |
| `SIA_SIMULATION`      | `false`                      | Set to `true` for no-hardware dev        |
| `SIA_FULLSCREEN`      | `true`                       | Set to `false` for windowed mode         |
| `SIA_UPLOAD_TIMEOUT`  | `10`                         | HTTP timeout in seconds                  |
| `DATABASE_URL`        | `******localhost:5432/sia_v2` | Server DB connection string |

---

## 5. Viewing logs

### Ubuntu server logs

```bash
journalctl -u sia-server.service -f
```

### Raspberry Pi client logs

```bash
journalctl -u sia-client.service -f
```

---

## 6. Troubleshooting

| Symptom | Check |
|---------|-------|
| Pi can't reach server | `tailscale ping 100.74.7.35` – both devices must be in the same tailnet |
| Port blocked | `sudo ufw allow 8000` on the Ubuntu server |
| Server not starting | Check `journalctl -u sia-server.service` and verify PostgreSQL is running |
| UI freezes on Pi startup | Make sure `DISPLAY=:0` and `XAUTHORITY` are set; check the service file |
| `409 Conflict` from test upload | Duplicate for that period – server is working; change `period_start` in the test script |
