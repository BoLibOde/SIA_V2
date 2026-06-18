# Raspberry Pi UI runtime + device secret handling

The Raspberry Pi UI should run as a **desktop application** via desktop autostart so the
Pygame window is visible on the Pi display. For a visible UI, this desktop autostart path
is the single supported runtime model.

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
- starts `python -m device.main`
- writes app output to `ui-autostart.log`
- includes duplicate-start protection (if a `device.main` process already exists, startup is skipped and logged)

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
- close the running UI instance and start the updated one via `restart_ui.sh`

> **Important:** After any code change (manual `git pull`, file copy, etc.) the running
> Python process does **not** pick up new code automatically — it must be restarted.
> `update_pi.sh` handles this automatically. If you deploy by any other means, restart
> the UI manually afterwards.

## 6) Single-instance rule

Keep exactly **one** `python -m device.main` process running.

Do **not** run a parallel `systemd` service for `device.main` at the same time as desktop autostart.
That combination can cause duplicate uploads and inflated dashboard counts.

Recommended setup for a visible Pi UI:

```bash
sudo systemctl disable --now sia-device
```

Then let the desktop autostart entry launch the app on login.

Check the running process count with:

```bash
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

Expected result:

- exactly one process line
- count = `1`

Upload behavior expected with this runtime:

- Live uploads are the sole source of mood events / mood counts.
- Periodic uploads are 15-minute sensor aggregates only.
- Periodic aggregate uploads must not change mood counts.

## 7) Clean restart

```bash
cd ~/Desktop/SIA_V2
./restart_ui.sh
pgrep -af "python -m device.main"
pgrep -fc "python -m device.main"
```

## 8) Retry buffer / stale upload cleanup

Failed uploads are buffered locally in:

```text
device/pending_uploads.json
```

Check it with:

```bash
cat ~/Desktop/SIA_V2/device/pending_uploads.json
```

Normal state:

```json
[]
```

If the file contains old buffered events that you **intentionally want to discard** before the next start:

```bash
pkill -f "python -m device.main"
printf '[]\n' > ~/Desktop/SIA_V2/device/pending_uploads.json
cd ~/Desktop/SIA_V2
./restart_ui.sh
```

Only do this if you explicitly want to drop old buffered uploads instead of retrying them.

## 9) Manual restart only (no update)

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
