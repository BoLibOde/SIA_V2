#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env.device"
ENV_BACKUP=""

cd "$APP_DIR"

cleanup() {
    if [ -n "$ENV_BACKUP" ] && [ -f "$ENV_BACKUP" ]; then
        if ! mv "$ENV_BACKUP" "$ENV_FILE"; then
            echo "Warning: failed to restore backup to $ENV_FILE." >&2
            echo "Backup retained at: $ENV_BACKUP" >&2
        fi
    fi
}
trap cleanup EXIT

if [ -f "$ENV_FILE" ]; then
    ENV_BACKUP="$(mktemp -p "$APP_DIR" .env.device.backup.XXXXXX)"
    cp "$ENV_FILE" "$ENV_BACKUP"
    chmod 600 "$ENV_BACKUP"
fi

echo "[1/4] Fetching latest code from origin/main..."
git fetch origin main

echo "[2/4] Updating local main branch (fast-forward only)..."
if git show-ref --verify --quiet refs/heads/main; then
    git switch main
else
    git switch -c main --track origin/main
fi
if ! git merge --ff-only origin/main; then
    echo "Update aborted: local branch cannot fast-forward to origin/main." >&2
    echo "Please resolve local commits/changes first, then retry ./update_pi.sh." >&2
    exit 1
fi

echo "[3/4] Refreshing Python dependencies..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade -r "$APP_DIR/requirements-device.txt"

echo "[4/4] Restarting UI..."
"$APP_DIR/restart_ui.sh"

echo ""
echo "Update complete."
echo "Pending failed uploads are retained in device/pending_uploads.json and retried by the app."
