# Raspberry Pi UI runtime + device secret handling

The Raspberry Pi UI is managed via the `sia-device` systemd service or a desktop
autostart entry (both are supported). See section 4 and section 5 for setup details.
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
- `SIA_UPLOAD_ENDPOINT=/stimmungsbarometer/device_ingest.php`
- `SIA_HEALTH_ENDPOINT=/stimmungsbarometer/device_ingest.php`

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
- **checks if `device.main` is already running and exits immediately if so** (prevents double instances)
- starts `python -m device.main`
- writes app output to `ui-autostart.log`

## 4) Desktop autostart

Point the desktop autostart entry to this script:

```ini
Exec=/home/<user>/Desktop/SIA_V2/start_ui.sh
Path=/home/<user>/Desktop/SIA_V2
```

This keeps the UI tied to the logged-in desktop session (Wayland/X session), which is required for Pygame display startup.

## 5) Recommended update flow on the Pi

Avoid `git pull` for routine Pi updates when local branch tracking is uncertain
or when local merge state is unclear. `git pull` can fail unexpectedly or create local merges.
`update_pi.sh` uses a fast-forward-only update (`git merge --ff-only origin/main`) and exits with
clear guidance if the update cannot be done safely.
Use the helper scripts in the repository root:

```bash
cd ~/Desktop/SIA_V2
chmod +x restart_ui.sh update_pi.sh
./update_pi.sh
```

`update_pi.sh` will:

- fetch and fast-forward to `origin/main` in a predictable way
- preserve local `.env.device`
- refresh device Python dependencies
- **clear `device/pending_uploads.json`** to prevent stale buffered events from being re-uploaded
- **restart the running UI automatically via `restart_ui.sh`** (step 4/4)

> **Important:** After any code change (manual `git pull`, file copy, etc.) the running
> Python process does **not** pick up new code automatically — it must be restarted.
> `update_pi.sh` handles this automatically.  If you deploy by any other means, run
> `./restart_ui.sh` afterwards to apply the changes.

Upload safety note:

- Failed uploads from the **current session** continue to be buffered in `device/pending_uploads.json` and retried in the background.
- On each deploy or `./update_pi.sh`, the buffer is **cleared** so that old events accumulated across previous runs are not re-uploaded to production.
- Duplicate hourly aggregate entries in the buffer are collapsed automatically on the next retry cycle.

### Double-instance prevention

`start_ui.sh` now checks whether `device.main` is already running before starting a
new instance. If a process is already active (e.g. started by the systemd service),
`start_ui.sh` exits immediately without launching a second process.

This means you can safely have **both** the systemd service **and** the desktop
autostart entry configured: only one instance will run.

Recommended single-instance setup:

```bash
# Enable and start the systemd service (primary, survives reboots)
sudo systemctl enable sia-device
sudo systemctl start sia-device

# Desktop autostart entry (start_ui.sh) acts as a fallback only;
# if the service is already running it will exit without duplicating the process.
```

If you want to use **only** the desktop autostart (no systemd):

```bash
sudo systemctl disable sia-device
sudo systemctl stop sia-device
# Desktop autostart will start the app on next login.
```

### Migration: clearing stale data on an existing Pi

If your Pi has an existing `device/pending_uploads.json` with old buffered events,
remove it once before the next update to avoid uploading stale data to production:

```bash
# Adjust the path if your SIA_V2 installation is not in ~/Desktop/SIA_V2
rm -f ~/Desktop/SIA_V2/device/pending_uploads.json
```

This is done automatically by `./update_pi.sh` and by the CI deploy workflow going
forward.

## 6) Manual restart only (no update)

If you only need to restart the app without pulling new code:

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

After restart, verify with:

```bash
pgrep -af "python -m device.main"
tail -n 40 ~/Desktop/SIA_V2/ui-autostart.log
```
