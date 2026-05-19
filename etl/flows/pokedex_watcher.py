"""
Prefect flow — Pokédex new-Pokémon watcher.

Watches two sources to detect newly added Pokémon:
  1. The Infinite Fusion wiki (PokedexTable/Data) — official source
  2. Data/pokedex/all_entries.json in infinitefusion/infinitefusion-e18 — early detection
     (the JSON file is updated in the game repo even before the wiki is edited)

On each run:
  1. Fetch the wiki list + the game-repo JSON
  2. Compare with the local snapshot (data/pokedex_last_ids.json)
  3. If new IDs are detected → notify Discord with the names

Manual run:
  python -m etl.flows.pokedex_watcher

Scheduled Prefect run (every 24h):
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
# Discord webhooks sit behind Cloudflare, which 403s requests with a default
# python User-Agent (CF error 1010) — set a browser UA to get through.
_DISCORD_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

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
    """Fetch the Pokémon list from the IF wiki.

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
    """Fetch the SHA of the latest commit on the game repo's main branch."""
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
    """Fetch the IDs from Data/pokedex/all_entries.json at a given SHA."""
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
    """Read the local snapshot of known Pokémon."""
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
    """Detect Pokémon present in `current` but absent from `known`."""
    logger = get_run_logger()
    new_ids = sorted(set(current.keys()) - set(known.keys()))
    new_entries = [(i, current[i]) for i in new_ids]
    if new_entries:
        names = ", ".join(f"#{i} {n}" for i, n in new_entries[:10])
        suffix = f" (+ {len(new_entries) - 10} more)" if len(new_entries) > 10 else ""
        logger.warning("[%s] %d new Pokémon: %s%s", source, len(new_entries), names, suffix)
    else:
        logger.info("[%s] No new Pokémon detected (%d known).", source, len(known))
    return new_entries


@task(name="notify-new-pokemon")
def notify_new_pokemon(new_entries: list[tuple[int, str]], source: str) -> None:
    """Send a Discord alert listing the new Pokémon."""
    logger = get_run_logger()
    if not new_entries:
        return

    lines = "\n".join(f"• `#{i}` **{n}**" for i, n in new_entries[:20])
    suffix = f"\n_… and {len(new_entries) - 20} more_" if len(new_entries) > 20 else ""
    msg = (
        f"🆕 **{len(new_entries)} new Pokémon detected on {source}!**\n\n"
        f"{lines}{suffix}\n\n"
        "An ETL re-run (`extract_pokedex_if.py` → `load_db.py`) is needed to integrate them."
    )

    if not _DISCORD_WEBHOOK:
        logger.info("DISCORD_WEBHOOK_URL not set — notification skipped.")
        logger.info("Message would have been:\n%s", msg)
        return

    try:
        resp = requests.post(
            _DISCORD_WEBHOOK,
            json={"content": msg},
            headers={"User-Agent": _DISCORD_UA},
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
    Detect newly added Pokémon in the IF wiki and the GitHub PBS.

    Sources checked:
    - IF wiki (PokedexTable/Data) — official game source
    - PBS pokemon.txt (infinitefusion/infinitefusion-e18) — early detection

    Schedule every 24h via Prefect (ideally a few hours before
    sprite_watcher runs, to anticipate a new version).
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
