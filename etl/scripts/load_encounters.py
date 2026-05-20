"""
ETL — Load encounters into location + pokemon_location tables.

Reads : data/encounters_if.json
Writes: location + pokemon_location in PostgreSQL

ID resolution:
  - Wild entries carry `if_id` (= pokemon.id) from the EncounterTable wiki
    template — used directly as the FK.
  - Static / Legendary entries leave `if_id = null` and resolve via
    `pokemon_name` (EN) → pokemon.name_en (lowercased).
"""

from __future__ import annotations

import re
from pathlib import Path

import psycopg2

from etl.utils.db import pg_connection
from etl.utils.io import load_json
from etl.utils.logging import setup_logging
from etl.utils.sql import load_id_map

LOGGER = setup_logging(__name__)

DATA_FILE = Path("data/encounters_if.json")

# method values allowed by DB check constraint
VALID_METHODS = {"wild", "gift", "trade", "static", "fishing", "headbutt"}


def load_encounters(conn) -> None:
    entries: list[dict] = load_json(DATA_FILE)
    LOGGER.info("Loaded %d encounter entries", len(entries))

    with conn.cursor() as cur:
        # Build lookup maps. The encounters JSON carries `if_id` (= pokemon.id);
        # the by_name fallback is used for static/legendary entries that have
        # `if_id == null`.
        cur.execute("SELECT id, name_en FROM pokemon WHERE is_hoenn_only = false")
        valid_ids:   set[int]       = set()
        by_name:     dict[str, int] = {}
        for db_id, name_en in cur.fetchall():
            valid_ids.add(db_id)
            by_name[name_en.lower()] = db_id

        # ── Insert locations ──────────────────────────────────────────────────
        location_names = {e["location_name"] for e in entries if e.get("location_name")}
        for loc_name in sorted(location_names):
            cur.execute(
                "INSERT INTO location (name_en) VALUES (%s) ON CONFLICT (name_en) DO NOTHING",
                (loc_name,),
            )
        conn.commit()

        loc_map = load_id_map(conn, "location", lower=False)
        LOGGER.info("Locations: %d", len(loc_map))

        # ── Insert pokemon_location ───────────────────────────────────────────
        inserted  = 0
        skipped   = 0
        no_pokemon = 0

        for e in entries:
            loc_name = e.get("location_name")
            if not loc_name or loc_name not in loc_map:
                skipped += 1
                continue

            loc_id = loc_map[loc_name]
            method = e.get("method", "wild")
            if method not in VALID_METHODS:
                method = "wild"

            # Split multi-Pokémon names like "Ho-Oh / Lugia" or "Dialga/Palkia/Giratina"
            raw_name = e.get("pokemon_name") or ""
            candidate_names = [n.strip() for n in re.split(r"\s*/\s*", raw_name) if n.strip()] if raw_name else [raw_name]

            # Build notes (shared across all candidates)
            notes_parts = []
            if e.get("encounter_rate"):
                notes_parts.append(f"rate:{e['encounter_rate']}")
            if e.get("level_min") is not None:
                lmin, lmax = e["level_min"], e["level_max"]
                notes_parts.append(f"lv:{lmin}-{lmax}" if lmin != lmax else f"lv:{lmin}")
            if e.get("notes"):
                notes_parts.append(e["notes"])
            notes = " | ".join(notes_parts) or None

            # For multi-Pokémon entries insert one row per Pokémon
            resolved_any = False
            for candidate in candidate_names:
                pid: int | None = None
                if e.get("if_id") and len(candidate_names) == 1:
                    if e["if_id"] in valid_ids:
                        pid = e["if_id"]
                if pid is None:
                    pid = by_name.get(candidate.lower())
                if pid is None:
                    continue
                try:
                    cur.execute(
                        "INSERT INTO pokemon_location (pokemon_id, location_id, method, notes) "
                        "VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (pokemon_id, location_id, method) DO UPDATE SET notes = EXCLUDED.notes",
                        (pid, loc_id, method, notes),
                    )
                    inserted += 1
                    resolved_any = True
                except psycopg2.Error as exc:
                    LOGGER.warning("Insert error for %s @ %s: %s", candidate, loc_name, exc)
                    conn.rollback()
                    skipped += 1

            if not resolved_any:
                LOGGER.debug("Cannot resolve Pokémon: %s", raw_name)
                no_pokemon += 1

        conn.commit()
        LOGGER.info(
            "pokemon_location: %d inserted/updated | %d no_pokemon | %d skipped",
            inserted, no_pokemon, skipped,
        )


def main() -> None:
    LOGGER.info("Connecting to PostgreSQL...")
    with pg_connection() as conn:
        load_encounters(conn)


if __name__ == "__main__":
    main()
