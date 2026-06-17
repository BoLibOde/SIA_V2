#!/usr/bin/env bash
# ============================================================
# Produktionsdaten-Cleanup für stimmungsbarometer
#
# Verwendung: sudo bash scripts/cleanup_production_data.sh
#
# Was das Skript tut:
#   1. Vollständiges mysqldump-Backup erstellen
#   2. cleanup_production_data.sql ausführen
#   3. Ergebnis anzeigen
# ============================================================
set -euo pipefail

DB_NAME="stimmungsbarometer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/cleanup_production_data.sql"
BACKUP_DIR="${SCRIPT_DIR}/../.db-backups"

if [ ! -f "$SQL_FILE" ]; then
  echo "[cleanup] SQL-Datei nicht gefunden: $SQL_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/pre_cleanup_${TIMESTAMP}.sql"

echo "[cleanup] Erstelle Backup: $BACKUP_FILE"
sudo mysqldump --single-transaction --routines --triggers "$DB_NAME" > "$BACKUP_FILE"
echo "[cleanup] Backup abgeschlossen ($(du -sh "$BACKUP_FILE" | cut -f1))"

echo "[cleanup] Starte Cleanup ..."
sudo mysql "$DB_NAME" < "$SQL_FILE"

echo "[cleanup] Fertig. Backup liegt unter: $BACKUP_FILE"
echo "[cleanup] Zum Wiederherstellen: sudo mysql $DB_NAME < $BACKUP_FILE"
