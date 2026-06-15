#!/usr/bin/env bash
set -euo pipefail

DB_NAME="stimmungsbarometer"
REPO_ROOT="/home/deploy/SIA-web"
SQL_FILE="$REPO_ROOT/server/stimmungsbarometer.sql"
BACKUP_DIR="$REPO_ROOT/.db-backups"
TMP_DIR="$(mktemp -d)"
TMP_SCHEMA_SQL="$TMP_DIR/stimmungsbarometer_schema.sql"
TMP_EXISTING_MEASUREMENTS="$TMP_DIR/existing_measurements.sql"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_SQL="$BACKUP_DIR/stimmungsbarometer_${TIMESTAMP}.sql"
MEASUREMENTS_ARCHIVE_SQL="$BACKUP_DIR/measurements_${TIMESTAMP}.sql"

if [ ! -f "$SQL_FILE" ]; then
  echo "SQL file not found: $SQL_FILE" >&2
  exit 1
fi

echo "[db] Backing up full database snapshot"
sudo mysqldump --single-transaction --routines --triggers "$DB_NAME" > "$ARCHIVE_SQL"

echo "[db] Backing up existing measurements"
sudo mysqldump --single-transaction --no-create-info --skip-triggers --complete-insert "$DB_NAME" measurements > "$TMP_EXISTING_MEASUREMENTS"
cp "$TMP_EXISTING_MEASUREMENTS" "$MEASUREMENTS_ARCHIVE_SQL"

echo "[db] Preparing schema import from repository SQL dump"
python3 - "$SQL_FILE" "$TMP_SCHEMA_SQL" <<'PY'
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")

source = re.sub(
    r"INSERT INTO `measurements`.*?;\n",
    "",
    source,
    flags=re.S,
)

source = re.sub(
    r"ALTER TABLE `measurements`\s+MODIFY `id` int\(11\) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=\d+;",
    "ALTER TABLE `measurements` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;",
    source,
)

Path(sys.argv[2]).write_text(source, encoding="utf-8")
PY

echo "[db] Rebuilding database from repository schema"
sudo mysql -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
sudo sh -c "mysql '$DB_NAME' < '$TMP_SCHEMA_SQL'"

echo "[db] Clearing imported measurement seed data"
sudo mysql "$DB_NAME" -e "SET FOREIGN_KEY_CHECKS=0; TRUNCATE TABLE measurements; SET FOREIGN_KEY_CHECKS=1;"

echo "[db] Restoring existing real measurements"
if grep -q "INSERT INTO .*measurements" "$TMP_EXISTING_MEASUREMENTS"; then
  sudo sh -c "mysql '$DB_NAME' < '$TMP_EXISTING_MEASUREMENTS'"
fi

echo "[db] Fixing AUTO_INCREMENT"
NEXT_ID=$(sudo mysql -N -B "$DB_NAME" -e "SELECT COALESCE(MAX(id), 0) + 1 FROM measurements")
sudo mysql "$DB_NAME" -e "ALTER TABLE measurements AUTO_INCREMENT = $NEXT_ID;"

echo "[db] Database refresh completed"
