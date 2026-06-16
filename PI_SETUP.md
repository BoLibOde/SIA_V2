# Raspberry Pi UI runtime + device secret handling

The Raspberry Pi UI is launched from the desktop session (autostart entry), not a systemd service.
Use the repository root helper scripts below.

## 1) Create local device env file

```bash
cd ~/Desktop/SIA_V2
cp .env.device.example .env.device
```

`.env.device` is **local-only** and contains secrets (`SIA_DEVICE_TOKEN`).
Do not commit it.

Current example defaults:

- `SIA_SERVER_URL=http://100.74.7.35` (placeholder, environment-specific; set this to the server address your Pi can reach, e.g. Tailscale IP, LAN IP, or DNS name)
- `SIA_UPLOAD_ENDPOINT=/device_ingest.php`
- `SIA_HEALTH_ENDPOINT=/device_ingest.php`

## 2) Manual upload test

```bash
cd ~/Desktop/SIA_V2
chmod +x manual_upload_test.sh
./manual_upload_test.sh
```

This sends one POST request to `${SIA_SERVER_URL}${SIA_UPLOAD_ENDPOINT}` with `X-Device-Token` and a current timestamp.

## 3) Start the UI runtime script

```bash
cd ~/Desktop/SIA_V2
chmod +x start_ui.sh
./start_ui.sh
```

`start_ui.sh`:

- activates `.venv`
- loads `.env.device`
- exports `SIA_SERVER_URL`, `SIA_UPLOAD_ENDPOINT`, `SIA_HEALTH_ENDPOINT`, `SIA_DEVICE_TOKEN`, `SIA_DEVICE_ID`
- starts `python -m device.main`
- writes app output to `ui-autostart.log`

## 4) Desktop autostart

Point the desktop autostart entry to this script:

```ini
Exec=/home/<user>/Desktop/SIA_V2/start_ui.sh
Path=/home/<user>/Desktop/SIA_V2
```

This keeps the UI tied to the logged-in desktop session (Wayland/X session), which is required for Pygame display startup.
