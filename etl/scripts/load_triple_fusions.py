"""
ETL — Load triple fusions into DB.

Reads : data/triple_fusions_if.json
Writes:
  triple_fusion            (main row, 1 per triple)
  triple_fusion_component  (3 base pokemon per triple)
  triple_fusion_type       (1 to 3 standard types — custom combo types skipped)
  triple_fusion_ability    (1 to 3 abilities, is_hidden flagged)

Idempotence: all 4 tables wiped then reinserted.

Notes:
  - Custom IF combo types like "[Ice/Fire/Electric]" are not in the `type`
    table (only the 18 canonical types are).  They are skipped and logged.
  - A few wiki spellings are aliased before lookup.
"""

from __future__ import annotations

import re
from pathlib import Path

from etl.utils.db import pg_connection
from etl.utils.io import load_json
from etl.utils.logging import setup_logging
from etl.utils.sql import load_id_map

LOGGER = setup_logging(__name__)

DATA_FILE = Path("data/triple_fusions_if.json")

# Wiki spelling → pokemon.name_en canonical spelling
COMPONENT_ALIASES = {
    "Feraligator": "Feraligatr",  # wiki typo
    "Treeko":      "Treecko",     # wiki typo
}

# Wiki spelling → ability.name_en canonical spelling
ABILITY_ALIASES = {
    "Syncronize": "Synchronize",  # wiki typo
}


# The 8 "unique types" defined by Infinite Fusion — each has its own defense
# profile (see Unique_Type_Defense_Chart image on the wiki).  They are stored
# as single rows in the `type` table with is_triple_fusion_type=true.
UNIQUE_IF_TYPES: list[tuple[str, str]] = [
    # (name_en,                name_fr)
    ("Ice/Fire/Electric",      "Glace/Feu/Électrik"),
    ("Fire/Water/Electric",    "Feu/Eau/Électrik"),
    ("Water/Ground/Flying",    "Eau/Sol/Vol"),
    ("Ghost/Steel/Water",      "Spectre/Acier/Eau"),
    ("Fire/Water/Grass",       "Feu/Eau/Plante"),
    ("Grass/Steel",            "Plante/Acier"),
    ("Bug/Steel/Psychic",      "Insecte/Acier/Psy"),
    ("Ice/Rock/Steel",         "Glace/Roche/Acier"),
]
UNIQUE_IF_TYPE_NAMES: set[str] = {name for name, _ in UNIQUE_IF_TYPES}


def split_type_string(type_str: str) -> list[str]:
    """
    Parse a triple-fusion type string into ordered slot tokens.

    A unique IF type (`Ice/Fire/Electric`, `Fire/Water/Grass`, …) occupies
    a single slot even though it visually contains slashes.  Bracket
    notation in the wiki (`[Ice/Fire/Electric]/Flying`) is a hint that the
    bracketed part is a unique type combined with a standard type.

    Examples:
      'Fire/Water/Electric'        → ['Fire/Water/Electric']         (unique)
      'Water/Ground/Flying'        → ['Water/Ground/Flying']         (unique)
      'Fire/Water/Grass'           → ['Fire/Water/Grass']            (unique)
      '[Ice/Fire/Electric]/Flying' → ['Ice/Fire/Electric', 'Flying']
      'Dragon/[Ghost/Steel/Water]' → ['Dragon', 'Ghost/Steel/Water']
      'Psychic/[Grass/Steel]'      → ['Psychic', 'Grass/Steel']
      'Dragon/[Ice/Fire/Electric]' → ['Dragon', 'Ice/Fire/Electric']
    """
    if not type_str:
        return []

    # Split on bracket boundaries: parts at odd indices are bracketed content,
    # parts at even indices are the surrounding standard-type text.
    parts = re.split(r"\[([^\]]+)\]", type_str)
    tokens: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside brackets → always a single unique-type slot
            tokens.append(part.strip())
            continue
        clean = part.strip().strip("/").strip()
        if not clean:
            continue
        # Outside brackets: if the whole segment matches a known unique IF
        # type, keep it as one slot (handles unbracketed `Fire/Water/Grass`
        # for starter triples and `Ice/Rock/Steel` for Regiregi, etc.).
        if clean in UNIQUE_IF_TYPE_NAMES:
            tokens.append(clean)
        else:
            for tok in clean.split("/"):
                tok = tok.strip()
                if tok:
                    tokens.append(tok)
    return tokens


def seed_unique_if_types(cur, type_by_name: dict[str, int]) -> int:
    """Upsert the 8 unique IF types. Returns number of newly created rows."""
    created = 0
    for name_en, name_fr in UNIQUE_IF_TYPES:
        if name_en in type_by_name:
            continue
        cur.execute(
            """INSERT INTO type (name_en, name_fr, is_triple_fusion_type)
               VALUES (%s, %s, TRUE)
               ON CONFLICT (name_en) DO UPDATE SET
                   name_fr = EXCLUDED.name_fr,
                   is_triple_fusion_type = TRUE
               RETURNING id""",
            (name_en, name_fr),
        )
        type_by_name[name_en] = cur.fetchone()[0]
        created += 1
    return created


def load_triple_fusions(conn) -> None:
    entries: list[dict] = load_json(DATA_FILE)
    LOGGER.info("Loaded %d triple fusion entries from JSON", len(entries))

    pokemon_by_name = load_id_map(conn, "pokemon", lower=False)
    ability_by_name = load_id_map(conn, "ability", lower=False)
    type_by_name    = load_id_map(conn, "type",    lower=False)

    with conn.cursor() as cur:
        # ── Seed unique IF types (8 custom combos) ───────────────────────────
        created = seed_unique_if_types(cur, type_by_name)
        if created:
            LOGGER.info("Seeded %d unique IF types in `type` table", created)

        # ── Wipe triple_fusion_* for idempotence ─────────────────────────────
        cur.execute("DELETE FROM triple_fusion_ability")
        cur.execute("DELETE FROM triple_fusion_type")
        cur.execute("DELETE FROM triple_fusion_component")
        cur.execute("DELETE FROM triple_fusion")
        cur.execute("ALTER SEQUENCE triple_fusion_id_seq RESTART WITH 1")
        LOGGER.info("Wiped existing triple fusion rows (sequence reset to 1)")

        # ── Pass 1 : insert triple_fusion rows (no evolves_from yet) ─────────
        id_by_name: dict[str, int] = {}
        for e in entries:
            s = e["stats"]
            cur.execute(
                """INSERT INTO triple_fusion
                   (name_en, name_fr, hp, attack, defense,
                    sp_attack, sp_defense, speed, steps_to_hatch, sprite_path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    e["name_en"],
                    None,  # name_fr — IF-specific names, no FR translation
                    s["hp"], s["attack"], s["defense"],
                    s["sp_attack"], s["sp_defense"], s["speed"],
                    e.get("steps_to_hatch"),
                    None,  # sprite_path — triple sprites not shipped
                ),
            )
            id_by_name[e["name_en"]] = cur.fetchone()[0]

        LOGGER.info("Inserted %d triple_fusion rows", len(id_by_name))

        # ── Pass 2 : resolve evolves_from_id + evolution_level ───────────────
        evo_updates = 0
        for e in entries:
            parent_name = e.get("evolves_from")
            if parent_name and parent_name in id_by_name:
                cur.execute(
                    "UPDATE triple_fusion SET evolves_from_id = %s, evolution_level = %s WHERE id = %s",
                    (id_by_name[parent_name], e.get("evolution_level"), id_by_name[e["name_en"]]),
                )
                evo_updates += 1
        LOGGER.info("Resolved %d evolution links", evo_updates)

        # ── Components ───────────────────────────────────────────────────────
        comp_rows = 0
        comp_missing = 0
        for e in entries:
            tf_id = id_by_name[e["name_en"]]
            for pos, comp_name in enumerate(e["components"], start=1):
                canonical = COMPONENT_ALIASES.get(comp_name, comp_name)
                pid = pokemon_by_name.get(canonical)
                if pid is None:
                    LOGGER.warning("Unknown component %r for %s", comp_name, e["name_en"])
                    comp_missing += 1
                    continue
                cur.execute(
                    """INSERT INTO triple_fusion_component
                       (triple_fusion_id, pokemon_id, position)
                       VALUES (%s, %s, %s)""",
                    (tf_id, pid, pos),
                )
                comp_rows += 1
        LOGGER.info("triple_fusion_component: %d rows (%d missing)", comp_rows, comp_missing)

        # ── Types ────────────────────────────────────────────────────────────
        type_rows = 0
        type_missing = 0
        for e in entries:
            tf_id = id_by_name[e["name_en"]]
            tokens = split_type_string(e.get("type") or "")
            for slot, token in enumerate(tokens, start=1):
                tid = type_by_name.get(token)
                if tid is None:
                    LOGGER.warning("Unknown type %r for %s", token, e["name_en"])
                    type_missing += 1
                    continue
                cur.execute(
                    """INSERT INTO triple_fusion_type (triple_fusion_id, type_id, slot)
                       VALUES (%s, %s, %s)""",
                    (tf_id, tid, slot),
                )
                type_rows += 1
        LOGGER.info("triple_fusion_type: %d rows (%d missing)", type_rows, type_missing)

        # ── Abilities ────────────────────────────────────────────────────────
        ab_rows = 0
        ab_missing = 0
        for e in entries:
            tf_id = id_by_name[e["name_en"]]
            # Dedupe consecutive duplicates (e.g. Deosectwo has "Pressure" listed twice)
            seen: set[str] = set()
            slot = 0
            for ab in e.get("abilities", []):
                canonical = ABILITY_ALIASES.get(ab["name"], ab["name"])
                if canonical in seen:
                    continue
                seen.add(canonical)
                aid = ability_by_name.get(canonical)
                if aid is None:
                    LOGGER.warning("Unknown ability %r for %s", ab["name"], e["name_en"])
                    ab_missing += 1
                    continue
                slot += 1
                if slot > 3:   # check constraint limits slot to 1-3
                    break
                cur.execute(
                    """INSERT INTO triple_fusion_ability
                       (triple_fusion_id, ability_id, slot, is_hidden)
                       VALUES (%s, %s, %s, %s)""",
                    (tf_id, aid, slot, ab.get("is_hidden", False)),
                )
                ab_rows += 1
        LOGGER.info("triple_fusion_ability: %d rows (%d missing)", ab_rows, ab_missing)

        conn.commit()


def main() -> None:
    LOGGER.info("Connecting to PostgreSQL...")
    with pg_connection() as conn:
        load_triple_fusions(conn)


if __name__ == "__main__":
    main()
