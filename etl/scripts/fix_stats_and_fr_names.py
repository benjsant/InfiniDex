"""
Correction script — re-syncs stats + name_fr + base_experience with the
`national_id` (now correct after `fix_national_ids.py`).

The original script (extract_stats_pokeapi.py) set `national_id = if_id`,
which mixed up stats and French names for ~320 rows. Now that
`national_id` is correct in the DB, re-fetch directly from PokeAPI.

No intermediate file: reads/writes the DB directly.
"""

from __future__ import annotations

from etl.utils.db import pg_connection
from etl.utils.http import get_json, prefetch_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEAPI_POKEMON = "https://pokeapi.co/api/v2/pokemon/{}"
POKEAPI_SPECIES = "https://pokeapi.co/api/v2/pokemon-species/{}"

STAT_MAP = {
    "hp":              "hp",
    "attack":          "attack",
    "defense":         "defense",
    "special-attack":  "sp_attack",
    "special-defense": "sp_defense",
    "speed":           "speed",
}


def fetch_pokemon(national_id: int) -> dict | None:
    return get_json(POKEAPI_POKEMON.format(national_id))


def fetch_species(national_id: int) -> dict | None:
    return get_json(POKEAPI_SPECIES.format(national_id))


def extract_name_fr(species: dict) -> str | None:
    for entry in species.get("names", []):
        if entry["language"]["name"] == "fr":
            return entry["name"]
    return None


def extract_stats(pokemon: dict) -> dict[str, int]:
    return {
        STAT_MAP[s["stat"]["name"]]: s["base_stat"]
        for s in pokemon["stats"]
        if s["stat"]["name"] in STAT_MAP
    }


def fix(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, national_id, name_en FROM pokemon "
        "WHERE national_id IS NOT NULL ORDER BY id"
    )
    rows = cur.fetchall()
    LOGGER.info("%d Pokémon to update", len(rows))

    # Warm the shared HTTP cache concurrently; the loop below reads from it.
    prefetch_json(
        [POKEAPI_POKEMON.format(nid) for _, nid, _ in rows]
        + [POKEAPI_SPECIES.format(nid) for _, nid, _ in rows]
    )

    updated = errors = 0
    for i, (pokemon_id, national_id, name_en) in enumerate(rows, start=1):
        poke = fetch_pokemon(national_id)
        if not poke:
            LOGGER.warning("PokeAPI /pokemon/%d failed for id=%d (%s)",
                           national_id, pokemon_id, name_en)
            errors += 1
            continue

        species = fetch_species(national_id)
        name_fr = extract_name_fr(species) if species else None

        stats = extract_stats(poke)
        base_xp = poke.get("base_experience")

        cur.execute(
            """
            UPDATE pokemon SET
                hp              = %(hp)s,
                attack          = %(attack)s,
                defense         = %(defense)s,
                sp_attack       = %(sp_attack)s,
                sp_defense      = %(sp_defense)s,
                speed           = %(speed)s,
                base_experience = %(base_xp)s,
                name_fr         = COALESCE(%(name_fr)s, name_fr)
            WHERE id = %(id)s
            """,
            {
                **stats,
                "base_xp": base_xp,
                "name_fr": name_fr,
                "id":      pokemon_id,
            },
        )
        updated += 1

        if i % 50 == 0:
            conn.commit()
            LOGGER.info("[%d/%d] %d updated, %d errors", i, len(rows), updated, errors)

    conn.commit()
    cur.close()
    LOGGER.info("Done — %d updated | %d errors", updated, errors)


def main() -> None:
    with pg_connection() as conn:
        fix(conn)


if __name__ == "__main__":
    main()
