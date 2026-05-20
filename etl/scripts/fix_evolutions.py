"""
Correction script — re-fetch evolution chains for every Pokémon using the
now-correct `national_id` (set by `fix_national_ids.py`).

Context: `extract_stats_pokeapi.py` sets `national_id = if_id`, which means
for IF Pokémon with `if_id > 251` the wrong PokeAPI Pokémon was queried.
The evolution chains saved into `evolutions_base.json` therefore belonged
to the wrong species (Mime Jr (if_id=258) recorded Mudkip's chain etc.),
so the post-Kanto chains were silently missing from `pokemon_evolution`.

This script reuses the same chain-parsing logic as `extract_stats_pokeapi`,
deduplicates chains by URL (most chains are shared between 2-3 species),
and resolves the PokeAPI slug → `pokemon.id` via `pokeapi_move_slug` so
special-character names ("Mime Jr.", "Nidoran♀", "Flabébé", …) match.

Idempotent: ON CONFLICT DO NOTHING on every insert.
"""

from __future__ import annotations

import time
from pathlib import Path

from etl.utils.db import pg_connection
from etl.utils.http import USER_AGENT, get_json
from etl.utils.io import load_json
from etl.utils.logging import setup_logging
from etl.utils.pokeapi_moves import pokeapi_move_slug

LOGGER = setup_logging(__name__)

POKEAPI_SPECIES = "https://pokeapi.co/api/v2/pokemon-species/{}"
REQUEST_DELAY   = 0.1

IF_OVERRIDES_FILE = Path(__file__).parent / "data" / "if_evolution_overrides.json"

_TRIGGER_MAP = {
    "level-up":          "level_up",
    "use-item":          "use_item",
    "trade":             "trade",
    "shed":              "other",
    "spin":              "other",
    "tower-of-darkness": "other",
    "tower-of-waters":   "other",
    "agile-style-move":  "other",
    "strong-style-move": "other",
    "recoil-damage":     "other",
    "take-damage":       "other",
    "other":             "other",
}


def _parse_chain_node(node: dict, results: list[dict]) -> None:
    from_name = node["species"]["name"]
    for evo in node.get("evolves_to", []):
        into_name = evo["species"]["name"]
        for detail in evo.get("evolution_details", []):
            trigger = detail.get("trigger", {}).get("name", "other")
            results.append({
                "from_name": from_name,
                "into_name": into_name,
                "trigger":   _TRIGGER_MAP.get(trigger, "other"),
                "min_level": detail.get("min_level"),
                "item":      (detail.get("item") or {}).get("name"),
            })
        _parse_chain_node(evo, results)


def _load_if_override_keys() -> set[tuple[str, str]]:
    """Return `{(from, into)}` pairs handled by load_db.load_evolutions's
    IF-override branch. We must NOT re-insert a base row for those — the
    override already replaces the base evolution with IF-specific conditions.
    """
    entries = load_json(IF_OVERRIDES_FILE)
    return {(e["from"], e["into"]) for e in entries}


def fix_evolutions(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name_en, national_id FROM pokemon "
        "WHERE national_id IS NOT NULL ORDER BY id"
    )
    pokemon_rows = cur.fetchall()
    LOGGER.info("%d Pokémon with national_id", len(pokemon_rows))

    # slug → pokemon.id resolver (handles ♀/♂, accents, etc. via pokeapi_move_slug)
    by_slug: dict[str, int] = {pokeapi_move_slug(name): pid for pid, name, _ in pokemon_rows}
    by_name: dict[str, int] = {name.lower(): pid for pid, name, _ in pokemon_rows}

    def resolve(key: str) -> int | None:
        k = key.lower()
        return by_slug.get(k) or by_name.get(k)

    if_override_keys = _load_if_override_keys()

    # Dedupe chains we've already processed (one chain spans several species)
    seen_chain_urls: set[str] = set()
    pairs: list[dict] = []

    for i, (pk_id, name_en, national_id) in enumerate(pokemon_rows, start=1):
        species = get_json(POKEAPI_SPECIES.format(national_id))
        time.sleep(REQUEST_DELAY)
        if not species:
            LOGGER.warning("species not found for %s (national=%d)", name_en, national_id)
            continue
        chain_url = (species.get("evolution_chain") or {}).get("url")
        if not chain_url or chain_url in seen_chain_urls:
            continue
        seen_chain_urls.add(chain_url)
        chain_data = get_json(chain_url)
        time.sleep(REQUEST_DELAY)
        if not chain_data:
            continue
        _parse_chain_node(chain_data["chain"], pairs)

        if i % 50 == 0:
            LOGGER.info(
                "[%d/%d] %d unique chains, %d pairs collected so far",
                i, len(pokemon_rows), len(seen_chain_urls), len(pairs),
            )

    # Insert (skipping if_override keys — those rows are owned by load_db.load_evolutions)
    inserted = duplicate = unresolved = override_skipped = 0
    for pair in pairs:
        if (pair["from_name"], pair["into_name"]) in if_override_keys:
            override_skipped += 1
            continue
        from_id = resolve(pair["from_name"])
        into_id = resolve(pair["into_name"])
        if not from_id or not into_id:
            unresolved += 1
            continue
        cur.execute(
            """
            INSERT INTO pokemon_evolution
            (pokemon_id, evolves_into_id, trigger_type, min_level, item_name_en)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (pokemon_id, evolves_into_id, trigger_type, COALESCE(item_name_en, ''))
            DO NOTHING
            """,
            (from_id, into_id, pair["trigger"], pair["min_level"], pair["item"]),
        )
        if cur.rowcount:
            inserted += 1
        else:
            duplicate += 1

    conn.commit()
    cur.close()
    LOGGER.info(
        "Done — %d new rows | %d already present | %d unresolved | %d if_override skipped "
        "(out of %d unique chains)",
        inserted, duplicate, unresolved, override_skipped, len(seen_chain_urls),
    )


def main() -> None:
    with pg_connection() as conn:
        fix_evolutions(conn)


if __name__ == "__main__":
    main()
