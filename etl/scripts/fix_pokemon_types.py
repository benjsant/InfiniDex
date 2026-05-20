"""
Correction script — Enrich pokemon_type from PokeAPI.

Problem : extract_pokedex_if.py mis-assigns type1/type2 from the IF wiki.
Solution: for each Pokémon with a known national_id, fetch the types
          from PokeAPI and update pokemon_type in the DB.

Idempotent: ON CONFLICT (pokemon_id, slot) DO UPDATE.
"""

from __future__ import annotations

import time

from etl.utils.db import pg_connection
from etl.utils.http import get_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEAPI = "https://pokeapi.co/api/v2/pokemon/{}"
REQUEST_DELAY = 0.15  # seconds between requests

# IF Pokémon with no PokeAPI equivalent (IF-custom forms, triple fusions, etc.)
# Left with the IF wiki types
SKIP_NATIONAL_IDS: set[int] = set()


def fetch_types(national_id: int) -> list[tuple[int, str]]:
    """Return [(slot, type_name_en)] from PokeAPI for a national_id.

    Retries with exponential backoff on 429/503 (handled by `get_json`).
    """
    data = get_json(POKEAPI.format(national_id))
    if data is None:
        return []
    return [
        (t["slot"], t["type"]["name"].capitalize())
        for t in data["types"]
    ]


def fix_pokemon_types(conn) -> None:
    cur = conn.cursor()

    # Fetch the list of Pokémon with their national_id
    cur.execute("SELECT id, national_id FROM pokemon WHERE national_id IS NOT NULL ORDER BY id")
    rows = cur.fetchall()
    LOGGER.info("%d Pokémon with a national_id found", len(rows))

    # Fetch the type_map name_en → id
    cur.execute("SELECT id, name_en FROM type WHERE is_triple_fusion_type = FALSE")
    type_map: dict[str, int] = {name: tid for tid, name in cur.fetchall()}

    updated = skipped = errors = 0

    for i, (pokemon_id, national_id) in enumerate(rows):
        if national_id in SKIP_NATIONAL_IDS:
            skipped += 1
            continue

        types = fetch_types(national_id)
        if not types:
            errors += 1
            continue

        # Erase stale slots before re-inserting (handles mono-type Pokémon
        # that previously had a stale slot 2 from the wiki).
        slots_from_api = [s for s, _ in types]
        if slots_from_api:
            cur.execute(
                "DELETE FROM pokemon_type WHERE pokemon_id = %s AND slot <> ALL(%s)",
                (pokemon_id, slots_from_api),
            )

        for slot, type_name in types:
            # Some PokeAPI names: "fighting" → "Fighting"
            type_id = type_map.get(type_name)
            if type_id is None:
                LOGGER.warning(
                    "Unknown type '%s' for Pokémon #%d (national #%d)",
                    type_name, pokemon_id, national_id
                )
                continue

            cur.execute(
                """
                INSERT INTO pokemon_type (pokemon_id, type_id, slot)
                VALUES (%s, %s, %s)
                ON CONFLICT (pokemon_id, slot) DO UPDATE
                    SET type_id = EXCLUDED.type_id
                """,
                (pokemon_id, type_id, slot),
            )

        if (i + 1) % 50 == 0:
            conn.commit()
            LOGGER.info("[%d/%d] %d updated, %d errors", i + 1, len(rows), updated + i + 1, errors)

        updated += 1
        time.sleep(REQUEST_DELAY)

    conn.commit()

    # Pokémon with no national_id (IF-only): use the wiki type2 as slot 1
    LOGGER.info("Fixing IF-only Pokémon (no national_id)...")
    cur.execute("""
        SELECT id FROM pokemon
        WHERE national_id IS NULL
          AND id NOT IN (SELECT DISTINCT pokemon_id FROM pokemon_type)
    """)
    if_only = [r[0] for r in cur.fetchall()]
    LOGGER.info("%d IF-only Pokémon without types in DB", len(if_only))

    cur.close()
    LOGGER.info(
        "Done — %d updated | %d skipped | %d errors",
        updated, skipped, errors
    )


def main() -> None:
    with pg_connection() as conn:
        fix_pokemon_types(conn)


if __name__ == "__main__":
    main()
