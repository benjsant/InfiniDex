#!/usr/bin/env python3
"""
InfiniDex — PostgreSQL backup script.

Crée un dump pg_dump compressé (.sql.gz) horodaté dans backups/.
Garde les N backups les plus récents et supprime les anciens.

Fonctionne sur Linux, macOS et Windows (stdlib pure, aucune dépendance externe).

Usage :
    python scripts/backup_db.py
    python scripts/backup_db.py --keep 5
    python scripts/backup_db.py --backup-dir D:/backups

Variables d'environnement (mêmes que le reste du projet) :
    POSTGRES_HOST       défaut : localhost
    POSTGRES_PORT       défaut : INFINIDEX_DB_PORT ou 55432
    POSTGRES_DB         défaut : infinidex_db
    POSTGRES_USER       défaut : infinidex_user
    POSTGRES_PASSWORD   requis pour pg_dump direct
    POSTGRES_CONTAINER  défaut : infinidex_postgres (fallback docker exec)
    BACKUP_DIR          défaut : <repo>/backups
    BACKUP_KEEP         défaut : 10
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent

PG_HOST      = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT      = os.getenv("POSTGRES_PORT", os.getenv("INFINIDEX_DB_PORT", "55432"))
PG_DB        = os.getenv("POSTGRES_DB", "infinidex_db")
PG_USER      = os.getenv("POSTGRES_USER", "infinidex_user")
PG_PASSWORD  = os.getenv("POSTGRES_PASSWORD", "")
PG_CONTAINER = os.getenv("POSTGRES_CONTAINER", "infinidex_postgres")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], extra_env: dict[str, str] | None = None) -> bytes:
    """Lance une commande et retourne stdout. Lève RuntimeError si ça échoue."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(cmd, capture_output=True, env=env)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"Command failed (code {result.returncode}): {stderr}")
    return result.stdout


def dump_via_pg_dump() -> bytes:
    print(f"  → pg_dump {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    return _run(
        ["pg_dump", "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, PG_DB],
        extra_env={"PGPASSWORD": PG_PASSWORD},
    )


def dump_via_docker() -> bytes:
    print(f"  → docker exec {PG_CONTAINER} pg_dump")
    return _run(
        ["docker", "exec", PG_CONTAINER, "pg_dump", "-U", PG_USER, PG_DB],
    )


def create_dump() -> bytes:
    """Essaie pg_dump d'abord, puis docker exec en fallback."""
    if shutil.which("pg_dump"):
        return dump_via_pg_dump()
    if shutil.which("docker"):
        return dump_via_docker()
    raise RuntimeError(
        "Ni pg_dump ni docker trouvé dans le PATH.\n"
        "  Windows : installe PostgreSQL client ou utilise WSL.\n"
        "  Linux   : apt install postgresql-client"
    )


def prune(backup_dir: Path, keep: int) -> None:
    backups = sorted(backup_dir.glob("infinidex_*.sql.gz"), reverse=True)
    for old in backups[keep:]:
        old.unlink()
        print(f"  Supprimé : {old.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="InfiniDex DB backup")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(os.getenv("BACKUP_DIR", str(REPO_ROOT / "backups"))),
        help="Dossier de destination (défaut: <repo>/backups)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=int(os.getenv("BACKUP_KEEP", "10")),
        help="Nombre de backups à conserver (défaut: 10)",
    )
    args = parser.parse_args()

    backup_dir: Path = args.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = backup_dir / f"infinidex_{ts}.sql.gz"

    print(f"InfiniDex backup — {ts}")
    print(f"  Destination : {outfile}")

    try:
        sql_bytes = create_dump()
    except RuntimeError as exc:
        print(f"\n[ERREUR] {exc}", file=sys.stderr)
        sys.exit(1)

    with gzip.open(outfile, "wb") as f:
        f.write(sql_bytes)

    size_mb = outfile.stat().st_size / 1024 / 1024
    print(f"  Taille      : {size_mb:.1f} MB")

    prune(backup_dir, args.keep)

    print(f"\n✓ Backup terminé : {outfile.name}")


if __name__ == "__main__":
    main()
