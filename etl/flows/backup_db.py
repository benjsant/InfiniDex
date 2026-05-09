"""
Prefect flow — PostgreSQL database backup.

Crée un dump pg_dump compressé (.sql.gz) horodaté dans le dossier backups/.
Garde les N backups les plus récents et supprime les anciens.

Lancement manuel :
  python -m etl.flows.backup_db

Lancement Prefect planifié (toutes les nuits à 3h) :
  prefect deployment run backup-db/nightly

Variables d'environnement (mêmes que le reste du projet) :
  POSTGRES_HOST      (défaut : localhost)
  POSTGRES_PORT      (défaut : FUSIONDEX_DB_PORT ou 55432)
  POSTGRES_DB        (défaut : fusiondex_db)
  POSTGRES_USER      (défaut : fusiondex_user)
  POSTGRES_PASSWORD  (requis)
  POSTGRES_CONTAINER (défaut : fusiondex_postgres — utilisé si pg_dump absent)
  BACKUP_DIR         (défaut : <repo>/backups)
  BACKUP_KEEP        (défaut : 10 — nombre de backups à conserver)
  DISCORD_WEBHOOK_URL (optionnel — alerte en cas d'échec)
"""

from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests
from prefect import flow, task
from prefect.logging import get_run_logger

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[2]
BACKUP_DIR  = Path(os.getenv("BACKUP_DIR", str(REPO_ROOT / "backups")))
KEEP        = int(os.getenv("BACKUP_KEEP", "10"))

_PG_HOST      = os.getenv("POSTGRES_HOST", "localhost")
_PG_PORT      = os.getenv("POSTGRES_PORT", os.getenv("FUSIONDEX_DB_PORT", "55432"))
_PG_DB        = os.getenv("POSTGRES_DB", "fusiondex_db")
_PG_USER      = os.getenv("POSTGRES_USER", "fusiondex_user")
_PG_PASSWORD  = os.getenv("POSTGRES_PASSWORD", "")
_PG_CONTAINER = os.getenv("POSTGRES_CONTAINER", "fusiondex_postgres")

_DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(name="pg-dump", retries=2, retry_delay_seconds=30)
def pg_dump_task() -> Path:
    """Crée le dump compressé et retourne son chemin."""
    logger    = get_run_logger()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = BACKUP_DIR / f"fusiondex_{ts}.sql.gz"

    env = os.environ.copy()
    env["PGPASSWORD"] = _PG_PASSWORD

    # Préférer pg_dump système ; fallback sur docker exec si absent.
    if shutil.which("pg_dump"):
        cmd = [
            "pg_dump",
            "-h", _PG_HOST,
            "-p", _PG_PORT,
            "-U", _PG_USER,
            _PG_DB,
        ]
        logger.info("Dumping via pg_dump → %s", outfile.name)
        result = subprocess.run(cmd, capture_output=True, env=env, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"pg_dump failed (code {result.returncode}): "
                f"{result.stderr.decode()[:500]}"
            )
        with gzip.open(outfile, "wb") as f:
            f.write(result.stdout)

    elif shutil.which("docker"):
        cmd = [
            "docker", "exec", _PG_CONTAINER,
            "pg_dump", "-U", _PG_USER, _PG_DB,
        ]
        logger.info("pg_dump not found — using docker exec %s → %s", _PG_CONTAINER, outfile.name)
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"docker exec pg_dump failed (code {result.returncode}): "
                f"{result.stderr.decode()[:500]}"
            )
        with gzip.open(outfile, "wb") as f:
            f.write(result.stdout)

    else:
        raise RuntimeError(
            "Neither pg_dump nor docker found — cannot create backup. "
            "Install postgresql-client or run from the host with Docker."
        )

    size_mb = outfile.stat().st_size / 1024 / 1024
    logger.info("Backup written: %s (%.1f MB)", outfile.name, size_mb)
    return outfile


@task(name="prune-old-backups")
def prune_old_backups(keep: int = KEEP) -> int:
    """Supprime les backups les plus anciens au-delà du quota."""
    logger  = get_run_logger()
    backups = sorted(BACKUP_DIR.glob("fusiondex_*.sql.gz"), reverse=True)
    to_delete = backups[keep:]
    for path in to_delete:
        path.unlink()
        logger.info("Deleted old backup: %s", path.name)
    if to_delete:
        logger.info("Pruned %d old backup(s), kept %d.", len(to_delete), keep)
    return len(to_delete)


@task(name="notify-backup-failure")
def notify_failure(error: str) -> None:
    """Alerte Discord en cas d'échec du backup."""
    if not _DISCORD_WEBHOOK:
        return
    try:
        requests.post(
            _DISCORD_WEBHOOK,
            json={"content": f"🔴 **Backup DB FusionDex échoué !**\n```{error[:500]}```"},
            timeout=10,
        )
    except Exception:
        pass  # best-effort


# ── Flow ──────────────────────────────────────────────────────────────────────

@flow(name="backup-db", log_prints=True)
def backup_db_flow(keep: int = KEEP) -> None:
    """
    Dump PostgreSQL → backups/fusiondex_YYYYMMDD_HHMMSS.sql.gz
    Garde les `keep` backups les plus récents.

    Restore :
      zcat backups/fusiondex_<ts>.sql.gz | psql <DSN>
    """
    logger = get_run_logger()
    logger.info(
        "Starting backup — DB: %s@%s:%s/%s, keep: %d",
        _PG_USER, _PG_HOST, _PG_PORT, _PG_DB, keep,
    )

    try:
        outfile = pg_dump_task()
    except Exception as exc:
        notify_failure(str(exc))
        raise

    prune_old_backups(keep)
    logger.info("Backup flow complete → %s", outfile.name)


if __name__ == "__main__":
    backup_db_flow()
