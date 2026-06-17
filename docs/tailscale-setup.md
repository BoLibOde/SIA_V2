# Tailscale / Network Setup

This project uses [Tailscale](https://tailscale.com/) so the Raspberry Pi can reach the server
without port-forwarding or a public IP.

## 1. Install Tailscale on every machine

**Linux (Pi + server):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Windows / Mac:** download the installer from https://tailscale.com/download

All machines must be logged in to the **same Tailscale account / tailnet**.

## 2. Find the server's Tailscale IP

```bash
tailscale ip -4          # prints something like 100.x.y.z
# or use MagicDNS name:
tailscale status         # shows hostname e.g. "myserver"
```

## 3. Configure the device to reach the server

Edit `.env.device` on the Pi (copy from `.env.device.example` if it doesn't exist):

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
# then edit SIA_SERVER_URL with the real server address
```

Key variables:

| Variable             | Example value                              | Description                          |
|----------------------|--------------------------------------------|--------------------------------------|
| `SIA_SERVER_URL`     | `http://100.74.7.35`                       | Server base URL (no trailing slash)  |
| `SIA_UPLOAD_ENDPOINT`| `/stimmungsbarometer/device_ingest.php`    | Ingest path on the server            |
| `SIA_HEALTH_ENDPOINT`| `/stimmungsbarometer/device_ingest.php`    | Health check path (same endpoint)    |
| `SIA_DEVICE_TOKEN`   | *(your shared secret)*                     | Must match `device_ingest_token` in `db.local.php` |
| `SIA_DEVICE_ID`      | `pi-room-01`                               | Unique name for this Pi              |
| `SIA_SIMULATION`     | `false`                                    | Set to `true` for no-hardware dev    |
| `SIA_FULLSCREEN`     | `true`                                     | Set to `false` for windowed mode     |
| `SIA_UPLOAD_TIMEOUT` | `10`                                       | HTTP timeout in seconds              |

## 4. Production server stack

The server runs **PHP + nginx + php-fpm + MariaDB**.  There is no separate Python/FastAPI server
process in production.  The ingest endpoint is:

```
http://<server-ip>/stimmungsbarometer/device_ingest.php
```

## 5. Verify the connection

From the Pi:
```bash
# Tailscale reachability
ping 100.74.7.35

# PHP ingest health check
curl -i http://100.74.7.35/stimmungsbarometer/device_ingest.php
# Expected: {"status":"ok","service":"php-device-ingest"}

# Full upload test (requires .env.device to be set)
cd ~/Desktop/SIA_V2
./manual_upload_test.sh
```

## Troubleshooting

- **Can't reach server:** run `tailscale ping <server-ip>` – if it fails, check that both machines are in the same tailnet.
- **404 on ingest:** check that `SIA_UPLOAD_ENDPOINT` is `/stimmungsbarometer/device_ingest.php` (not just `/device_ingest.php`).
- **401 Unauthorized:** the `SIA_DEVICE_TOKEN` in `.env.device` does not match the `device_ingest_token` in `db.local.php` on the server.
- **422 Unprocessable:** no device location is configured for the current timestamp – set one via Admin → Gerätestandort.
- **UI freezes on startup:** pygame needs a display – set `SIA_FULLSCREEN=false` and ensure `DISPLAY=:0` on the Pi.
