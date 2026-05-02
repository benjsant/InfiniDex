#!/usr/bin/env bash
# Régénère seed.sql.gz depuis la DB locale Docker.
# Lancer depuis la racine du repo :
#   bash backend/tests/fixtures/generate_fixture.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$SCRIPT_DIR/seed.sql.gz"

echo "▶ Dump en cours (data-only, disable-triggers)..."
docker exec fusiondex_postgres pg_dump \
  -U fusiondex_user \
  -d fusiondex_db \
  --data-only \
  --no-privileges \
  --no-owner \
  --disable-triggers \
  | gzip -9 > "$OUT"

SIZE=$(du -sh "$OUT" | cut -f1)
echo "✓ Fixture générée : $OUT ($SIZE)"
echo "  → committer avec : git add backend/tests/fixtures/seed.sql.gz"
