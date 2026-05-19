"""
ETL Step 8 — Load all transformed data into PostgreSQL.

Loading order respects FK constraints:
  1. generation
  2. type
  3. ability
  4. move
  5. tm
  6. pokemon
  7. pokemon_type
  8. pokemon_ability
  9. pokemon_evolution
  10. location
  11. pokemon_location
  12. pokemon_move

All inserts use ON CONFLICT DO NOTHING → idempotent / re-runnable.

Sources:
  data/pokedex_if.json
  data/pokemon_stats.json
  data/moves_if.json
  data/tms_if.json
  data/abilities_if.json
  data/locations_if.json
  data/movesets_merged.json
  data/evolutions_base.json
"""

from __future__ import annotations

from pathlib import Path

from psycopg2.extras import execute_values

from etl.utils.db import pg_connection
from etl.utils.io import load_json
from etl.utils.logging import setup_logging
from etl.utils.sql import load_id_map

LOGGER = setup_logging(__name__)

# IF-specific evolution rules (from Differences_with_the_official_games wiki page)
# are curated data, not code — kept in etl/scripts/data/if_evolution_overrides.json
# and indexed below by (from_name_en, into_name_en). Each value is a list of
# alternative {trigger, min_level, item, notes} conditions.
IF_EVO_OVERRIDES_FILE = Path(__file__).parent / "data" / "if_evolution_overrides.json"


def _load_if_evolution_overrides() -> dict[tuple[str, str], list[dict]]:
    entries = load_json(IF_EVO_OVERRIDES_FILE)
    return {(e["from"], e["into"]): e["conditions"] for e in entries}


# ─── Load functions per table ─────────────────────────────────────────────────

def load_generations(conn) -> dict[int, int]:
    """Seed generation table. Returns {gen_number: db_id}."""
    GENS = [
        (1, "generation-i",   "génération-i"),
        (2, "generation-ii",  "génération-ii"),
        (3, "generation-iii", "génération-iii"),
        (4, "generation-iv",  "génération-iv"),
        (5, "generation-v",   "génération-v"),
        (6, "generation-vi",  "génération-vi"),
        (7, "generation-vii", "génération-vii"),
    ]
    with conn.cursor() as cur:
        for num, name_en, name_fr in GENS:
            cur.execute(
                "INSERT INTO generation (name_en, name_fr) VALUES (%s, %s) "
                "ON CONFLICT (name_en) DO NOTHING",
                (name_en, name_fr),
            )
        conn.commit()
        cur.execute("SELECT id, name_en FROM generation")
        rows = cur.fetchall()

    gen_map = {}
    for db_id, name_en in rows:
        num = int(name_en.split("-")[-1].replace("i", "1").replace("v", "5").replace("x", "10"))
        # Use Roman numeral position for mapping
        roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}
        suffix = name_en.split("-")[-1]
        gen_map[roman.get(suffix, 0)] = db_id

    LOGGER.info("Loaded %d generations", len(gen_map))
    return gen_map


def load_types(conn, moves: list[dict]) -> dict[str, int]:
    """Seed type table from move data. Returns {name_en_lower: db_id}.

    Note: the 8 unique IF triple-fusion types (Ice/Fire/Electric, …) are
    seeded separately by ``load_triple_fusions.py`` with
    ``is_triple_fusion_type=true`` and FR names.
    """
    # Capitalize to match the canonical form inserted by seed_type_effectiveness
    type_names_en = {m["type_en"].capitalize() for m in moves if m.get("type_en")}

    with conn.cursor() as cur:
        for name in sorted(type_names_en):
            cur.execute(
                "INSERT INTO type (name_en) VALUES (%s) "
                "ON CONFLICT (name_en) DO NOTHING",
                (name,),
            )
        conn.commit()

    type_map = load_id_map(conn, "type")
    LOGGER.info("Loaded %d types", len(type_map))
    return type_map


def load_abilities(conn, abilities: list[dict]) -> dict[str, int]:
    """Returns {name_en_lower: db_id}."""
    with conn.cursor() as cur:
        for ab in abilities:
            cur.execute(
                "INSERT INTO ability (name_en, name_fr, description_en, description_fr) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (name_en) DO UPDATE "
                "SET name_fr = EXCLUDED.name_fr, description_en = EXCLUDED.description_en, "
                "description_fr = EXCLUDED.description_fr",
                (ab["name_en"], ab.get("name_fr"), ab.get("description_en"), ab.get("description_fr")),
            )
        conn.commit()

    ability_map = load_id_map(conn, "ability")
    LOGGER.info("Loaded %d abilities", len(ability_map))
    return ability_map


def load_moves(conn, moves: list[dict], type_map: dict) -> dict[str, int]:
    """Returns {name_en_lower: db_id}."""
    with conn.cursor() as cur:
        for m in moves:
            type_id = type_map.get(m.get("type_en", "").lower())
            if not type_id:
                LOGGER.warning("Unknown type '%s' for move '%s'", m.get("type_en"), m["name_en"])
                continue
            cur.execute(
                """INSERT INTO move
                   (name_en, name_fr, type_id, category, power, accuracy, pp,
                    description_en, description_fr, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (name_en) DO UPDATE SET
                     name_fr = EXCLUDED.name_fr,
                     description_fr = EXCLUDED.description_fr""",
                (
                    m["name_en"], m.get("name_fr"), type_id,
                    m.get("category", "Status"),
                    m.get("power"), m.get("accuracy"), m.get("pp", 1),
                    m.get("description_en"), m.get("description_fr"),
                    m.get("source", "base"),
                ),
            )
        conn.commit()

    move_map = load_id_map(conn, "move")
    LOGGER.info("Loaded %d moves", len(move_map))
    return move_map


def load_tms(conn, tms: list[dict], move_map: dict) -> None:
    with conn.cursor() as cur:
        for tm in tms:
            move_id = move_map.get(tm["move_name"].lower())
            if not move_id:
                LOGGER.warning("TM%02d: move '%s' not found", tm["number"], tm["move_name"])
                continue
            cur.execute(
                "INSERT INTO tm (number, move_id) VALUES (%s, %s) "
                "ON CONFLICT (number) DO NOTHING",
                (tm["number"], move_id),
            )
        conn.commit()
    LOGGER.info("Loaded %d TMs", len(tms))


def load_pokemon(conn, pokedex: list[dict], stats: list[dict], gen_map: dict) -> dict[int, int]:
    """Returns {if_id: db_id} (db_id = if_id since it's the PK)."""
    stats_by_id = {s["if_id"]: s for s in stats}

    with conn.cursor() as cur:
        for entry in pokedex:
            if_id   = entry["if_id"]
            s       = stats_by_id.get(if_id, {})
            gen_id  = gen_map.get(entry.get("generation", 1), 1)

            cur.execute(
                """INSERT INTO pokemon
                   (id, national_id, name_en, name_fr, generation_id,
                    hp, attack, defense, sp_attack, sp_defense, speed,
                    base_experience, is_hoenn_only, sprite_path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       sprite_path = EXCLUDED.sprite_path""",
                (
                    if_id,
                    s.get("national_id"),
                    entry["name_en"],
                    s.get("name_fr"),
                    gen_id,
                    s.get("hp", 1),
                    s.get("attack", 1),
                    s.get("defense", 1),
                    s.get("sp_attack", 1),
                    s.get("sp_defense", 1),
                    s.get("speed", 1),
                    s.get("base_experience"),
                    entry.get("is_hoenn_only", False),
                    f"{if_id}.{if_id}.png",
                ),
            )
        conn.commit()
    LOGGER.info("Loaded %d Pokémon", len(pokedex))
    return {e["if_id"]: e["if_id"] for e in pokedex}


def load_pokemon_types(conn, pokedex: list[dict], type_map: dict) -> None:
    """Rebuild pokemon_type from the IF Pokédex.

    Builds the full intended slot set in Python, then DELETE + bulk-insert
    atomically (single commit). Replaces the old ON CONFLICT DO NOTHING
    pattern, which silently dropped any (pokemon_id, slot) collision: with a
    plain INSERT a real collision now raises a DB IntegrityError instead of
    vanishing. Dropped rows (unknown type / mono-type dedup) are logged.
    """
    rows: list[tuple[int, int, int]] = []
    for entry in pokedex:
        if_id = entry["if_id"]
        t1 = (entry.get("type1") or "").lower() or None
        t2 = (entry.get("type2") or "").lower() or None
        # Skip slot 2 if identical to slot 1 (wiki IF often duplicates for mono-type)
        if t2 and t1 and t2 == t1:
            t2 = None
        for slot, type_key in ((1, t1), (2, t2)):
            if not type_key:
                continue
            type_id = type_map.get(type_key)
            if not type_id:
                LOGGER.warning("Unknown type '%s' for Pokémon #%d", type_key, if_id)
                continue
            rows.append((if_id, type_id, slot))

    with conn.cursor() as cur:
        cur.execute("DELETE FROM pokemon_type")
        cur.executemany(
            "INSERT INTO pokemon_type (pokemon_id, type_id, slot) VALUES (%s, %s, %s)",
            rows,
        )
        conn.commit()
    LOGGER.info("Loaded %d Pokémon type rows", len(rows))


def load_pokemon_abilities(conn, abilities: list[dict], ability_map: dict) -> None:
    """Load pokemon_ability rows from abilities_if.json pokemon lists."""
    pokemon_name_to_id = load_id_map(conn, "pokemon")

    # Accumulate the full intended slot set per Pokémon, then DELETE +
    # bulk-insert atomically. The JSON is keyed by ability, so a Pokémon's
    # two normal abilities land in separate iterations: normal → slots 1,2
    # in encounter order (capped at 2), hidden → slot 3. Every drop is
    # logged (never silent); audit_db.py independently verifies DB vs JSON.
    desired: dict[int, dict[int, tuple[int, bool]]] = {}
    normal_count: dict[int, int] = {}

    for ab in abilities:
        ability_id = ability_map.get(ab["name_en"].lower())
        if not ability_id:
            continue
        for poke in ab.get("pokemon", []):
            poke_id = pokemon_name_to_id.get(poke["name"].lower())
            if not poke_id:
                continue
            slots = desired.setdefault(poke_id, {})
            if poke["is_hidden"]:
                slot = 3
                if slot in slots:
                    LOGGER.warning(
                        "Pokémon id=%d: extra hidden ability '%s' dropped (slot 3 taken)",
                        poke_id, ab["name_en"],
                    )
                    continue
            else:
                n = normal_count.get(poke_id, 0) + 1
                normal_count[poke_id] = n
                if n > 2:
                    LOGGER.warning(
                        "Pokémon id=%d: >2 normal abilities, '%s' dropped (slot %d)",
                        poke_id, ab["name_en"], n,
                    )
                    continue
                slot = n
            slots[slot] = (ability_id, poke["is_hidden"])

    rows = [
        (pid, aid, slot, hidden)
        for pid, smap in desired.items()
        for slot, (aid, hidden) in smap.items()
    ]
    with conn.cursor() as cur:
        cur.execute("DELETE FROM pokemon_ability")
        cur.executemany(
            "INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden) "
            "VALUES (%s, %s, %s, %s)",
            rows,
        )
        conn.commit()
    LOGGER.info("Loaded %d Pokémon ability rows", len(rows))


def load_evolutions(conn, evolutions_base: list[dict]) -> None:
    """
    Load evolution data.
    Base evolutions come from PokeAPI (evolutions_base.json).
    IF overrides replace or augment those based on if_evolution_overrides.json.
    """
    if_overrides_map = _load_if_evolution_overrides()

    pokemon_name_to_id = load_id_map(conn, "pokemon")

    with conn.cursor() as cur:
        for evo in evolutions_base:
            from_id  = pokemon_name_to_id.get(evo["from_name"].lower())
            into_id  = pokemon_name_to_id.get(evo["into_name"].lower())
            if not from_id or not into_id:
                continue

            key          = (evo["from_name"].lower(), evo["into_name"].lower())
            if_overrides = if_overrides_map.get(key)

            if if_overrides:
                # Replace with IF-specific conditions
                for cond in if_overrides:
                    cur.execute(
                        """INSERT INTO pokemon_evolution
                           (pokemon_id, evolves_into_id, trigger_type, min_level,
                            item_name_en, if_override, if_notes)
                           VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                           ON CONFLICT (pokemon_id, evolves_into_id, trigger_type, COALESCE(item_name_en, ''))
                           DO NOTHING""",
                        (from_id, into_id, cond["trigger"], cond["min_level"],
                         cond["item"], cond["notes"]),
                    )
            else:
                # Base game evolution, unmodified
                trigger  = evo.get("trigger", "other")
                cur.execute(
                    """INSERT INTO pokemon_evolution
                       (pokemon_id, evolves_into_id, trigger_type, min_level, item_name_en)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (pokemon_id, evolves_into_id, trigger_type, COALESCE(item_name_en, ''))
                       DO NOTHING""",
                    (from_id, into_id, trigger, evo.get("min_level"), evo.get("item")),
                )
        conn.commit()
    LOGGER.info("Loaded evolutions")


def _normalize_move_name(name: str) -> str:
    """Normalize FR move name for fuzzy lookup.

    Handles the two main mismatches between Pokepedia and PokeAPI names:
      - Apostrophe variants: ' (U+2019) ↔ ' (U+0027)
      - Hyphens vs spaces: 'Cage-Éclair' ↔ 'Cage Éclair'
    """
    name = name.lower()
    name = name.replace("\u2019", "'").replace("\u2018", "'")  # curly → straight
    name = name.replace("-", " ")
    return name


def _build_move_fr_lookup(move_fr_map: dict[str, int]) -> dict[str, int]:
    """Build an extended lookup with normalized keys for fuzzy matching."""
    lookup: dict[str, int] = {}
    for name_fr, db_id in move_fr_map.items():
        lookup[name_fr] = db_id                        # exact (already lowered)
        lookup[_normalize_move_name(name_fr)] = db_id  # normalized
    return lookup


def load_movesets(conn, movesets: list[dict], move_map: dict) -> None:
    """Load pokemon_move from movesets_merged.json (name_fr as key)."""
    move_fr_map = load_id_map(conn, "move", "name_fr", where="name_fr IS NOT NULL")

    # Extended lookup with normalized keys (apostrophes + hyphens)
    lookup = _build_move_fr_lookup(move_fr_map)

    rows: list[tuple] = []
    skipped = 0
    for record in movesets:
        raw     = record["move_name_fr"]
        move_id = lookup.get(raw.lower()) or lookup.get(_normalize_move_name(raw))
        if not move_id:
            skipped += 1
            continue
        rows.append((
            record["pokemon_if_id"],
            move_id,
            record["method"],
            record.get("level"),
            record.get("source", "base"),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO pokemon_move
               (pokemon_id, move_id, method, level, source)
               VALUES %s
               ON CONFLICT (pokemon_id, move_id, method) DO NOTHING""",
            rows,
            page_size=2000,
        )
        conn.commit()
    LOGGER.info("Loaded %d moveset rows (%d skipped — move not found)", len(rows), skipped)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    required = {
        "data/pokedex_if.json":      "extract_pokedex_if.py",
        "data/pokemon_stats.json":   "extract_stats_pokeapi.py",
        "data/moves_if.json":        "extract_moves_if.py",
        "data/tms_if.json":          "extract_moves_if.py",
        "data/abilities_if.json":    "extract_abilities_if.py",
        "data/movesets_merged.json": "transform_merge_movesets.py",
        "data/evolutions_base.json": "extract_stats_pokeapi.py",
    }
    for path, script in required.items():
        if not Path(path).exists():
            raise FileNotFoundError(f"{path} not found — run {script} first")

    pokedex      = load_json(Path("data/pokedex_if.json"))
    stats        = load_json(Path("data/pokemon_stats.json"))
    moves        = load_json(Path("data/moves_if.json"))
    tms          = load_json(Path("data/tms_if.json"))
    abilities    = load_json(Path("data/abilities_if.json"))
    movesets     = load_json(Path("data/movesets_merged.json"))
    evolutions   = load_json(Path("data/evolutions_base.json"))

    LOGGER.info("Connecting to PostgreSQL...")
    with pg_connection() as conn:
        gen_map     = load_generations(conn)
        type_map    = load_types(conn, moves)
        ability_map = load_abilities(conn, abilities)
        move_map    = load_moves(conn, moves, type_map)
        load_tms(conn, tms, move_map)
        load_pokemon(conn, pokedex, stats, gen_map)
        load_pokemon_types(conn, pokedex, type_map)
        load_pokemon_abilities(conn, abilities, ability_map)
        load_evolutions(conn, evolutions)
        load_movesets(conn, movesets, move_map)

    LOGGER.info("All data loaded successfully.")


if __name__ == "__main__":
    main()
