"""
Correction script — fill in Infinite Fusion TMs via PokeAPI.

Business rule (Infinite Fusion): a Pokémon can learn an IF TM as soon as
it learns that move by *any* method in the official games (level, TM,
tutor, egg) OR through pre-evolution. The IF wiki scraper only captures
the moves listed on each Pokémon's own page, which leaves many gaps
(e.g. Moonblast: 13 Pokémon on the IF side, 63 on PokeAPI).

Pipeline:
  1. IF TM list → fandom wiki (api.php, prop=wikitext).
  2. For each TM, PokeAPI /move/{name}/ → learner list + `machines`
     flag (official TM in at least one game?).
  3. Insert `pokemon_move(method='tm', source=base|infinite_fusion)` for
     each learner present in our DB.
  4. Forward pre-evolution inheritance: every descendant of a learner
     also receives the TM (IF rule reminded by the user).
  5. Idempotent via the UNIQUE constraint (pokemon_id, move_id, method).

The `source` field distinguishes:
  - `base`             : official Nintendo TM (exists in at least one game).
  - `infinite_fusion`  : IF-specific TM (the move is not a TM elsewhere).
"""

from __future__ import annotations

import re

import requests

from etl.utils.db import pg_connection
from etl.utils.http import USER_AGENT
from etl.utils.logging import setup_logging
from etl.utils.pokeapi_moves import (
    all_descendants,
    fetch_move_detail,
    load_evolution_forward,
    load_move_ids,
    load_pokemon_ids,
)

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"


# ─── Step 1 — IF TM list ──────────────────────────────────────────────────────

TM_ROW_RE = re.compile(
    r"\|\s*(?:TM|HM)\d+\s*\n\|\s*\[\[[^|\]]+\|(?P<name>[^\]]+)\]\]"
)


def fetch_if_tm_names() -> list[str]:
    """Return the (en) names of the moves listed as TMs on the IF wiki."""
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   "List_of_TMs",
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]
    names = sorted({m.group("name").strip() for m in TM_ROW_RE.finditer(wikitext)})
    LOGGER.info("IF wiki: %d distinct moves listed as TMs", len(names))
    return names


# ─── Step 2 — Main pipeline ───────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    tm_names = fetch_if_tm_names()
    move_ids = load_move_ids(cur, tm_names)
    LOGGER.info("Moves found in DB: %d / %d", len(move_ids), len(tm_names))
    missing = set(tm_names) - set(move_ids)
    if missing:
        LOGGER.warning("IF TM moves missing from the `move` table (skipped): %s",
                       sorted(missing))

    pokemon_ids = load_pokemon_ids(cur)
    evolutions  = load_evolution_forward(cur)

    inserted = 0
    skipped  = 0

    for name_en, move_id in move_ids.items():
        detail = fetch_move_detail(name_en, logger=LOGGER)
        if detail is None:
            continue
        is_official_tm, learners = detail
        source = "base" if is_official_tm else "infinite_fusion"

        # Collect pokemon_id (learners + descendants)
        targets: set[int] = set()
        for slug in learners:
            pid = pokemon_ids.get(slug)
            if pid is None:
                continue
            targets.add(pid)
            targets |= all_descendants(pid, evolutions)

        if not targets:
            LOGGER.debug("No learner for %s", name_en)
            continue

        # Idempotent INSERT
        for pid in targets:
            cur.execute(
                """
                INSERT INTO pokemon_move (pokemon_id, move_id, method, source)
                VALUES (%s, %s, 'tm', %s)
                ON CONFLICT (pokemon_id, move_id, method) DO NOTHING
                """,
                (pid, move_id, source),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1

        LOGGER.info("  %s (source=%s) → %d learners targeted",
                    name_en, source, len(targets))

    conn.commit()
    cur.close()
    LOGGER.info("Done — %d new TM rows inserted, %d already present",
                inserted, skipped)


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    main()
