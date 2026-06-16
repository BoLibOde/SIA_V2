#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/deploy/SIA-web"
SRC="$REPO_ROOT/server/WEBSITE/"
DEST="/var/www/html/stimmungsbarometer/"

if [ ! -d "$SRC" ]; then
  echo "Website source directory not found: $SRC" >&2
  exit 1
fi

echo "[web] Syncing PHP website files"
sudo mkdir -p "$DEST"
# db.local.php holds local-only production secrets — it must never be overwritten by a deploy
sudo rsync -av --delete \
  --exclude 'db.local.php' \
  --exclude '.gitkeep' \
  "$SRC" "$DEST"

echo "[web] Setting permissions"
sudo find "$DEST" -type d -exec chmod 755 {} \;
sudo find "$DEST" -type f -exec chmod 644 {} \;
sudo chown -R www-data:www-data "$DEST"

echo "[web] Reloading nginx"
if systemctl is-active --quiet nginx; then
  sudo systemctl reload nginx
else
  sudo systemctl start nginx
fi

echo "[web] Website deploy completed"
