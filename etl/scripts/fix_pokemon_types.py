"""
Script de correction — Enrich pokemon_type depuis PokeAPI.

Problème : extract_pokedex_if.py assigne mal type1/type2 depuis le wiki IF.
Solution  : pour chaque Pokémon avec national_id connu, récupère les types
            depuis PokeAPI et met à jour pokemon_type en base.

Idempotent : ON CONFLICT (pokemon_id, slot) DO UPDATE.
"""

from __future__ import annotations

import time

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEAPI = "https://pokeapi.co/api/v2/pokemon/{}"
REQUEST_DELAY = 0.15  # secondes entre requêtes

# Pokémon IF sans équivalent PokeAPI (formes IF custom, triple fusions, etc.)
# On les laisse avec les types du wiki IF
SKIP_NATIONAL_IDS: set[int] = set()


def fetch_types(national_id: int, retries: int = 3) -> list[tuple[int, str]]:
    """Retourne [(slot, type_name_en)] depuis PokeAPI pour un national_id.

    Retente jusqu'à `retries` fois en cas de 429 ou d'erreur réseau,
    avec backoff exponentiel (2s, 4s, 8s).
    """
    for attempt in range(retries):
        try:
            resp = requests.get(POKEAPI.format(national_id), timeout=15)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                LOGGER.warning("PokeAPI 429 pour #%d — attente %ds", national_id, wait)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                LOGGER.warning("PokeAPI HTTP %d pour #%d", resp.status_code, national_id)
                return []
            data = resp.json()
            return [
                (t["slot"], t["type"]["name"].capitalize())
                for t in data["types"]
            ]
        except Exception as e:
            wait = 2 ** (attempt + 1)
            LOGGER.warning("PokeAPI error pour #%d (tentative %d/%d) : %s — attente %ds",
                           national_id, attempt + 1, retries, e, wait)
            if attempt < retries - 1:
                time.sleep(wait)
    return []


def fix_pokemon_types(conn) -> None:
    cur = conn.cursor()

    # Récupère la liste des Pokémon avec leur national_id
    cur.execute("SELECT id, national_id FROM pokemon WHERE national_id IS NOT NULL ORDER BY id")
    rows = cur.fetchall()
    LOGGER.info("%d Pokémon avec national_id trouvés", len(rows))

    # Récupère le type_map name_en → id
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
            # Certains noms PokeAPI : "fighting" → "Fighting"
            type_id = type_map.get(type_name)
            if type_id is None:
                LOGGER.warning(
                    "Type inconnu '%s' pour Pokémon #%d (national #%d)",
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
            LOGGER.info("[%d/%d] %d mis à jour, %d erreurs", i + 1, len(rows), updated + i + 1, errors)

        updated += 1
        time.sleep(REQUEST_DELAY)

    conn.commit()

    # Pokémon sans national_id (IF-only) : utilise type2 du wiki comme slot 1
    LOGGER.info("Correction des Pokémon IF-only (sans national_id)...")
    cur.execute("""
        SELECT id FROM pokemon
        WHERE national_id IS NULL
          AND id NOT IN (SELECT DISTINCT pokemon_id FROM pokemon_type)
    """)
    if_only = [r[0] for r in cur.fetchall()]
    LOGGER.info("%d Pokémon IF-only sans types en base", len(if_only))

    cur.close()
    LOGGER.info(
        "Terminé — %d mis à jour | %d ignorés | %d erreurs",
        updated, skipped, errors
    )


def main() -> None:
    with pg_connection() as conn:
        fix_pokemon_types(conn)


if __name__ == "__main__":
    main()
