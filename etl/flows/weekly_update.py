"""
Prefect flow — Weekly FusionDex update checker.

Vérifie chaque lundi :
  1. Nouvelle version du jeu Pokémon Infinite Fusion (GitHub releases)
  2. Nouveaux sprites custom (sous-flow sprite_watcher)
  3. Envoie un résumé via Discord webhook (optionnel)

Lancement manuel :
  python -m etl.flows.weekly_update

Lancement planifié (lundi 9h Europe/Paris) :
  docker compose --profile prefect up -d prefect-worker
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from prefect import flow, task
from prefect.logging import get_run_logger

from etl.flows.sprite_watcher import sprite_watcher_flow

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
VERSION_FILE = DATA_DIR / "game_last_version.txt"

# Repo GitHub officiel du jeu (configurable via env si fork/miroir).
IF_GAME_REPO    = os.getenv("IF_GAME_REPO", "jonlanglet/Pokemon-Infinite-Fusion")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN", "")


def _gh_headers() -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(name="check-game-version", retries=2, retry_delay_seconds=30)
def check_game_version() -> dict:
    """Vérifie la dernière release GitHub du jeu IF.

    Returns:
        Dict avec les clés ``new_version`` (bool), ``version`` (str|None),
        ``previous`` (str|None).
    """
    logger = get_run_logger()
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{IF_GAME_REPO}/releases/latest",
            headers=_gh_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        latest: str = resp.json()["tag_name"]
    except Exception as exc:
        logger.warning("Impossible de récupérer la version du jeu : %s", exc)
        return {"new_version": False, "version": None, "previous": None}

    previous = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None
    is_new   = previous != latest

    if is_new:
        logger.info("Nouvelle version détectée : %s → %s", previous or "inconnue", latest)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        VERSION_FILE.write_text(latest)
    else:
        logger.info("Version inchangée : %s", latest)

    return {"new_version": is_new, "version": latest, "previous": previous}


@task(name="send-discord-notification")
def send_discord_notification(summary: str) -> None:
    """Envoie un message Discord via webhook (no-op si DISCORD_WEBHOOK_URL absent).

    Args:
        summary: Texte Markdown à envoyer.
    """
    if not DISCORD_WEBHOOK:
        return
    logger = get_run_logger()
    try:
        resp = requests.post(
            DISCORD_WEBHOOK,
            json={"content": summary},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Notification Discord envoyée.")
    except Exception as exc:
        logger.warning("Échec de la notification Discord : %s", exc)


# ── Flow ──────────────────────────────────────────────────────────────────────

@flow(name="weekly-update", log_prints=True)
def weekly_update_flow() -> None:
    """Flow hebdomadaire FusionDex.

    Vérifie la version du jeu IF, détecte les nouveaux sprites, puis envoie
    un résumé Discord.  Planifié tous les lundis à 9h (Europe/Paris).
    """
    logger = get_run_logger()
    logger.info("=== FusionDex — vérification hebdomadaire ===")

    # 1. Version du jeu
    version_info = check_game_version()

    # 2. Sprites (sous-flow existant)
    sprite_watcher_flow()

    # 3. Résumé + notification
    lines: list[str] = []

    if version_info["new_version"]:
        lines.append(
            f":video_game: Nouvelle version IF : **{version_info['version']}**"
            f" (était : {version_info['previous'] or 'inconnue'})"
        )
    else:
        ver = version_info["version"] or "inconnue"
        lines.append(f":video_game: Version IF inchangée ({ver})")

    lines.append(":frame_photo: Vérification des sprites terminée — voir logs Prefect.")

    summary = "**FusionDex — mise à jour hebdo**\n" + "\n".join(lines)
    logger.info(summary)
    send_discord_notification(summary)


if __name__ == "__main__":
    weekly_update_flow.serve(
        name="fusiondex-weekly-update",
        cron="0 9 * * 1",
        timezone="Europe/Paris",
        pause_on_shutdown=False,
    )
