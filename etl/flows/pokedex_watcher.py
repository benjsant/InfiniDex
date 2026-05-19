"""
Prefect flow — Pokédex new Pokémon watcher.

Surveille deux sources pour détecter l'ajout de nouveaux Pokémon :
  1. Le wiki Infinite Fusion (PokedexTable/Data) — source officielle
  2. Data/pokedex/all_entries.json dans infinitefusion/infinitefusion-e18 — early detection
     (le fichier JSON est mis à jour dans le repo du jeu avant même que le wiki soit édité)

À chaque run :
  1. Récupère la liste wiki + le JSON du repo jeu
  2. Compare avec le snapshot local (data/pokedex_last_ids.json)
  3. Si de nouveaux IDs détectés → notifie Discord avec les noms

Lancement manuel :
  python -m etl.flows.pokedex_watcher

Lancement Prefect planifié (toutes les 24h) :
  prefect deployment run pokedex-watcher/daily
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests
from prefect import flow, task
from prefect.logging import get_run_logger

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR       = Path(__file__).resolve().parents[2] / "data"
SNAPSHOT_FILE  = DATA_DIR / "pokedex_last_ids.json"

# ── Wiki API ──────────────────────────────────────────────────────────────────
WIKI_API    = "https://infinitefusion.fandom.com/api.php"
POKEDEX_PAGE = "Pokédex"

# ── GitHub game repo (infinitefusion-e18) ────────────────────────────────────
GAME_REPO    = "infinitefusion/infinitefusion-e18"
GAME_BRANCH  = "main"
GAME_DEX_FILE = "Data/pokedex/all_entries.json"
GAME_SHA_FILE = DATA_DIR / "game_dex_last_sha.txt"

_DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

# PokedexTable/Data template:  {{PokedexTable/Data|index|id|name|...}}
_ENTRY_RE = re.compile(
    r"\{\{PokedexTable/Data\s*\|"
    r"\s*\d+\s*\|"
    r"\s*(?P<id>\d+)\s*\|"
    r"\s*(?P<name>[^|]+?)\s*\|",
    re.IGNORECASE,
)



# ── Tasks ─────────────────────────────────────────────────────────────────────

@task(name="fetch-wiki-pokedex", retries=3, retry_delay_seconds=30)
def fetch_wiki_pokedex() -> dict[int, str]:
    """Récupère la liste des Pokémon depuis le wiki IF.

    Returns {if_id: name_en}
    """
    logger = get_run_logger()
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   POKEDEX_PAGE,
            "prop":   "wikitext",
            "format": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "parse" not in data:
        raise RuntimeError(f"Wiki API returned unexpected shape: {list(data.keys())}")

    wikitext = data["parse"]["wikitext"]["*"]
    entries: dict[int, str] = {}
    for m in _ENTRY_RE.finditer(wikitext):
        if_id = int(m.group("id"))
        name  = m.group("name").strip()
        entries[if_id] = name

    logger.info("Wiki Pokédex: %d entries found", len(entries))
    return entries


@task(name="fetch-game-sha", retries=3, retry_delay_seconds=30)
def fetch_game_sha() -> str:
    """Récupère le SHA du dernier commit sur main du repo du jeu."""
    logger = get_run_logger()
    resp = requests.get(
        f"https://api.github.com/repos/{GAME_REPO}/commits/{GAME_BRANCH}",
        timeout=15,
    )
    resp.raise_for_status()
    sha = resp.json()["sha"]
    logger.info("Game repo SHA: %s", sha[:8])
    return sha


@task(name="fetch-game-dex-ids", retries=2, retry_delay_seconds=20)
def fetch_game_dex_ids(sha: str) -> set[int]:
    """Récupère les IDs de Data/pokedex/all_entries.json à un SHA donné."""
    logger = get_run_logger()
    url  = f"https://raw.githubusercontent.com/{GAME_REPO}/{sha}/{GAME_DEX_FILE}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 404:
        logger.warning("%s not found at SHA %s", GAME_DEX_FILE, sha[:8])
        return set()
    resp.raise_for_status()
    data = resp.json()
    ids  = {int(k) for k in data.keys()}
    logger.info("Game dex JSON: %d IDs found", len(ids))
    return ids


@task(name="load-snapshot")
def load_snapshot() -> dict[int, str]:
    """Lit le snapshot local des Pokémon connus."""
    if SNAPSHOT_FILE.exists():
        raw = json.loads(SNAPSHOT_FILE.read_text())
        # Keys are stored as strings in JSON
        return {int(k): v for k, v in raw.items()}
    return {}


@task(name="read-local-game-sha")
def read_local_game_sha() -> str | None:
    if GAME_SHA_FILE.exists():
        return GAME_SHA_FILE.read_text().strip() or None
    return None


@task(name="detect-new-pokemon")
def detect_new_pokemon(
    current: dict[int, str],
    known: dict[int, str],
    source: str,
) -> list[tuple[int, str]]:
    """Détecte les Pokémon présents dans `current` mais absents de `known`."""
    logger = get_run_logger()
    new_ids = sorted(set(current.keys()) - set(known.keys()))
    new_entries = [(i, current[i]) for i in new_ids]
    if new_entries:
        names = ", ".join(f"#{i} {n}" for i, n in new_entries[:10])
        suffix = f" (+ {len(new_entries) - 10} autres)" if len(new_entries) > 10 else ""
        logger.warning("[%s] %d new Pokémon: %s%s", source, len(new_entries), names, suffix)
    else:
        logger.info("[%s] No new Pokémon detected (%d known).", source, len(known))
    return new_entries


@task(name="notify-new-pokemon")
def notify_new_pokemon(new_entries: list[tuple[int, str]], source: str) -> None:
    """Envoie une alerte Discord listant les nouveaux Pokémon."""
    logger = get_run_logger()
    if not new_entries:
        return

    lines = "\n".join(f"• `#{i}` **{n}**" for i, n in new_entries[:20])
    suffix = f"\n_… et {len(new_entries) - 20} autres_" if len(new_entries) > 20 else ""
    msg = (
        f"🆕 **{len(new_entries)} nouveau(x) Pokémon détecté(s) sur {source} !**\n\n"
        f"{lines}{suffix}\n\n"
        "Un re-run ETL (`extract_pokedex_if.py` → `load_db.py`) est nécessaire pour les intégrer."
    )

    if not _DISCORD_WEBHOOK:
        logger.info("DISCORD_WEBHOOK_URL not set — notification skipped.")
        logger.info("Message would have been:\n%s", msg)
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


@task(name="save-pokedex-snapshot")
def save_pokedex_snapshot(entries: dict[int, str], game_sha: str | None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    if game_sha:
        GAME_SHA_FILE.write_text(game_sha)
    logger = get_run_logger()
    logger.info(
        "Snapshot saved — %d Pokémon, game repo SHA: %s",
        len(entries),
        game_sha[:8] if game_sha else "N/A",
    )


# ── Flow ──────────────────────────────────────────────────────────────────────

@flow(name="pokedex-watcher", log_prints=True)
def pokedex_watcher_flow() -> None:
    """
    Détecte l'ajout de nouveaux Pokémon dans le wiki IF et le PBS GitHub.

    Sources vérifiées :
    - Wiki IF (PokedexTable/Data) — source officielle du jeu
    - PBS pokemon.txt (infinitefusion/infinitefusion-e18) — early detection

    À planifier toutes les 24h via Prefect (idéalement quelques heures avant
    que le sprite_watcher ne tourne, afin d'anticiper une nouvelle version).
    """
    logger = get_run_logger()

    # ── Load known state ──────────────────────────────────────────────────────
    known         = load_snapshot()
    local_game_sha = read_local_game_sha()

    logger.info("Known Pokémon: %d", len(known))

    # ── Wiki check ────────────────────────────────────────────────────────────
    wiki_entries = fetch_wiki_pokedex()
    wiki_new     = detect_new_pokemon(wiki_entries, known, "Wiki IF")
    if wiki_new:
        notify_new_pokemon(wiki_new, "Wiki IF")

    # ── Game repo / GitHub early detection ───────────────────────────────────
    game_sha = fetch_game_sha()

    if game_sha != local_game_sha:
        logger.info(
            "Game repo updated: %s → %s",
            (local_game_sha or "none")[:8],
            game_sha[:8],
        )
        game_ids   = fetch_game_dex_ids(game_sha)
        game_known = set(known.keys())

        # Build minimal dicts (IDs only — game JSON has descriptions, not names)
        game_current   = {i: f"ID#{i}" for i in game_ids}
        game_known_dict = {i: f"ID#{i}" for i in game_known}
        game_new = detect_new_pokemon(game_current, game_known_dict, "Game repo")

        # Cross-reference with wiki names if available
        if game_new:
            enriched = [(i, wiki_entries.get(i, f"ID#{i}")) for i, _ in game_new]
            notify_new_pokemon(enriched, "Game repo (early detection)")
    else:
        logger.info("Game repo unchanged (SHA=%s). Skipping game dex check.", game_sha[:8])

    # ── Save snapshot (wiki is authoritative) ─────────────────────────────────
    if not known or wiki_new or wiki_entries != known:
        save_pokedex_snapshot(wiki_entries, game_sha)
        if not known:
            logger.info("First run — snapshot initialized with %d Pokémon.", len(wiki_entries))
    else:
        logger.info("No changes — snapshot unchanged.")

    logger.info("Pokédex watcher flow complete.")


if __name__ == "__main__":
    pokedex_watcher_flow()
