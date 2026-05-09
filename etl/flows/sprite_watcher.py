"""
Prefect flow — Sprite update watcher.

Surveille le repo infinitefusion/pif-downloadables (branche master).
À chaque run :
  1. Compare le SHA du dernier commit avec le SHA connu localement
  2. Si nouveau commit :
     a. Lit Settings.rb → détecte un changement de version du jeu
     b. Diff CUSTOM_SPRITES (ajouts / suppressions)
     c. Diff BASE_SPRITES (ajouts / suppressions)
     d. Nettoie les sprites supprimés du disque
     e. Lance extract_sprites.py si des sprites ont été ajoutés
     f. Notifie Discord si la version du jeu a changé
  3. Sauvegarde le SHA + la version pour le prochain run

Lancement manuel :
  python -m etl.flows.sprite_watcher

Lancement Prefect planifié (toutes les 24h) :
  prefect deployment run sprite-watcher/daily
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import requests
from prefect import flow, task
from prefect.logging import get_run_logger

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).resolve().parents[2] / "data"
SHA_FILE    = DATA_DIR / "sprites_last_sha.txt"
VER_FILE    = DATA_DIR / "game_version.txt"
SPRITES_DIR = DATA_DIR / "sprites"

# ── GitHub API ────────────────────────────────────────────────────────────────
REPO     = "infinitefusion/pif-downloadables"
BRANCH   = "master"
API_BASE = f"https://api.github.com/repos/{REPO}"

_DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(name="fetch-latest-sha", retries=3, retry_delay_seconds=30)
def fetch_latest_sha() -> str:
    """Récupère le SHA du dernier commit sur master."""
    logger = get_run_logger()
    resp = requests.get(f"{API_BASE}/commits/{BRANCH}", timeout=15)
    resp.raise_for_status()
    sha = resp.json()["sha"]
    logger.info("Latest SHA: %s", sha[:8])
    return sha


@task(name="read-local-sha")
def read_local_sha() -> str | None:
    """Lit le SHA connu localement."""
    if SHA_FILE.exists():
        return SHA_FILE.read_text().strip() or None
    return None


@task(name="fetch-settings-version", retries=2, retry_delay_seconds=20)
def fetch_settings_version(sha: str) -> str | None:
    """Lit LATEST_GAME_RELEASE dans Settings.rb au SHA donné."""
    logger = get_run_logger()
    url  = f"https://raw.githubusercontent.com/{REPO}/{sha}/Settings.rb"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 404:
        logger.warning("Settings.rb not found at SHA %s", sha[:8])
        return None
    resp.raise_for_status()
    m = re.search(r'LATEST_GAME_RELEASE\s*=\s*"([^"]+)"', resp.text)
    version = m.group(1) if m else None
    logger.info("Game version at %s: %s", sha[:8], version or "unknown")
    return version


@task(name="read-local-version")
def read_local_version() -> str | None:
    if VER_FILE.exists():
        return VER_FILE.read_text().strip() or None
    return None


@task(name="fetch-sprite-list", retries=3, retry_delay_seconds=30)
def fetch_sprite_list(sha: str, filename: str = "CUSTOM_SPRITES") -> set[str]:
    """Récupère la liste de sprites (CUSTOM_SPRITES ou BASE_SPRITES) à un SHA donné."""
    url  = f"https://raw.githubusercontent.com/{REPO}/{sha}/{filename}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 404:
        return set()
    resp.raise_for_status()
    return {
        line.strip()
        for line in resp.text.splitlines()
        if line.strip().endswith(".png")
    }


@task(name="compute-diff")
def compute_diff(old: set[str], new: set[str], label: str) -> dict[str, list[str]]:
    """Calcule les fichiers ajoutés et supprimés entre deux listes."""
    logger  = get_run_logger()
    added   = sorted(new - old)
    removed = sorted(old - new)
    logger.info("%s — added: %d / removed: %d", label, len(added), len(removed))
    return {"added": added, "removed": removed}


@task(name="cleanup-removed-sprites")
def cleanup_removed_sprites(removed: list[str]) -> int:
    """Supprime du disque les sprites retirés de CUSTOM_SPRITES.

    Le nom de fichier dans la liste est au format '{head_id}.{body_id}.png'
    (ou '{head_id}.{body_id}a.png' pour les alts).
    """
    logger  = get_run_logger()
    deleted = 0
    for filename in removed:
        path = SPRITES_DIR / filename
        if path.exists():
            path.unlink()
            deleted += 1
    if deleted:
        logger.info("Deleted %d stale sprite(s) from disk.", deleted)
    return deleted


@task(name="extract-new-sprites")
def extract_new_sprites() -> None:
    """Lance extract_sprites.py pour télécharger les nouveaux sprites."""
    logger      = get_run_logger()
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    logger.info("Launching sprite extraction…")
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "extract_sprites.py")],
        check=False,
    )
    if result.returncode != 0:
        logger.error("extract_sprites.py failed (code %d)", result.returncode)
    else:
        logger.info("Extraction complete.")


@task(name="notify-version-change")
def notify_version_change(old_version: str | None, new_version: str) -> None:
    """Envoie une alerte Discord quand la version du jeu change."""
    logger = get_run_logger()
    msg = (
        f"🎮 **Nouvelle version de Pokémon Infinite Fusion détectée !**\n"
        f"> `{old_version or 'inconnue'}` → `{new_version}`\n\n"
        "Un re-run ETL complet est peut-être nécessaire pour intégrer les changements de données."
    )
    logger.warning("Game version changed: %s → %s", old_version, new_version)

    if not _DISCORD_WEBHOOK:
        logger.info("DISCORD_WEBHOOK_URL not set — notification skipped.")
        return

    try:
        resp = requests.post(
            _DISCORD_WEBHOOK,
            json={"content": msg},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Discord notification sent.")
    except Exception as exc:
        logger.warning("Discord notification failed: %s", exc)


@task(name="save-state")
def save_state(sha: str, version: str | None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHA_FILE.write_text(sha)
    if version:
        VER_FILE.write_text(version)
    logger = get_run_logger()
    logger.info("State saved — SHA: %s, version: %s", sha[:8], version or "unchanged")


# ── Flow ──────────────────────────────────────────────────────────────────────

@flow(name="sprite-watcher", log_prints=True)
def sprite_watcher_flow() -> None:
    """
    Détecte les nouvelles versions du jeu et les mises à jour de sprites IF.
    À planifier toutes les 24h via Prefect.

    Actions :
    - Alerte Discord si la version du jeu (Settings.rb) a changé
    - Diff CUSTOM_SPRITES et BASE_SPRITES
    - Supprime les sprites retirés du disque
    - Lance extract_sprites.py si des sprites ont été ajoutés
    """
    logger = get_run_logger()

    latest_sha = fetch_latest_sha()
    local_sha  = read_local_sha()
    local_ver  = read_local_version()

    if local_sha == latest_sha:
        logger.info("No update detected (SHA=%s). Nothing to do.", latest_sha[:8])
        return

    logger.info(
        "New commit detected: %s → %s",
        (local_sha or "none")[:8],
        latest_sha[:8],
    )

    # ── Check game version ────────────────────────────────────────────────────
    new_version = fetch_settings_version(latest_sha)
    if new_version and new_version != local_ver:
        notify_version_change(local_ver, new_version)
    elif new_version:
        logger.info("Game version unchanged: %s", new_version)

    # ── Diff sprite lists ─────────────────────────────────────────────────────
    need_extraction = False

    if local_sha:
        # CUSTOM_SPRITES
        old_custom = fetch_sprite_list(local_sha, "CUSTOM_SPRITES")
        new_custom = fetch_sprite_list(latest_sha, "CUSTOM_SPRITES")
        custom_diff = compute_diff(old_custom, new_custom, "CUSTOM_SPRITES")

        if custom_diff["removed"]:
            cleanup_removed_sprites(custom_diff["removed"])

        if custom_diff["added"]:
            logger.info(
                "New custom sprites:\n  %s%s",
                "\n  ".join(custom_diff["added"][:20]),
                f"\n  … and {len(custom_diff['added']) - 20} more"
                if len(custom_diff["added"]) > 20 else "",
            )
            need_extraction = True

        # BASE_SPRITES
        old_base = fetch_sprite_list(local_sha, "BASE_SPRITES")
        new_base = fetch_sprite_list(latest_sha, "BASE_SPRITES")
        base_diff = compute_diff(old_base, new_base, "BASE_SPRITES")

        if base_diff["removed"]:
            cleanup_removed_sprites(base_diff["removed"])

        if base_diff["added"]:
            logger.info("New base sprites: %d — triggering extraction.", len(base_diff["added"]))
            need_extraction = True

        if not need_extraction:
            logger.info(
                "Sprite lists unchanged — only Settings.rb or other files updated."
            )
            save_state(latest_sha, new_version)
            return
    else:
        logger.info("First run — full extraction.")
        need_extraction = True

    # ── Extract ───────────────────────────────────────────────────────────────
    if need_extraction:
        extract_new_sprites()

    save_state(latest_sha, new_version)
    logger.info("Sprite watcher flow complete.")


if __name__ == "__main__":
    sprite_watcher_flow()
