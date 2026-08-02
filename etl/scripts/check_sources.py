"""
Watchdog — probe the external sources the ETL depends on and fail loudly.

Every ETL breakage this project has seen came from an upstream change
discovered by accident during a rebuild (IF wiki Pokédex restructure,
Pokepédia switching to protocol-relative hrefs). This script checks the
minimal invariants of each source WITHOUT touching the database, so a
scheduled CI run can raise the alarm before anyone re-runs the pipeline.

Checks (network only, no DB):
  1. IF wiki  — Pokédex/Hoenn/Classic parses ≥ 572 entries
  2. IF wiki  — Pokédex/Kanto/Classic parses ≥ 501 ids, strictly fewer
                than Hoenn (the diff is the Hoenn-only flag)
  3. IF wiki  — List_of_Moves parses ≥ 600 moves
  4. IF wiki  — List of Abilities parses ≥ 170 abilities
  5. Pokepédia — national dex list maps ≥ 1000 species, 0 corrupt slugs
  6. Pokepédia — sample Génération_7 page reachable and carries USUL data
  7. PokeAPI  — /pokemon/25 answers with types
  8. IF game  — LATEST_GAME_RELEASE in the game repo still matches the version
                recorded in data/game_version.txt

Check 8 is deliberately stateless: `data/game_version.txt` is committed, so a
new game release makes this fail until someone bumps the file — which is the
signal to review what the release changed. (The heavy `sprite_watcher` Prefect
flow does the same check, but it only runs when the Prefect stack is up, which
is why 6.8.0 went unnoticed for three weeks.)

Run with the HTTP cache disabled so the probes hit the live sources:
    ETL_HTTP_CACHE_TTL_HOURS=0 python -m etl.scripts.check_sources

Exit code: 0 = all good, 1 = at least one source drifted.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

from etl.scripts.extract_abilities_if import parse_abilities
from etl.scripts.extract_moves_if import extract_moves
from etl.scripts.extract_pokedex_if import KANTO_PAGE, PAGE, extract_ids, parse_entries
from etl.scripts.extract_pokepedia_names import fetch_page, parse_list
from etl.utils.http import HEADERS, get_json
from etl.utils.logging import setup_logging
from etl.utils.wikitext import fetch_wikitext

LOGGER = setup_logging(__name__)

POKEPEDIA_SAMPLE = "https://www.pokepedia.fr/Bulbizarre/Génération_7"

# Same source the sprite_watcher flow reads (pif-downloadables/Settings.rb).
GAME_SETTINGS_URL = "https://raw.githubusercontent.com/infinitefusion/pif-downloadables/master/Settings.rb"
GAME_VERSION_FILE = Path("data/game_version.txt")
_GAME_VERSION_RE = re.compile(r'LATEST_GAME_RELEASE\s*=\s*"([^"]+)"')

FAILURES: list[str] = []


def parse_game_version(settings_rb: str) -> str | None:
    """Extract LATEST_GAME_RELEASE from the game's Settings.rb contents."""
    m = _GAME_VERSION_RE.search(settings_rb)
    return m.group(1) if m else None


def check(label: str, condition: bool, detail: str) -> None:
    if condition:
        LOGGER.info("OK   %s — %s", label, detail)
    else:
        LOGGER.error("FAIL %s — %s", label, detail)
        FAILURES.append(f"{label}: {detail}")


def main() -> None:
    # 1-2. IF wiki Pokédex subpages
    hoenn = parse_entries(fetch_wikitext(PAGE))
    check("wiki-pokedex-hoenn", len(hoenn) >= 572,
          f"{len(hoenn)} entrées parsées sur {PAGE} (attendu ≥ 572)")

    kanto_ids = extract_ids(fetch_wikitext(KANTO_PAGE))
    check("wiki-pokedex-kanto", len(kanto_ids) >= 501,
          f"{len(kanto_ids)} ids parsés sur {KANTO_PAGE} (attendu ≥ 501)")
    check("wiki-pokedex-diff", 0 < len(hoenn) - len(kanto_ids) <= 200,
          f"diff Hoenn-Kanto = {len(hoenn) - len(kanto_ids)} (le flag hoenn-only en dépend)")

    # 3. Moves
    moves = extract_moves(fetch_wikitext("List_of_Moves"))
    check("wiki-moves", len(moves) >= 600,
          f"{len(moves)} moves parsés (attendu ≥ 600)")

    # 4. Abilities
    abilities = parse_abilities(fetch_wikitext("List of Abilities"))
    check("wiki-abilities", len(abilities) >= 170,
          f"{len(abilities)} talents parsés (attendu ≥ 170)")

    # 5. Pokepédia mapping
    entries = parse_list(fetch_page())
    corrupt = [e for e in entries if "/" in e["pokepedia_slug"] or not e["pokepedia_slug"]]
    check("pokepedia-mapping", len(entries) >= 1000 and not corrupt,
          f"{len(entries)} espèces mappées, {len(corrupt)} slugs corrompus")

    # 6. Pokepédia sample Gen 7 page (what the movesets crawl consumes)
    try:
        resp = requests.get(POKEPEDIA_SAMPLE, headers=HEADERS, timeout=20)
        page_ok = resp.status_code == 200 and "USUL" in resp.text
        detail = f"HTTP {resp.status_code}, marqueur USUL {'présent' if page_ok else 'absent'}"
    except requests.RequestException as exc:
        page_ok, detail = False, str(exc)
    check("pokepedia-gen7", page_ok, detail)

    # 7. PokeAPI
    pika = get_json("https://pokeapi.co/api/v2/pokemon/25")
    check("pokeapi", bool(pika and pika.get("types")),
          "GET /pokemon/25 " + ("répond avec types" if pika else "en échec"))

    # 8. Version du jeu vs version enregistrée (fichier committé)
    try:
        resp = requests.get(GAME_SETTINGS_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        live_version = parse_game_version(resp.text)
    except requests.RequestException as exc:
        live_version = None
        LOGGER.warning("Settings.rb injoignable: %s", exc)

    known_version = (
        GAME_VERSION_FILE.read_text(encoding="utf-8").strip()
        if GAME_VERSION_FILE.exists() else None
    )
    check("game-version", bool(live_version) and live_version == known_version,
          f"jeu={live_version or '?'} / enregistré={known_version or 'absent'}"
          + ("" if live_version == known_version
             else " → nouvelle version : vérifier le contenu puis bumper data/game_version.txt"))

    if FAILURES:
        LOGGER.error("%d source(s) en dérive:", len(FAILURES))
        for f in FAILURES:
            LOGGER.error("  - %s", f)
        sys.exit(1)
    LOGGER.info("Toutes les sources répondent aux invariants (%d checks).", 8)


if __name__ == "__main__":
    main()
