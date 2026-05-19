"""
Correction script — aligns `pokemon.national_id` with the real PokeAPI
national ID, keyed by the English name (from `data/pokedex_if.json`, the
authoritative source for Infinite Fusion numbering).

Context: `extract_stats_pokeapi.py` set `national_id = if_id`, which is
correct up to Celebi (#251) but wrong afterwards — the IF Pokédex diverges
from the national Pokédex (Shinx is if_id 388 but national 403, etc.).
Consequence: ~320 rows have a wrong national_id, hence inconsistent stats,
types, sprites and FR names.

This script fixes only `national_id`. The rest (types, stats, name_fr)
must be re-synced afterwards via the dedicated scripts.

Name normalization: matches the API (`/api/v2/pokemon/{name}`) — all
lowercase, apostrophes and dots removed, ♀/♂ mapped to -f/-m, alternate
forms mapped to their default variant.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEDEX_IF_JSON = Path(__file__).resolve().parents[2] / "data" / "pokedex_if.json"
POKEAPI_SPECIES = "https://pokeapi.co/api/v2/pokemon-species/{}"
REQUEST_DELAY = 0.12  # sec. between requests

# Manual mapping for cases the auto-normalization does not cover.
# Key: name_en as it appears in pokedex_if.json.
# Value: PokeAPI slug OR int national_id (if not in PokeAPI).
MANUAL_OVERRIDES: dict[str, str | int] = {
    # Forms with special characters
    "Nidoran♀": "nidoran-f",
    "Nidoran♂": "nidoran-m",
    "Farfetch'd": "farfetchd",
    "Mr. Mime": "mr-mime",
    "Mime Jr.": "mime-jr",
    "Mr. Rime": "mr-rime",
    "Type: Null": "type-null",
    "Jangmo-o": "jangmo-o",
    "Hakamo-o": "hakamo-o",
    "Kommo-o": "kommo-o",
    "Ho-Oh": "ho-oh",
    "Porygon-Z": "porygon-z",
    "Porygon2": "porygon2",
    "Flabébé": "flabebe",
    # IF-custom forms with no PokeAPI equivalent — leave national_id NULL.
    # (no override added; the script detects the absence and skips.)
}

# Special values: skip entirely (IF-only, triple fusions, custom forms)
SKIP_NAMES: set[str] = set()


def normalize_name(name_en: str) -> str:
    """Convert a name_en to the PokeAPI slug."""
    n = name_en.lower()
    # Strip basic accents for a few cases (é, è, â…)
    n = (
        n.replace("é", "e")
         .replace("è", "e")
         .replace("ê", "e")
         .replace("à", "a")
         .replace("â", "a")
         .replace("ô", "o")
         .replace("û", "u")
         .replace("î", "i")
         .replace("ï", "i")
    )
    n = n.replace("'", "").replace(".", "").replace(" ", "-")
    return n


def resolve_slug(name_en: str) -> str | int | None:
    """Return the PokeAPI slug, a direct national_id, or None if it should be skipped."""
    if name_en in SKIP_NAMES:
        return None
    if name_en in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[name_en]
    return normalize_name(name_en)


def fetch_national_id(slug: str) -> int | None:
    """Query PokeAPI `/pokemon-species/{slug}` (returns the national ID)."""
    try:
        resp = requests.get(POKEAPI_SPECIES.format(slug), timeout=10)
        if resp.status_code != 200:
            return None
        return int(resp.json()["id"])
    except Exception as e:
        LOGGER.warning("PokeAPI error for slug=%s: %s", slug, e)
        return None


def load_pokedex_if() -> dict[int, str]:
    """Load pokedex_if.json → {if_id: name_en}."""
    with POKEDEX_IF_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    return {entry["if_id"]: entry["name_en"] for entry in data}


def fix_national_ids(conn) -> None:
    cur = conn.cursor()

    pokedex_if = load_pokedex_if()
    LOGGER.info("%d entries loaded from pokedex_if.json", len(pokedex_if))

    cur.execute("SELECT id, national_id, name_en FROM pokemon ORDER BY id")
    db_rows = cur.fetchall()
    LOGGER.info("%d Pokémon in DB", len(db_rows))

    updated = unchanged = unresolved = skipped = 0
    unresolved_names: list[tuple[int, str]] = []
    # 1) First pass: collect (pk_id, target_national_id). NO UPDATE is done
    #    here, to avoid temporarily violating the UNIQUE constraint.
    updates: list[tuple[int, int | None]] = []

    for pokemon_id, current_national, name_en in db_rows:
        # Check that the DB name_en actually matches pokedex_if.json
        expected_name = pokedex_if.get(pokemon_id)
        if expected_name and expected_name != name_en:
            LOGGER.warning(
                "Pokémon id=%d: name_en DB='%s' ≠ pokedex_if='%s' — trusting pokedex_if",
                pokemon_id, name_en, expected_name,
            )
            name_en = expected_name

        slug_or_id = resolve_slug(name_en)
        if slug_or_id is None:
            skipped += 1
            updates.append((pokemon_id, None))
            continue

        if isinstance(slug_or_id, int):
            target = slug_or_id
        else:
            target = fetch_national_id(slug_or_id)
            time.sleep(REQUEST_DELAY)
            if target is None:
                unresolved += 1
                unresolved_names.append((pokemon_id, name_en))
                updates.append((pokemon_id, None))  # will be nulled
                continue

        updates.append((pokemon_id, target))

    # 2) Collision resolution — several if_id can point to the same
    #    national_id (e.g. alternate forms). Keep the smallest if_id and
    #    set the others to NULL.
    by_target: dict[int, list[int]] = {}
    for pk_id, target in updates:
        if target is not None:
            by_target.setdefault(target, []).append(pk_id)

    collisions: set[int] = set()
    for target, pks in by_target.items():
        if len(pks) > 1:
            keep = min(pks)
            for pk in pks:
                if pk != keep:
                    collisions.add(pk)
            LOGGER.warning(
                "Collision national_id=%d: keep pk=%d, NULL for %s",
                target, keep, [pk for pk in pks if pk != keep],
            )

    # 3) Apply: first set EVERYTHING to NULL, then set the target values.
    #    Avoids UNIQUE conflicts during the transition.
    cur.execute("UPDATE pokemon SET national_id = NULL")
    LOGGER.info("national_id cleared for all rows")

    for pk_id, target in updates:
        if target is None or pk_id in collisions:
            continue
        cur.execute(
            "UPDATE pokemon SET national_id = %s WHERE id = %s",
            (target, pk_id),
        )
        # Count changed vs unchanged relative to the initial state
        # (before the UPDATE ... = NULL)
        initial = next((n for i, n, _ in db_rows if i == pk_id), None)
        if initial == target:
            unchanged += 1
        else:
            updated += 1

    conn.commit()

    LOGGER.info(
        "Done — %d updated | %d unchanged | %d unresolved | %d skipped | %d collisions NULL",
        updated, unchanged, unresolved, skipped, len(collisions),
    )
    if unresolved_names:
        LOGGER.warning("Unresolved names (handle via override):")
        for pk_id, name in unresolved_names:
            LOGGER.warning("  id=%d name_en=%s", pk_id, name)

    cur.close()


def main() -> None:
    with pg_connection() as conn:
        fix_national_ids(conn)


if __name__ == "__main__":
    main()
