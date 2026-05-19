"""ETL — Enrich missing abilities via PokeAPI.

Target: every Pokémon with no pokemon_ability row that has a national_id
        (required to query PokeAPI).

For each target Pokémon:
  1. Fetch GET /pokemon/{national_id} → ability list (slot, is_hidden, slug)
  2. For each ability:
       a. Check whether it exists in our ability table (by name_en)
       b. Otherwise fetch GET /ability/{slug} for name_en + name_fr,
          then INSERT into ability
  3. INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden)
     ON CONFLICT DO NOTHING

Idempotent: safe to re-run.

Usage:
    docker compose run --rm etl python -m etl.scripts.enrich_missing_abilities
"""

from __future__ import annotations

import time

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

log = setup_logging("enrich_missing_abilities")

POKEAPI = "https://pokeapi.co/api/v2"
DELAY   = 0.15  # seconds between requests


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    time.sleep(DELAY)
    return resp.json()


def _ability_name_en(slug: str) -> tuple[str, str | None]:
    """Return (name_en, name_fr) from PokeAPI for an ability slug."""
    data  = _get(f"{POKEAPI}/ability/{slug}")
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    return names.get("en", slug.replace("-", " ").title()), names.get("fr")


def main() -> None:
    with pg_connection() as conn:
        cur = conn.cursor()

        # Target Pokémon: no ability + known national_id
        cur.execute("""
            SELECT p.id, p.name_en, p.national_id
            FROM pokemon p
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_ability pa WHERE pa.pokemon_id = p.id
            )
              AND p.national_id IS NOT NULL
            ORDER BY p.id
        """)
        targets = cur.fetchall()
        log.info("%d Pokémon without abilities to enrich.", len(targets))

        # Cache ability name_en → ability.id to avoid repeated queries
        cur.execute("SELECT name_en, id FROM ability")
        ability_cache: dict[str, int] = dict(cur.fetchall())

        inserted_abilities = 0
        inserted_pokemon_abilities = 0
        errors = 0

        for pokemon_id, name_en, national_id in targets:
            log.info("  ── %s (IF#%d national=%d)", name_en, pokemon_id, national_id)
            try:
                poke_data = _get(f"{POKEAPI}/pokemon/{national_id}")
            except Exception as exc:
                log.warning("    PokeAPI error for %s: %s", name_en, exc)
                errors += 1
                continue

            for entry in poke_data["abilities"]:
                slot      = entry["slot"]
                is_hidden = entry["is_hidden"]
                slug      = entry["ability"]["name"]

                # Resolve or create the ability in our table
                if slug.replace("-", " ").title() in ability_cache:
                    ability_id = ability_cache[slug.replace("-", " ").title()]
                else:
                    # Fetch official name_en from PokeAPI
                    try:
                        ab_name_en, ab_name_fr = _ability_name_en(slug)
                    except Exception as exc:
                        log.warning("    Ability %s not found: %s", slug, exc)
                        continue

                    if ab_name_en in ability_cache:
                        ability_id = ability_cache[ab_name_en]
                    else:
                        cur.execute(
                            """
                            INSERT INTO ability (name_en, name_fr)
                            VALUES (%s, %s)
                            ON CONFLICT (name_en) DO UPDATE SET name_fr = EXCLUDED.name_fr
                            RETURNING id
                            """,
                            (ab_name_en, ab_name_fr),
                        )
                        row = cur.fetchone()
                        ability_id = row[0]
                        ability_cache[ab_name_en] = ability_id
                        log.info("    + ability created: %s (id=%d)", ab_name_en, ability_id)
                        inserted_abilities += 1

                cur.execute(
                    """
                    INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pokemon_id, slot) DO NOTHING
                    """,
                    (pokemon_id, ability_id, slot, is_hidden),
                )
                if cur.rowcount:
                    inserted_pokemon_abilities += 1

            conn.commit()

        log.info("─" * 50)
        log.info("Abilities created     : %d", inserted_abilities)
        log.info("pokemon_ability rows  : %d", inserted_pokemon_abilities)
        log.info("PokeAPI errors        : %d", errors)
        if errors == 0:
            log.info("✅ Enrichment finished with no errors.")
        else:
            log.warning("⚠️  %d Pokémon not enriched (see logs above).", errors)


if __name__ == "__main__":
    main()
