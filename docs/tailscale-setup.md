# Tailscale / Prototype Setup

This project uses [Tailscale](https://tailscale.com/) so the Raspberry Pi can reach the server
without port-forwarding or a public IP.

## 1. Install Tailscale on every machine

**Linux (Pi + server):**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Windows / Mac server:** download the installer from https://tailscale.com/download

All machines must be logged in to the **same Tailscale account / tailnet**.

## 2. Find the server's Tailscale IP

```bash
tailscale ip -4          # prints something like 100.x.y.z
# or use MagicDNS name:
tailscale status         # shows hostname e.g. "myserver"
```

## 3. Configure the device to reach the server

Set the `SIA_SERVER_URL` environment variable before starting the device app:

```bash
export SIA_SERVER_URL="http://100.x.y.z:8000"
python -m device.main
```

Or add it to your systemd unit / `.env` file.

You can also change it in `device/config.py` directly as the default value.

## 4. Start the server

```bash
cd ~/Desktop/SIA_V2
source .venv/bin/activate
export DATABASE_URL="******localhost:5432/sia_v2"
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Using `--host 0.0.0.0` ensures the server listens on the Tailscale interface.

## 5. Verify the connection

From the Pi, run:
```bash
curl http://100.x.y.z:8000/api/v1/health
# Expected: {"status":"ok","timestamp":"..."}
```

## 6. Website access

The website teammate only needs Tailscale installed (or to be on the same tailnet).
Point the website's API base URL to `http://<server-tailscale-ip>:8000`.

## Environment variable reference

| Variable             | Default                        | Description                          |
|----------------------|--------------------------------|--------------------------------------|
| `SIA_SERVER_URL`     | `http://localhost:8000`        | Server base URL (Tailscale IP/name)  |
| `SIA_DEVICE_ID`      | `pi-room-01`                   | Unique name for this Pi              |
| `SIA_SIMULATION`     | `false`                        | Set to `true` for no-hardware dev    |
| `SIA_FULLSCREEN`     | `true`                         | Set to `false` for windowed mode     |
| `SIA_UPLOAD_TIMEOUT` | `10`                           | HTTP timeout in seconds              |
| `DATABASE_URL`       | `postgresql://postgres:...`    | Server DB connection string          |

## Troubleshooting

- **Can't reach server:** run `tailscale ping <server-ip>` – if it fails, check that both machines are in the same tailnet.
- **Port blocked:** make sure port 8000 is not blocked by a host firewall (`ufw allow 8000`).
- **Server not starting:** check `DATABASE_URL` is set and PostgreSQL is running.
- **UI freezes on startup:** pygame needs a display – set `SIA_FULLSCREEN=false` and `DISPLAY=:0` on the Pi.
