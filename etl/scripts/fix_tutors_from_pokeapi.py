"""
Correction script — fill in Infinite Fusion Move Tutor moves.

Same rule as for TMs (cf. fix_tms_from_pokeapi.py): a Pokémon can learn
a move via an IF tutor if it learns it by *any* official method (level,
TM, tutor, egg) or through pre-evolution inheritance.

Three wiki rows are skipped because they are not real moves:
  - "Move Teacher" (Move Reminder): re-teaches moves already in the learnset
  - "Move Deleter": deletes moves
  - "Egg Moves": slot to re-learn egg moves (already captured under the
    `breeding` method)

The Move Expert page is handled separately (List_of_Move_Expert_Moves),
since those moves are only learnable on fusions under conditions.
"""

from __future__ import annotations

import re
import time

import requests

from etl.utils.db import pg_connection
from etl.utils.http import USER_AGENT
from etl.utils.logging import setup_logging
from etl.utils.pokeapi_moves import (
    DELAY,
    all_descendants,
    fetch_move_detail,
    load_evolution_forward,
    load_move_ids,
    load_pokemon_ids,
)

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"

SKIP_NAMES: set[str] = {
    "Move Teacher",
    "Move Reminder",
    "Move Deleter",
    "Egg Moves",
}


# ─── Step 1 — Parse tutor list ────────────────────────────────────────────────

# Lines of the form:
#   |[[bulbapedia:NAME_LINK|DISPLAY_NAME]]
# or:
#   |[https://bulbapedia.../NAME DISPLAY_NAME]
# We capture DISPLAY_NAME, then filter via SKIP_NAMES.
TUTOR_BULBA_WIKI = re.compile(
    r"\|\s*\[\[bulbapedia:[^|\]]+\|(?P<name>[^\]]+)\]\]"
)
TUTOR_BULBA_EXTLINK = re.compile(
    r"\|\s*\[https?://bulbapedia\.bulbagarden\.net/wiki/[^\s]+\s+(?P<name>[^\]]+)\]"
)


def fetch_tutor_names() -> list[str]:
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   "List_of_Tutors",
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]

    # Only capture the FIRST cell of each table row (which is the move name).
    # The wiki table uses row separators "|-" and columns separated by "|".
    # A naive extract of any bulbapedia link would also catch "Location" cells
    # that happen to link to a move (rare). We therefore restrict to lines
    # starting with "|[[bulbapedia:" or "|[https://bulbapedia".
    names: set[str] = set()
    for line in wikitext.splitlines():
        stripped = line.strip()
        m = TUTOR_BULBA_WIKI.match(stripped) or TUTOR_BULBA_EXTLINK.match(stripped)
        if not m:
            continue
        name = m.group("name").strip()
        if name in SKIP_NAMES:
            continue
        names.add(name)

    names_sorted = sorted(names)
    LOGGER.info("IF wiki: %d distinct moves listed as tutors", len(names_sorted))
    return names_sorted


# ─── Step 2 — Main pipeline ───────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    names = fetch_tutor_names()
    move_ids = load_move_ids(cur, names)
    LOGGER.info("Moves found in DB: %d / %d", len(move_ids), len(names))
    missing = set(names) - set(move_ids)
    if missing:
        LOGGER.warning("IF tutor moves missing from the `move` table (skipped): %s",
                       sorted(missing))

    pokemon_ids = load_pokemon_ids(cur)
    evolutions  = load_evolution_forward(cur)

    inserted = 0
    skipped  = 0

    for name_en, move_id in move_ids.items():
        detail = fetch_move_detail(name_en, logger=LOGGER)
        time.sleep(DELAY)
        if detail is None:
            continue
        is_official, learners = detail
        # For tutors: mark `base` if the move is either an official TM
        # (non-empty machines) or listed as learnable in an official game
        # (non-empty learned_by_pokemon in general). Otherwise it is a
        # tutor added by IF.
        source = "base" if (is_official or learners) else "infinite_fusion"

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

        for pid in targets:
            cur.execute(
                """
                INSERT INTO pokemon_move (pokemon_id, move_id, method, source)
                VALUES (%s, %s, 'tutor', %s)
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
    LOGGER.info("Done — %d new tutor rows inserted, %d already present",
                inserted, skipped)


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    main()
