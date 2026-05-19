"""ETL — Enrichissement des talents manquants via PokeAPI.

Cible : tous les Pokémon qui n'ont aucune entrée dans pokemon_ability
        et qui possèdent un national_id (requis pour interroger PokeAPI).

Pour chaque Pokémon cible :
  1. Fetch GET /pokemon/{national_id} → liste des abilities (slot, is_hidden, slug)
  2. Pour chaque ability :
       a. Vérifie si elle existe dans notre table ability (par name_en)
       b. Sinon, fetch GET /ability/{slug} pour récupérer name_en + name_fr,
          puis INSERT dans ability
  3. INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden)
     ON CONFLICT DO NOTHING

Idempotent : peut être relancé sans risque.

Usage :
    docker compose run --rm etl python -m etl.scripts.enrich_missing_abilities
"""

from __future__ import annotations

import time

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

log = setup_logging("enrich_missing_abilities")

POKEAPI = "https://pokeapi.co/api/v2"
DELAY   = 0.15  # secondes entre chaque requête


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    time.sleep(DELAY)
    return resp.json()


def _ability_name_en(slug: str) -> tuple[str, str | None]:
    """Retourne (name_en, name_fr) depuis PokeAPI pour un slug d'ability."""
    data  = _get(f"{POKEAPI}/ability/{slug}")
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    return names.get("en", slug.replace("-", " ").title()), names.get("fr")


def main() -> None:
    with pg_connection() as conn:
        cur = conn.cursor()

        # Pokémon cibles : sans ability + national_id connu
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
        log.info("%d Pokémon sans ability à enrichir.", len(targets))

        # Cache ability name_en → ability.id pour éviter les requêtes répétées
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
                log.warning("    PokeAPI erreur pour %s : %s", name_en, exc)
                errors += 1
                continue

            for entry in poke_data["abilities"]:
                slot      = entry["slot"]
                is_hidden = entry["is_hidden"]
                slug      = entry["ability"]["name"]

                # Résoudre ou créer l'ability dans notre table
                if slug.replace("-", " ").title() in ability_cache:
                    ability_id = ability_cache[slug.replace("-", " ").title()]
                else:
                    # Fetch name_en officiel depuis PokeAPI
                    try:
                        ab_name_en, ab_name_fr = _ability_name_en(slug)
                    except Exception as exc:
                        log.warning("    Ability %s introuvable : %s", slug, exc)
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
                        log.info("    + ability créée : %s (id=%d)", ab_name_en, ability_id)
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
        log.info("Abilities créées     : %d", inserted_abilities)
        log.info("pokemon_ability rows : %d", inserted_pokemon_abilities)
        log.info("Erreurs PokeAPI      : %d", errors)
        if errors == 0:
            log.info("✅ Enrichissement terminé sans erreur.")
        else:
            log.warning("⚠️  %d Pokémon non enrichis (voir logs ci-dessus).", errors)


if __name__ == "__main__":
    main()
