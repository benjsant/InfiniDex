#!/usr/bin/env bash
# Dump the FusionDex PostgreSQL database to a timestamped gzip file.
#
# Usage:
#   ./scripts/backup_db.sh              # dumps to ./backups/
#   BACKUP_DIR=/mnt/nas ./scripts/backup_db.sh
#
# Requires: docker (postgres container running), or pg_dump + env vars set.
# Restore:  zcat <file> | psql "$DSN"

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="$BACKUP_DIR/fusiondex_${TIMESTAMP}.sql.gz"

# Try via docker exec first (works when the container is running).
CONTAINER="${POSTGRES_CONTAINER:-fusiondex_postgres}"

if docker inspect "$CONTAINER" &>/dev/null 2>&1; then
  echo "Dumping via container $CONTAINER…"
  docker exec "$CONTAINER" pg_dump \
    -U "${POSTGRES_USER:-fusiondex}" \
    "${POSTGRES_DB:-fusiondex}" \
    | gzip > "$OUTFILE"
else
  # Fallback: use pg_dump directly (env vars must be set).
  echo "Container not found — using pg_dump directly…"
  PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-55432}" \
    -U "${POSTGRES_USER:-fusiondex}" \
    "${POSTGRES_DB:-fusiondex}" \
    | gzip > "$OUTFILE"
fi

SIZE=$(du -sh "$OUTFILE" | cut -f1)
echo "✓ Backup written: $OUTFILE ($SIZE)"

# Keep only the 10 most recent backups to avoid filling disk.
KEEP=10
COUNT=$(ls -1t "$BACKUP_DIR"/fusiondex_*.sql.gz 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
  ls -1t "$BACKUP_DIR"/fusiondex_*.sql.gz | tail -n +"$((KEEP + 1))" | xargs rm -f
  echo "Pruned old backups (kept $KEEP most recent)."
fi
